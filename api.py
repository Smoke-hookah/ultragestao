"""API Flask focada no fluxo de Processar em Lote."""

from datetime import datetime
import json
import os
from pathlib import Path
import multiprocessing
import subprocess
import sys
import tempfile
import time
import uuid

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.exceptions import RequestEntityTooLarge

from config import CONFIG_DIR, LOGS_DIR, MAX_FORM_PARTS, MAX_UPLOAD_MB, OUTPUT_DIR
from services.cobertura_lote import criar_servico_cobertura_padrao
from services.excel_reader import LeitorPlanilha
from services.orquestrador import Orquestrador
from services.protheus_coleta import criar_servico_coleta_protheus_padrao
from services.protheus_config import get_public_protheus_config, save_protheus_public_config
from services.historico_service import HistoricoService
from utils.logger import logger
from utils.progress import progresso_atual, set_progresso
from utils.ui import obter_pasta_xmls_salva, salvar_pasta_xmls


if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys._MEIPASS)
    STATIC_FOLDER = BASE_DIR / "static" / "dist"
else:
    BASE_DIR = Path(__file__).parent
    STATIC_FOLDER = BASE_DIR / "static" / "dist"


app = Flask(__name__, static_folder=str(STATIC_FOLDER) if STATIC_FOLDER.exists() else None)
CORS(app)

app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024
app.config["MAX_FORM_PARTS"] = MAX_FORM_PARTS

processamento_ativo = False

_PLANILHA_CACHE: dict[str, dict] = {}
_PLANILHA_CACHE_TTL_SECONDS = 60 * 60
_PLANILHA_CACHE_MAX = 10
_PROTHEUS_SERVICE = criar_servico_coleta_protheus_padrao()
_PROTHEUS_STAGING = _PROTHEUS_SERVICE.staging_store
_PROTHEUS_CREDENTIAL_STORE = _PROTHEUS_SERVICE.credential_store
_COVERAGE_SERVICE = criar_servico_cobertura_padrao(protheus_service=_PROTHEUS_SERVICE)
_COVERAGE_STAGING = _COVERAGE_SERVICE.coverage_store


def _output_base_dir() -> Path:
    output_dir = os.getenv("ULTRADANFE_OUTPUT_DIR")
    if output_dir:
        return Path(output_dir)
    return Path(__file__).resolve().parent / "output"


def _safe_rmtree(path: Path | None) -> None:
    if not path:
        return

    try:
        resolved = path.resolve()
    except Exception:
        resolved = path

    try:
        output_base = _output_base_dir().resolve()
        if resolved != output_base and output_base not in resolved.parents:
            logger.warning(f"Ignorando limpeza fora da pasta output: {resolved}")
            return
    except Exception:
        pass

    try:
        import shutil

        shutil.rmtree(resolved, ignore_errors=True)
    except Exception as error:
        logger.warning(f"Falha ao limpar diretorio temporario {resolved}: {error}")


def _discard_planilha_cache_entry(key: str) -> None:
    cached = _PLANILHA_CACHE.pop(key, None)
    if not cached:
        return

    run_dir = cached.get("run_dir")
    if run_dir:
        _safe_rmtree(Path(str(run_dir)))


def _planilha_cache_entry_age(value: dict, now: float | None = None) -> float:
    current_time = now if now is not None else time.time()
    last_access = float(value.get("last_accessed", value.get("created", 0)) or 0)
    return current_time - last_access


def _touch_planilha_cache_entry(key: str) -> None:
    cached = _PLANILHA_CACHE.get(key)
    if not cached:
        return
    cached["last_accessed"] = time.time()


def _cleanup_stale_temp_dirs() -> None:
    _PROTHEUS_STAGING.cleanup()
    _COVERAGE_STAGING.cleanup()
    output_path = _output_base_dir()
    if not output_path.exists():
        return

    now = time.time()
    prefixes = ("ultradanfe_filtros_", "ultradanfe_local_")
    for child in output_path.iterdir():
        if not child.is_dir() or not child.name.startswith(prefixes):
            continue
        try:
            age_seconds = now - child.stat().st_mtime
        except Exception:
            continue
        if age_seconds > _PLANILHA_CACHE_TTL_SECONDS:
            _safe_rmtree(child)


def _cleanup_planilha_cache() -> None:
    now = time.time()
    expirados = [
        key
        for key, value in _PLANILHA_CACHE.items()
        if _planilha_cache_entry_age(value, now) > _PLANILHA_CACHE_TTL_SECONDS
    ]
    for key in expirados:
        _discard_planilha_cache_entry(key)

    if len(_PLANILHA_CACHE) > _PLANILHA_CACHE_MAX:
        itens = sorted(
            _PLANILHA_CACHE.items(),
            key=lambda item: float(item[1].get("last_accessed", item[1].get("created", 0)) or 0),
        )
        for key, _ in itens[: max(0, len(_PLANILHA_CACHE) - _PLANILHA_CACHE_MAX)]:
            _discard_planilha_cache_entry(key)


def _allowed_ui_roots() -> list[Path]:
    return [OUTPUT_DIR, CONFIG_DIR, LOGS_DIR]


def _resolve_allowed_ui_dir(path: Path) -> bool:
    try:
        target = path.resolve()
    except Exception:
        target = path

    for base in _allowed_ui_roots():
        try:
            resolved_base = base.resolve()
            if target == resolved_base or resolved_base in target.parents:
                return True
        except Exception:
            continue
    return False


def _parse_json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    except Exception:
        pass
    return [item.strip() for item in str(value).split(",") if item.strip()]


@app.errorhandler(RequestEntityTooLarge)
def handle_request_entity_too_large(error):
    return jsonify(
        {
            "sucesso": False,
            "mensagem": (
                "Upload muito grande (413). "
                f"Limite atual: {MAX_UPLOAD_MB}MB e {MAX_FORM_PARTS} arquivos/partes. "
                "Tente enviar menos arquivos ou aumente MAX_UPLOAD_MB/MAX_FORM_PARTS no .env."
            ),
        }
    ), 413


@app.route("/api/planilha-filtros", methods=["POST"])
def planilha_filtros():
    """Le a planilha e devolve opcoes de filtros para o frontend."""
    planilha = request.files.get("planilha")
    if not planilha or not (planilha.filename or "").strip():
        return jsonify({"sucesso": False, "mensagem": "Arquivo 'planilha' e obrigatorio"}), 400

    run_dir: Path | None = None
    token: str | None = None
    try:
        output_path = _output_base_dir()
        output_path.mkdir(parents=True, exist_ok=True)
        _cleanup_stale_temp_dirs()

        run_dir = Path(tempfile.mkdtemp(prefix="ultradanfe_filtros_", dir=str(output_path)))
        uploads_dir = run_dir / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)

        plan_name = Path(planilha.filename or "planilha.xlsx").name
        plan_path = uploads_dir / plan_name
        planilha.save(plan_path)

        leitor = LeitorPlanilha(str(plan_path))
        alocacoes = leitor.ler_alocacoes()

        _cleanup_planilha_cache()
        token = uuid.uuid4().hex
        _PLANILHA_CACHE[token] = {
            "created": time.time(),
            "last_accessed": time.time(),
            "run_dir": str(run_dir),
            "planilha_path": str(plan_path),
            "alocacoes": alocacoes,
        }

        rotas: set[str] = set()
        placas: set[str] = set()
        clientes: set[str] = set()
        rota_clientes: dict[str, set[str]] = {}
        placa_clientes: dict[str, set[str]] = {}

        for alocacao in alocacoes:
            rota = str(getattr(alocacao, "rota", "") or "").strip()
            placa = str(getattr(alocacao, "placa", "") or "").strip()
            cliente = str(getattr(alocacao, "cliente", "") or "").strip()

            if rota:
                rotas.add(rota)
            if placa:
                placas.add(placa)
            if cliente:
                clientes.add(cliente)

            if rota and cliente:
                rota_clientes.setdefault(rota, set()).add(cliente)
            if placa and cliente:
                placa_clientes.setdefault(placa, set()).add(cliente)

        return jsonify(
            {
                "sucesso": True,
                "rotas": sorted(rotas),
                "placas": sorted(placas),
                "clientes": sorted(clientes),
                "rota_clientes": {key: sorted(value) for key, value in rota_clientes.items()},
                "placa_clientes": {key: sorted(value) for key, value in placa_clientes.items()},
                "total_alocacoes": len(alocacoes),
                "planilha_token": token,
            }
        )
    except Exception as error:
        logger.error(f"Erro no endpoint /api/planilha-filtros: {error}")
        return jsonify({"sucesso": False, "mensagem": f"Erro: {error}"}), 500
    finally:
        if token is None:
            _safe_rmtree(run_dir)


@app.route("/api/progresso", methods=["GET"])
def get_progresso():
    """Retorna o progresso do processamento atual."""
    return jsonify(
        {
            "processamento_ativo": processamento_ativo,
            "etapa": progresso_atual.get("etapa", ""),
            "percentual": progresso_atual.get("percentual", 0),
            "mensagem": progresso_atual.get("mensagem", ""),
            "detalhes": progresso_atual.get("detalhes", ""),
        }
    )


@app.route("/api/ui/pasta-xmls", methods=["GET"])
def ui_get_pasta_xmls():
    """Retorna a pasta de XMLs salva no backend."""
    return jsonify({"sucesso": True, "pasta_xmls": obter_pasta_xmls_salva()})


@app.route("/api/ui/protheus-config", methods=["GET", "POST"])
def ui_protheus_config():
    """Le e grava configuracoes publicas do Protheus."""
    if request.method == "GET":
        return jsonify(
            {
                "sucesso": True,
                "config": get_public_protheus_config(
                    has_password=_PROTHEUS_CREDENTIAL_STORE.has()
                ),
            }
        )

    dados = request.get_json(silent=True) or {}
    config = save_protheus_public_config(dados)
    return jsonify(
        {
            "sucesso": True,
            "config": get_public_protheus_config(
                has_password=_PROTHEUS_CREDENTIAL_STORE.has()
            ),
            "mensagem": "Configuracao do Protheus atualizada",
            "uf_branch_map": config.get("uf_branch_map") or {},
        }
    )


@app.route("/api/ui/protheus-credenciais", methods=["POST"])
def ui_protheus_credenciais():
    """Salva ou atualiza as credenciais do Protheus no Credential Manager."""
    dados = request.get_json(silent=True) or {}
    username = str(dados.get("username") or "").strip()
    password = str(dados.get("password") or "")
    if not username:
        return jsonify({"sucesso": False, "mensagem": "username e obrigatorio"}), 400
    if not password:
        return jsonify({"sucesso": False, "mensagem": "password e obrigatorio"}), 400

    _PROTHEUS_CREDENTIAL_STORE.save(username, password)
    save_protheus_public_config({"protheus_user": username})
    return jsonify(
        {
            "sucesso": True,
            "mensagem": "Credenciais do Protheus salvas com sucesso",
            "config": get_public_protheus_config(has_password=True),
        }
    )


@app.route("/api/ui/pasta-xmls/set", methods=["POST"])
def ui_set_pasta_xmls():
    """Salva a pasta de XMLs informada pelo frontend."""
    dados = request.get_json(silent=True) or {}
    pasta = (dados.get("pasta_xmls") or "").strip()
    if not pasta:
        return jsonify({"sucesso": False, "mensagem": "pasta_xmls e obrigatoria"}), 400

    caminho = Path(pasta)
    if not caminho.exists() or not caminho.is_dir():
        return jsonify({"sucesso": False, "mensagem": f"Pasta invalida: {pasta}"}), 400

    salvar_pasta_xmls(str(caminho))
    return jsonify({"sucesso": True, "pasta_xmls": str(caminho)})


@app.route("/api/ui/pasta-xmls/selecionar", methods=["POST"])
def ui_selecionar_pasta_xmls():
    """Abre a janela do Windows para selecionar a pasta de XMLs."""
    from utils.ui import selecionar_pasta_xmls

    try:
        pasta = selecionar_pasta_xmls()
        if not pasta:
            return jsonify({"sucesso": False, "mensagem": "Selecao cancelada"}), 400

        salvar_pasta_xmls(pasta)
        return jsonify({"sucesso": True, "pasta_xmls": pasta})
    except Exception as error:
        logger.error(f"Erro ao selecionar pasta: {error}")
        return jsonify({"sucesso": False, "mensagem": f"Erro: {error}"}), 500


@app.route("/api/ui/abrir-pasta", methods=["POST"])
def ui_abrir_pasta():
    """Abre uma pasta no explorer local."""
    dados = request.get_json(silent=True) or {}
    caminho = (dados.get("path") or "").strip()
    if not caminho:
        return jsonify({"sucesso": False, "mensagem": "path e obrigatorio"}), 400

    pasta = Path(caminho)
    if not pasta.exists() or not pasta.is_dir():
        return jsonify({"sucesso": False, "mensagem": f"Pasta invalida: {caminho}"}), 400

    if not _resolve_allowed_ui_dir(pasta):
        return jsonify({"sucesso": False, "mensagem": "Acesso negado"}), 403

    try:
        if os.name == "nt":
            subprocess.Popen(["explorer", str(pasta)])
        else:
            subprocess.Popen([str(pasta)])
        return jsonify({"sucesso": True})
    except Exception as error:
        return jsonify({"sucesso": False, "mensagem": f"Erro: {error}"}), 500


@app.route("/api/protheus/extrair", methods=["POST"])
def protheus_extrair():
    """Extrai XMLs e boletos do Protheus com base no subset filtrado."""
    global processamento_ativo

    if processamento_ativo:
        return jsonify({"sucesso": False, "mensagem": "Um processamento ja esta em andamento"}), 409

    dados = request.get_json(silent=True) or {}
    planilha_token = str(dados.get("planilha_token") or "").strip()
    uf = str(dados.get("uf") or "").strip().upper()
    filtro_rotas = _parse_json_list(json.dumps(dados.get("filtro_rotas") or []))
    filtro_placas = _parse_json_list(json.dumps(dados.get("filtro_placas") or []))
    filtro_clientes = _parse_json_list(json.dumps(dados.get("filtro_clientes") or []))

    if not planilha_token:
        return jsonify({"sucesso": False, "mensagem": "planilha_token e obrigatorio"}), 400
    if not uf:
        return jsonify({"sucesso": False, "mensagem": "UF obrigatoria para a coleta Protheus"}), 400

    _cleanup_planilha_cache()
    cached = _PLANILHA_CACHE.get(planilha_token)
    if not cached:
        return jsonify(
            {"sucesso": False, "mensagem": "Token de planilha expirou. Selecione a planilha novamente."}
        ), 400
    _touch_planilha_cache_entry(planilha_token)

    try:
        processamento_ativo = True
        review = _PROTHEUS_SERVICE.collect(
            planilha_token=planilha_token,
            planilha_path=str(cached.get("planilha_path") or ""),
            alocacoes=list(cached.get("alocacoes") or []),
            uf=uf,
            filtro_rotas=filtro_rotas,
            filtro_placas=filtro_placas,
            filtro_clientes=filtro_clientes,
        )
        return jsonify(
            {
                "sucesso": True,
                "mensagem": "Coleta Protheus concluida",
                "review": review,
            }
        )
    except ValueError as error:
        logger.error(f"Erro de validacao no endpoint /api/protheus/extrair: {error}")
        return jsonify({"sucesso": False, "mensagem": str(error)}), 400
    except Exception as error:
        logger.error(f"Erro no endpoint /api/protheus/extrair: {error}")
        return jsonify({"sucesso": False, "mensagem": f"Erro: {error}"}), 500
    finally:
        processamento_ativo = False


@app.route("/api/cobertura-lote", methods=["POST"])
def cobertura_lote():
    """Valida a cobertura de XML/PDF do subset antes do processamento."""
    global processamento_ativo

    if processamento_ativo:
        return jsonify({"sucesso": False, "mensagem": "Um processamento ja esta em andamento"}), 409

    dados = request.get_json(silent=True) or {}
    planilha_token = str(dados.get("planilha_token") or "").strip()
    coleta_token = str(dados.get("coleta_token") or "").strip() or None
    uf = str(dados.get("uf") or "").strip().upper() or None
    filtro_rotas = _parse_json_list(json.dumps(dados.get("filtro_rotas") or []))
    filtro_placas = _parse_json_list(json.dumps(dados.get("filtro_placas") or []))
    filtro_clientes = _parse_json_list(json.dumps(dados.get("filtro_clientes") or []))
    pasta_xmls = str(dados.get("pasta_xmls") or "").strip() or obter_pasta_xmls_salva()
    garantir_pdf = bool(dados.get("garantir_pdf", True))
    baixar_pdf = bool(dados.get("baixar_pdf", True))
    metodo_pdf = str(dados.get("metodo_pdf") or "api").strip()

    if not planilha_token:
        return jsonify({"sucesso": False, "mensagem": "planilha_token e obrigatorio"}), 400

    _cleanup_planilha_cache()
    cached = _PLANILHA_CACHE.get(planilha_token)
    if not cached:
        return jsonify(
            {"sucesso": False, "mensagem": "Token de planilha expirou. Selecione a planilha novamente."}
        ), 400
    _touch_planilha_cache_entry(planilha_token)

    coleta_manifest = None
    if coleta_token:
        coleta_manifest = _PROTHEUS_STAGING.load_manifest(coleta_token)
        if not coleta_manifest:
            return jsonify({"sucesso": False, "mensagem": "coleta_token expirou. Refaça a coleta Protheus."}), 400

    try:
        processamento_ativo = True
        review = _COVERAGE_SERVICE.validate(
            planilha_token=planilha_token,
            planilha_path=str(cached.get("planilha_path") or ""),
            alocacoes=list(cached.get("alocacoes") or []),
            pasta_xmls=pasta_xmls,
            coleta_manifest=coleta_manifest,
            uf=uf,
            filtro_rotas=filtro_rotas,
            filtro_placas=filtro_placas,
            filtro_clientes=filtro_clientes,
            baixar_pdf=baixar_pdf,
            metodo_pdf=metodo_pdf,
            garantir_pdf=garantir_pdf,
        )
        mensagem = (
            "Cobertura validada"
            if review.get("ready_for_processing")
            else "Cobertura bloqueada; revise os itens faltantes antes de processar"
        )
        return jsonify({"sucesso": True, "mensagem": mensagem, "review": review})
    except ValueError as error:
        logger.error(f"Erro de validacao no endpoint /api/cobertura-lote: {error}")
        return jsonify({"sucesso": False, "mensagem": str(error)}), 400
    except Exception as error:
        logger.error(f"Erro no endpoint /api/cobertura-lote: {error}")
        return jsonify({"sucesso": False, "mensagem": f"Erro: {error}"}), 500
    finally:
        processamento_ativo = False


@app.route("/api/processar-local", methods=["POST"])
def processar_local():
    """Processa em lote usando a planilha do frontend e a pasta de XMLs salva."""
    global processamento_ativo

    logger.info("Requisicao recebida em /api/processar-local")

    if processamento_ativo:
        return jsonify({"sucesso": False, "mensagem": "Um processamento ja esta em andamento"}), 409

    planilha_arquivo = request.files.get("planilha")
    planilha_token = (request.form.get("planilha_token") or "").strip() or None
    coverage_token = (request.form.get("coverage_token") or "").strip() or None
    coleta_token = (request.form.get("coleta_token") or "").strip() or None
    coverage_manifest = _COVERAGE_STAGING.load_manifest(coverage_token) if coverage_token else None
    coleta_manifest = _PROTHEUS_STAGING.load_manifest(coleta_token) if coleta_token else None

    if planilha_arquivo is None and planilha_token is None and coverage_manifest is None and coleta_manifest is None:
        return jsonify(
            {
                "sucesso": False,
                "mensagem": (
                    "Envie o arquivo 'planilha', informe um planilha_token valido, "
                    "use um coverage_token valido ou use um coleta_token valido"
                ),
            }
        ), 400
    if coverage_token and not coverage_manifest:
        return jsonify({"sucesso": False, "mensagem": "coverage_token expirou. Revalide a cobertura do lote."}), 400
    if coleta_token and not coleta_manifest:
        return jsonify({"sucesso": False, "mensagem": "coleta_token expirou. Refaça a coleta Protheus."}), 400
    if coverage_manifest and not coverage_manifest.get("ready_for_processing"):
        return jsonify(
            {
                "sucesso": False,
                "mensagem": "coverage_token bloqueado. Corrija os itens faltantes na validacao de cobertura antes de processar.",
            }
        ), 400

    boletos_pdf_arquivo = request.files.get("boletos_pdf")
    tipo_separacao = (request.form.get("tipo_separacao") or "placa").strip()
    baixar_pdf = (request.form.get("baixar_pdf") or "true").lower() == "true"
    baixar_xml = (request.form.get("baixar_xml") or "false").lower() == "true"
    juntar_pdfs = (request.form.get("juntar_pdfs") or "false").lower() == "true"
    separar_em_pastas = (request.form.get("separar_em_pastas") or "true").lower() == "true"
    metodo_pdf = (request.form.get("metodo_pdf") or "api").strip()
    filtro_rotas = _parse_json_list(request.form.get("filtro_rotas"))
    filtro_placas = _parse_json_list(request.form.get("filtro_placas"))
    filtro_clientes = _parse_json_list(request.form.get("filtro_clientes"))

    if tipo_separacao not in {"placa", "rota"}:
        return jsonify({"sucesso": False, "mensagem": "tipo_separacao deve ser 'placa' ou 'rota'"}), 400

    pasta_xmls = (
        str(coverage_manifest.get("processing_xml_dir") or "").strip()
        if coverage_manifest
        else (
        str(coleta_manifest.get("processing_xml_dir") or coleta_manifest.get("xml_dir") or "").strip()
        if coleta_manifest
        else obter_pasta_xmls_salva()
        )
    )
    if not pasta_xmls:
        return jsonify(
            {
                "sucesso": False,
                "mensagem": (
                    "Pasta de XMLs nao configurada. Defina em /api/ui/pasta-xmls/set."
                    if not coleta_manifest and not coverage_manifest
                    else "A validacao de cobertura nao possui XMLs prontos para processamento."
                    if coverage_manifest
                    else "A coleta Protheus nao possui XMLs prontos para processamento."
                ),
            }
        ), 400
    if coverage_manifest:
        filtro_rotas = list(coverage_manifest.get("filtro_rotas") or [])
        filtro_placas = list(coverage_manifest.get("filtro_placas") or [])
        filtro_clientes = list(coverage_manifest.get("filtro_clientes") or [])
        metodo_pdf = str(coverage_manifest.get("metodo_pdf_resolved") or metodo_pdf).strip()
    elif coleta_manifest:
        filtro_rotas = list(coleta_manifest.get("filtro_rotas") or [])
        filtro_placas = list(coleta_manifest.get("filtro_placas") or [])
        filtro_clientes = list(coleta_manifest.get("filtro_clientes") or [])

    try:
        output_path = _output_base_dir()
        output_path.mkdir(parents=True, exist_ok=True)
        _cleanup_stale_temp_dirs()

        planilha_path: Path | None = None
        boletos_pdf_path: Path | None = None
        alocacoes_precarregadas = None
        run_dir: Path | None = None

        if coverage_manifest:
            planilha_cache_token = str(coverage_manifest.get("planilha_token") or planilha_token or "").strip()
            if planilha_cache_token:
                _cleanup_planilha_cache()
                cached = _PLANILHA_CACHE.get(planilha_cache_token)
                if cached:
                    _touch_planilha_cache_entry(planilha_cache_token)
                    alocacoes_precarregadas = cached.get("alocacoes")
            planilha_path = Path(str(coverage_manifest.get("planilha_path") or ""))
            boleto_manifest = str(coverage_manifest.get("boleto_pdf_path") or "").strip()
            boletos_pdf_path = Path(boleto_manifest) if boleto_manifest else None
            if boletos_pdf_path is None and boletos_pdf_arquivo is not None and (boletos_pdf_arquivo.filename or "").strip():
                run_dir = Path(tempfile.mkdtemp(prefix="ultradanfe_local_", dir=str(output_path)))
                uploads_dir = run_dir / "uploads"
                uploads_dir.mkdir(parents=True, exist_ok=True)
                boletos_nome = Path(boletos_pdf_arquivo.filename or "boletos.pdf").name
                boletos_pdf_path = uploads_dir / boletos_nome
                boletos_pdf_arquivo.save(boletos_pdf_path)
        elif planilha_token:
            _cleanup_planilha_cache()
            cached = _PLANILHA_CACHE.get(planilha_token)
            if cached:
                _touch_planilha_cache_entry(planilha_token)

                planilha_path = Path(str(cached.get("planilha_path") or ""))
                alocacoes_precarregadas = cached.get("alocacoes")
            elif not coleta_manifest:
                return jsonify(
                    {"sucesso": False, "mensagem": "Token de planilha expirou. Selecione a planilha novamente."}
                ), 400

            if (
                coleta_manifest is None
                and boletos_pdf_arquivo is not None
                and (boletos_pdf_arquivo.filename or "").strip()
            ):
                run_dir = Path(tempfile.mkdtemp(prefix="ultradanfe_local_", dir=str(output_path)))
                uploads_dir = run_dir / "uploads"
                uploads_dir.mkdir(parents=True, exist_ok=True)
                boletos_nome = Path(boletos_pdf_arquivo.filename or "boletos.pdf").name
                boletos_pdf_path = uploads_dir / boletos_nome
                boletos_pdf_arquivo.save(boletos_pdf_path)
        elif planilha_arquivo is not None:
            run_dir = Path(tempfile.mkdtemp(prefix="ultradanfe_local_", dir=str(output_path)))
            uploads_dir = run_dir / "uploads"
            uploads_dir.mkdir(parents=True, exist_ok=True)

            planilha_nome = Path(planilha_arquivo.filename or "planilha.xlsx").name
            planilha_path = uploads_dir / planilha_nome
            planilha_arquivo.save(planilha_path)

            if boletos_pdf_arquivo is not None and (boletos_pdf_arquivo.filename or "").strip():
                boletos_nome = Path(boletos_pdf_arquivo.filename or "boletos.pdf").name
                boletos_pdf_path = uploads_dir / boletos_nome
                boletos_pdf_arquivo.save(boletos_pdf_path)

        if coleta_manifest and not coverage_manifest:
            if planilha_path is None:
                planilha_path = Path(str(coleta_manifest.get("planilha_path") or ""))
            boleto_manifest = str(coleta_manifest.get("boleto_pdf_path") or "").strip()
            boletos_pdf_path = Path(boleto_manifest) if boleto_manifest else None

        if planilha_path is None or not planilha_path.exists():
            return jsonify({"sucesso": False, "mensagem": "Planilha nao encontrada para processamento"}), 400
        if boletos_pdf_path is not None and not boletos_pdf_path.exists():
            return jsonify({"sucesso": False, "mensagem": f"PDF de boletos nao encontrado: {boletos_pdf_path}"}), 400
        if not Path(pasta_xmls).exists():
            return jsonify({"sucesso": False, "mensagem": f"Pasta nao encontrada: {pasta_xmls}"}), 400

        logger.info(
            "Processamento local: "
            f"planilha={planilha_path} pasta_xmls={pasta_xmls} boletos_pdf={boletos_pdf_path}"
        )
        logger.info(
            "Config: "
            f"tipo={tipo_separacao}, pdf={baixar_pdf}, xml={baixar_xml}, "
            f"juntar_pdfs={juntar_pdfs}, metodo_pdf={metodo_pdf}, "
            f"separar_em_pastas={separar_em_pastas}"
        )

        processamento_ativo = True
        set_progresso(etapa="Iniciando", percentual=0, mensagem="Preparando processamento...", detalhes="")

        orquestrador = Orquestrador()
        sucesso, _ = orquestrador.processar_planilha(
            str(planilha_path),
            tipo_separacao,
            baixar_pdf,
            baixar_xml,
            metodo_pdf=metodo_pdf,
            pasta_xmls=str(pasta_xmls),
            juntar_pdfs=juntar_pdfs,
            caminho_boletos_pdf=str(boletos_pdf_path) if boletos_pdf_path is not None else None,
            filtro_rotas=filtro_rotas,
            filtro_placas=filtro_placas,
            filtro_clientes=filtro_clientes,
            alocacoes_precarregadas=alocacoes_precarregadas,
            separar_em_pastas=separar_em_pastas,
        )

        resumo = orquestrador.obter_resumo()
        return jsonify(
            {
                "sucesso": sucesso,
                "mensagem": "Processamento concluido" if sucesso else "Processamento com erros",
                "resumo": resumo,
                "timestamp": datetime.now().isoformat(),
            }
        )
    except Exception as error:
        logger.error(f"Erro no endpoint /api/processar-local: {error}")
        return jsonify({"sucesso": False, "mensagem": f"Erro: {error}"}), 500
    finally:
        processamento_ativo = False
        if run_dir is not None:
            _safe_rmtree(run_dir)


@app.errorhandler(404)
def nao_encontrado(error):
    return jsonify({"sucesso": False, "mensagem": "Endpoint nao encontrado"}), 404


@app.errorhandler(500)
def erro_interno(error):
    logger.error(f"Erro interno: {error}")
    return jsonify({"sucesso": False, "mensagem": "Erro interno do servidor"}), 500


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    """Serve o frontend buildado."""
    if not STATIC_FOLDER or not STATIC_FOLDER.exists():
        return jsonify(
            {
                "sucesso": False,
                "mensagem": "Frontend nao disponivel. Use o servidor de desenvolvimento.",
            }
        ), 404

    if path.startswith("api/"):
        return jsonify({"sucesso": False, "mensagem": "Endpoint nao encontrado"}), 404

    if path and (STATIC_FOLDER / path).exists():
        return send_from_directory(STATIC_FOLDER, path)

    return send_from_directory(STATIC_FOLDER, "index.html")


from services.historico_service import HistoricoService

@app.route("/api/historico/listar", methods=["GET"])
def listar_historico():
    limit = request.args.get("limit", default=50, type=int)
    offset = request.args.get("offset", default=0, type=int)
    processamentos = HistoricoService.listar_processamentos(limit, offset)
    
    res = []
    for p in processamentos:
        res.append({
            "uuid": p.uuid,
            "timestamp": p.timestamp.isoformat(),
            "planilha_nome": p.planilha_nome,
            "status": p.status,
            "resumo": p.resumo
        })
    return jsonify(res)

@app.route("/api/historico/detalhes/<p_uuid>", methods=["GET"])
def detalhes_historico(p_uuid):
    detalhes = HistoricoService.obter_detalhes(p_uuid)
    if not detalhes:
        return jsonify({"error": "Processamento não encontrado"}), 404
    return jsonify(detalhes)

@app.route("/api/historico/buscar/<chave>", methods=["GET"])
def buscar_por_chave(chave):
    resultados = HistoricoService.buscar_por_chave(chave)
    return jsonify(resultados)

@app.route("/api/historico/download/<p_uuid>/<tipo>/<chave>", methods=["GET"])
def download_arquivo_historico(p_uuid, tipo, chave):
    detalhes = HistoricoService.obter_detalhes(p_uuid)
    if not detalhes:
        return "Processamento não encontrado", 404
    
    from models.historico import ArquivoProcessado, Processamento
    from models.database import SessionLocal
    
    db = SessionLocal()
    try:
        p = db.query(Processamento).filter(Processamento.uuid == p_uuid).first()
        if not p:
            return "Processamento não encontrado", 404
            
        arq = db.query(ArquivoProcessado).filter(
            ArquivoProcessado.processamento_id == p.id,
            ArquivoProcessado.chave_nfe == chave,
            ArquivoProcessado.tipo == tipo
        ).first()
        
        if not arq or not arq.caminho_local:
            return "Arquivo não encontrado", 404
            
        path = Path(arq.caminho_local)
        if not path.exists():
            return "Arquivo não encontrado no disco", 404
            
        return send_from_directory(path.parent, path.name)
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("Iniciando API Flask...")
    multiprocessing.freeze_support()
    app.run(debug=False, host="0.0.0.0", port=5000)
