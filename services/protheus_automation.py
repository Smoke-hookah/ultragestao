"""Automacao web do Protheus via Playwright."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional
import zipfile

from config import CONFIG_DIR
from utils.logger import logger


@dataclass
class ProtheusBranchRequest:
    uf: str
    branch_code: str
    nf_start: str
    nf_end: str
    xml_dir: Path
    boleto_pdf_path: Path
    work_dir: Path
    diagnostics_dir: Path


@dataclass
class ProtheusAutomationResult:
    xml_dir: Path
    boleto_pdf_path: Optional[Path]
    notes: List[str] = field(default_factory=list)
    download_manifest: Dict[str, Any] = field(default_factory=dict)


class ProtheusPlaywrightCollector:
    def __init__(self) -> None:
        self.profile_dir = CONFIG_DIR / "protheus" / "browser-profile"
        self.profile_dir.mkdir(parents=True, exist_ok=True)

    def _load_playwright(self):
        try:
            browsers_dir = Path(os.getenv("ULTRADANFE_PLAYWRIGHT_BROWSERS_DIR") or "").strip()
            if browsers_dir:
                os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(browsers_dir))
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError  # type: ignore
            from playwright.sync_api import sync_playwright  # type: ignore

            return sync_playwright, PlaywrightTimeoutError
        except Exception as error:
            raise RuntimeError(
                "Playwright nao esta disponivel. Instale a dependencia e baixe o Chromium do app."
            ) from error

    def _timeout_ms(self, config: Dict[str, Any], key: str, default: int) -> int:
        try:
            return int(((config.get("timeouts") or {}).get(key)) or default)
        except Exception:
            return default

    def _selector(self, block: Dict[str, Any], key: str) -> str:
        value = str(block.get(key) or "").strip()
        if not value or value.startswith("__"):
            raise RuntimeError(f"Campo de configuracao ausente: {key}")
        return value

    def _apply_steps(self, page, steps: List[Dict[str, Any]], default_timeout: int) -> None:
        for idx, step in enumerate(steps or [], 1):
            action = str(step.get("action") or "").strip().lower()
            timeout_ms = int(step.get("timeout_ms") or default_timeout)
            selector = str(step.get("selector") or "").strip()
            value = str(step.get("value") or "")
            if action == "goto":
                page.goto(value, wait_until="networkidle", timeout=timeout_ms)
            elif action == "click":
                page.locator(selector).first.click(timeout=timeout_ms)
            elif action == "fill":
                page.locator(selector).first.fill(value, timeout=timeout_ms)
            elif action == "press":
                page.locator(selector).first.press(value or "Enter", timeout=timeout_ms)
            elif action == "wait_for":
                page.locator(selector).first.wait_for(state=str(step.get("state") or "visible"), timeout=timeout_ms)
            elif action == "sleep":
                page.wait_for_timeout(int(step.get("ms") or 500))
            else:
                raise RuntimeError(f"Acao de automacao nao suportada: {action or f'passo#{idx}'}")

    def _capture_diagnostics(self, page, diagnostics_dir: Path, stage: str, error: Exception | None = None) -> None:
        diagnostics_dir.mkdir(parents=True, exist_ok=True)
        stamp = str(int(time.time() * 1000))
        if error is not None:
            (diagnostics_dir / f"{stamp}-{stage}.txt").write_text(
                f"{type(error).__name__}: {error}",
                encoding="utf-8",
            )

        try:
            page.screenshot(path=str(diagnostics_dir / f"{stamp}-{stage}.png"), full_page=True)
        except Exception:
            pass

        try:
            html = page.content()
            (diagnostics_dir / f"{stamp}-{stage}.html").write_text(html, encoding="utf-8")
        except Exception:
            pass

    def _wait_for_files(self, target_dir: Path, expected_glob: str, settle_seconds: int, timeout_ms: int) -> List[Path]:
        deadline = time.time() + (timeout_ms / 1000.0)
        latest_files: List[Path] = []
        while time.time() < deadline:
            files = sorted(target_dir.glob(expected_glob))
            if files:
                latest_mtime = max(f.stat().st_mtime for f in files)
                if time.time() - latest_mtime >= settle_seconds:
                    return files
                latest_files = files
            time.sleep(0.5)
        return latest_files

    def _extract_zip_download(self, source_path: Path, target_dir: Path) -> List[Path]:
        extracted: List[Path] = []
        if zipfile.is_zipfile(source_path):
            with zipfile.ZipFile(source_path, "r") as handle:
                handle.extractall(target_dir)
            extracted = sorted(target_dir.rglob("*.xml"))
        return extracted

    def _run_login(self, page, config: Dict[str, Any]) -> None:
        login_cfg = config.get("login") or {}
        page.goto(str(config.get("base_url") or "").strip(), wait_until="networkidle", timeout=self._timeout_ms(config, "navigation_ms", 30000))
        success_selector = self._selector(login_cfg, "success_selector")
        if page.locator(success_selector).count() > 0:
            try:
                page.locator(success_selector).first.wait_for(state="visible", timeout=1500)
                return
            except Exception:
                pass

        username = str(login_cfg.get("_resolved_username") or "").strip()
        password = str(login_cfg.get("_resolved_password") or "")
        if not username or not password:
            raise RuntimeError("Credenciais do Protheus ausentes para login automatico")

        page.locator(self._selector(login_cfg, "username_selector")).first.fill(username, timeout=self._timeout_ms(config, "default_ms", 12000))
        page.locator(self._selector(login_cfg, "password_selector")).first.fill(password, timeout=self._timeout_ms(config, "default_ms", 12000))
        page.locator(self._selector(login_cfg, "submit_selector")).first.click(timeout=self._timeout_ms(config, "default_ms", 12000))
        page.locator(success_selector).first.wait_for(state="visible", timeout=self._timeout_ms(config, "navigation_ms", 30000))

    def _run_branch_switch(self, page, config: Dict[str, Any], branch_code: str) -> None:
        branch_cfg = config.get("branch") or {}
        self._apply_steps(page, list(branch_cfg.get("open_steps") or []), self._timeout_ms(config, "default_ms", 12000))
        page.locator(self._selector(branch_cfg, "input_selector")).first.fill(branch_code, timeout=self._timeout_ms(config, "default_ms", 12000))
        page.locator(self._selector(branch_cfg, "confirm_selector")).first.click(timeout=self._timeout_ms(config, "default_ms", 12000))
        page.locator(self._selector(branch_cfg, "success_selector")).first.wait_for(state="visible", timeout=self._timeout_ms(config, "navigation_ms", 30000))

    def _run_xml_export(self, page, config: Dict[str, Any], request: ProtheusBranchRequest) -> Dict[str, Any]:
        xml_cfg = config.get("xml_export") or {}
        self._apply_steps(page, list(xml_cfg.get("open_steps") or []), self._timeout_ms(config, "default_ms", 12000))

        page.locator(self._selector(xml_cfg, "nf_from_selector")).first.fill(request.nf_start, timeout=self._timeout_ms(config, "default_ms", 12000))
        page.locator(self._selector(xml_cfg, "nf_to_selector")).first.fill(request.nf_end, timeout=self._timeout_ms(config, "default_ms", 12000))

        mode = str(xml_cfg.get("mode") or "target_dir").strip().lower()
        if mode == "target_dir":
            page.locator(self._selector(xml_cfg, "target_dir_selector")).first.fill(
                str(request.xml_dir),
                timeout=self._timeout_ms(config, "default_ms", 12000),
            )
            page.locator(self._selector(xml_cfg, "submit_selector")).first.click(timeout=self._timeout_ms(config, "default_ms", 12000))
            page.locator(self._selector(xml_cfg, "completion_selector")).first.wait_for(
                state="visible",
                timeout=self._timeout_ms(config, "download_ms", 180000),
            )
            files = self._wait_for_files(
                request.xml_dir,
                str(xml_cfg.get("expected_glob") or "*.xml"),
                int((config.get("timeouts") or {}).get("file_settle_seconds") or 3),
                self._timeout_ms(config, "download_ms", 180000),
            )
            return {
                "mode": mode,
                "files": [str(item) for item in files],
            }

        if mode == "download":
            with page.expect_download(timeout=self._timeout_ms(config, "download_ms", 180000)) as download_info:
                page.locator(self._selector(xml_cfg, "submit_selector")).first.click(timeout=self._timeout_ms(config, "default_ms", 12000))
            download = download_info.value
            suggested = Path(download.suggested_filename or "xml_export.zip").name
            download_path = request.work_dir / suggested
            download.save_as(str(download_path))
            page.locator(self._selector(xml_cfg, "completion_selector")).first.wait_for(
                state="visible",
                timeout=self._timeout_ms(config, "download_ms", 180000),
            )
            extracted = self._extract_zip_download(download_path, request.xml_dir)
            return {
                "mode": mode,
                "download": str(download_path),
                "files": [str(item) for item in extracted],
            }

        raise RuntimeError(f"Modo de exportacao XML nao suportado: {mode}")

    def _run_boleto_export(self, page, config: Dict[str, Any], request: ProtheusBranchRequest) -> Dict[str, Any]:
        boleto_cfg = config.get("boleto_export") or {}
        self._apply_steps(page, list(boleto_cfg.get("open_steps") or []), self._timeout_ms(config, "default_ms", 12000))

        page.locator(self._selector(boleto_cfg, "nf_from_selector")).first.fill(request.nf_start, timeout=self._timeout_ms(config, "default_ms", 12000))
        page.locator(self._selector(boleto_cfg, "nf_to_selector")).first.fill(request.nf_end, timeout=self._timeout_ms(config, "default_ms", 12000))

        mode = str(boleto_cfg.get("mode") or "download").strip().lower()
        if mode != "download":
            raise RuntimeError(f"Modo de exportacao de boleto nao suportado: {mode}")

        with page.expect_download(timeout=self._timeout_ms(config, "download_ms", 180000)) as download_info:
            page.locator(self._selector(boleto_cfg, "submit_selector")).first.click(timeout=self._timeout_ms(config, "default_ms", 12000))
        download = download_info.value
        request.boleto_pdf_path.parent.mkdir(parents=True, exist_ok=True)
        download.save_as(str(request.boleto_pdf_path))
        page.locator(self._selector(boleto_cfg, "completion_selector")).first.wait_for(
            state="visible",
            timeout=self._timeout_ms(config, "download_ms", 180000),
        )
        return {
            "mode": mode,
            "download": str(request.boleto_pdf_path),
        }

    def collect_branch(
        self,
        request: ProtheusBranchRequest,
        config: Dict[str, Any],
        credentials: Dict[str, str],
        progress_callback=None,
    ) -> ProtheusAutomationResult:
        sync_playwright, PlaywrightTimeoutError = self._load_playwright()
        config = json.loads(json.dumps(config))
        config.setdefault("login", {})
        config["login"]["_resolved_username"] = credentials.get("username") or config.get("protheus_user") or ""
        config["login"]["_resolved_password"] = credentials.get("password") or ""

        default_timeout = self._timeout_ms(config, "default_ms", 12000)
        slow_mo_ms = int(((config.get("browser") or {}).get("slow_mo_ms")) or 0)
        viewport = ((config.get("browser") or {}).get("viewport")) or {"width": 1440, "height": 900}
        headless = bool(((config.get("browser") or {}).get("headless")) or False)

        request.xml_dir.mkdir(parents=True, exist_ok=True)
        request.work_dir.mkdir(parents=True, exist_ok=True)
        request.diagnostics_dir.mkdir(parents=True, exist_ok=True)

        if progress_callback:
            progress_callback("protheus_login", 10, f"Abrindo Protheus para filial {request.branch_code}", request.uf)

        with sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir),
                headless=headless,
                slow_mo=slow_mo_ms,
                accept_downloads=True,
                viewport=viewport,
            )
            page = context.pages[0] if context.pages else context.new_page()
            page.set_default_timeout(default_timeout)
            try:
                self._run_login(page, config)

                if progress_callback:
                    progress_callback("protheus_filial", 25, f"Alternando para filial {request.branch_code}", request.branch_code)
                self._run_branch_switch(page, config, request.branch_code)

                if progress_callback:
                    progress_callback("protheus_xml", 45, f"Extraindo XMLs {request.nf_start}-{request.nf_end}", request.branch_code)
                xml_manifest = self._run_xml_export(page, config, request)

                if progress_callback:
                    progress_callback("protheus_boletos", 70, f"Baixando boletos {request.nf_start}-{request.nf_end}", request.branch_code)
                boleto_manifest = self._run_boleto_export(page, config, request)

                manifest = {
                    "xml_export": xml_manifest,
                    "boleto_export": boleto_manifest,
                }
                (request.diagnostics_dir / "download_manifest.json").write_text(
                    json.dumps(manifest, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                return ProtheusAutomationResult(
                    xml_dir=request.xml_dir,
                    boleto_pdf_path=request.boleto_pdf_path if request.boleto_pdf_path.exists() else None,
                    notes=[],
                    download_manifest=manifest,
                )
            except PlaywrightTimeoutError as error:
                self._capture_diagnostics(page, request.diagnostics_dir, "timeout", error)
                raise RuntimeError(f"Timeout na automacao do Protheus: {error}") from error
            except Exception as error:
                self._capture_diagnostics(page, request.diagnostics_dir, "falha", error)
                raise
            finally:
                try:
                    context.close()
                except Exception:
                    pass


def criar_coletor_protheus_padrao() -> ProtheusPlaywrightCollector:
    return ProtheusPlaywrightCollector()
