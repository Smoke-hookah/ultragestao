"""Histórico/cache de boletos extraídos.

Objetivo:
- Persistir um mapeamento eficiente (compacto) entre uma NF-e (chave de acesso)
  e as páginas do boleto dentro de um PDF de origem.
- Reaproveitar boletos em novas execuções sem precisar reenviar o PDF.

Estratégia de espaço:
- Guardar somente UMA cópia do PDF de boletos por hash (sha256) em disco.
- Guardar no SQLite apenas: chave, nf (texto), últimos 5 dígitos (nf5), hash do PDF e páginas.

O PDF final de cada execução continua sendo gerado normalmente na pasta output/.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import time
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config import CONFIG_DIR
from utils.logger import logger

BOLETO_EXTRACTION_CACHE_VERSION = 1


def _sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


@dataclass
class HistoricoBoletos:
    db_path: Path
    sources_dir: Path

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.sources_dir.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(str(self.db_path))
        con.execute("PRAGMA journal_mode=WAL;")
        con.execute("PRAGMA synchronous=NORMAL;")
        con.row_factory = sqlite3.Row
        self._ensure_schema(con)
        return con

    def _ensure_schema(self, con: sqlite3.Connection) -> None:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS boleto_sources (
              hash TEXT PRIMARY KEY,
              filename TEXT,
              size_bytes INTEGER,
              created_ts INTEGER
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS boleto_map (
              chave TEXT PRIMARY KEY,
              nota TEXT,
              nf5 TEXT,
              doc_digits TEXT,
              source_hash TEXT,
              pages_json TEXT,
              updated_ts INTEGER
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS boleto_extraction_cache (
              source_hash TEXT PRIMARY KEY,
              extractor_version INTEGER NOT NULL,
              page_count INTEGER NOT NULL DEFAULT 0,
              documents_json TEXT NOT NULL,
              unidentified_pages_json TEXT NOT NULL,
              updated_ts INTEGER NOT NULL
            )
            """
        )
        con.execute("CREATE INDEX IF NOT EXISTS idx_boleto_map_nf5 ON boleto_map(nf5);")
        con.execute("CREATE INDEX IF NOT EXISTS idx_boleto_map_source ON boleto_map(source_hash);")
        con.commit()

    def registrar_pdf_origem(self, caminho_pdf: str) -> Optional[str]:
        """Registra (e cacheia) o PDF de boletos por hash; retorna o hash."""
        try:
            src = Path(caminho_pdf)
            if not src.exists() or not src.is_file():
                return None

            file_hash = _sha256_file(src)
            dst = self.sources_dir / f"{file_hash}.pdf"

            with closing(self._connect()) as con:
                row = con.execute(
                    "SELECT hash FROM boleto_sources WHERE hash = ?",
                    (file_hash,),
                ).fetchone()

                if not row:
                    if not dst.exists():
                        shutil.copy2(str(src), str(dst))

                    size = dst.stat().st_size if dst.exists() else src.stat().st_size
                    con.execute(
                        "INSERT OR IGNORE INTO boleto_sources(hash, filename, size_bytes, created_ts) VALUES(?,?,?,?)",
                        (file_hash, src.name, int(size), int(time.time())),
                    )
                    con.commit()

            return file_hash
        except Exception as e:
            logger.warning(f"Não foi possível registrar PDF de boletos no histórico: {e}")
            return None

    def caminho_pdf_cache(self, source_hash: str) -> Path:
        return self.sources_dir / f"{source_hash}.pdf"

    def registrar_extracao_pdf(
        self,
        source_hash: str,
        documentos: List[Dict[str, Any]],
        nao_identificadas: List[int],
    ) -> bool:
        """Persiste a extracao estruturada de um PDF de boletos por hash."""
        try:
            source_hash_s = str(source_hash).strip()
            if not source_hash_s:
                return False

            payload_documentos = json.dumps(documentos, ensure_ascii=False, separators=(",", ":"))
            payload_nao_identificadas = json.dumps(
                [int(p) for p in nao_identificadas],
                separators=(",", ":"),
            )
            page_count = sum(len(doc.get("pages") or []) for doc in documentos)

            with closing(self._connect()) as con:
                con.execute(
                    """
                    INSERT INTO boleto_extraction_cache(
                      source_hash,
                      extractor_version,
                      page_count,
                      documents_json,
                      unidentified_pages_json,
                      updated_ts
                    )
                    VALUES(?,?,?,?,?,?)
                    ON CONFLICT(source_hash) DO UPDATE SET
                      extractor_version=excluded.extractor_version,
                      page_count=excluded.page_count,
                      documents_json=excluded.documents_json,
                      unidentified_pages_json=excluded.unidentified_pages_json,
                      updated_ts=excluded.updated_ts
                    """,
                    (
                        source_hash_s,
                        BOLETO_EXTRACTION_CACHE_VERSION,
                        int(page_count),
                        payload_documentos,
                        payload_nao_identificadas,
                        int(time.time()),
                    ),
                )
                con.commit()
            return True
        except Exception as e:
            logger.warning(f"Não foi possível registrar extração de boletos no histórico: {e}")
            return False

    def obter_extracao_pdf(self, source_hash: str) -> Optional[Dict[str, Any]]:
        """Retorna a extracao estruturada do PDF se o cache estiver valido."""
        try:
            source_hash_s = str(source_hash).strip()
            if not source_hash_s:
                return None

            with closing(self._connect()) as con:
                row = con.execute(
                    """
                    SELECT source_hash, extractor_version, page_count, documents_json,
                           unidentified_pages_json, updated_ts
                    FROM boleto_extraction_cache
                    WHERE source_hash = ?
                    """,
                    (source_hash_s,),
                ).fetchone()
                if not row:
                    return None
                if int(row["extractor_version"] or 0) != BOLETO_EXTRACTION_CACHE_VERSION:
                    return None

                documentos = json.loads(row["documents_json"] or "[]")
                nao_identificadas = json.loads(row["unidentified_pages_json"] or "[]")
                if not isinstance(documentos, list) or not isinstance(nao_identificadas, list):
                    return None

                return {
                    "source_hash": source_hash_s,
                    "documentos": documentos,
                    "nao_identificadas": [int(p) for p in nao_identificadas],
                    "page_count": int(row["page_count"] or 0),
                    "updated_ts": int(row["updated_ts"] or 0),
                }
        except Exception as e:
            logger.warning(f"Não foi possível consultar cache da extração de boletos: {e}")
            return None

    def registrar_boleto(
        self,
        chave: str,
        nota: str,
        source_hash: str,
        paginas: List[int],
        doc_digits: Optional[str] = None,
    ) -> bool:
        """Upsert do mapeamento chave -> (source_hash, paginas)."""
        try:
            chave_s = str(chave).strip()
            if not chave_s or not source_hash or not paginas:
                return False

            nota_s = str(nota or "").strip()
            nf_digits = "".join(ch for ch in nota_s if ch.isdigit())
            nf5 = nf_digits[-5:] if len(nf_digits) >= 5 else ""

            pages_json = json.dumps(sorted(set(int(p) for p in paginas)), separators=(",", ":"))
            doc_s = str(doc_digits).strip() if doc_digits else ""

            with closing(self._connect()) as con:
                con.execute(
                    """
                    INSERT INTO boleto_map(chave, nota, nf5, doc_digits, source_hash, pages_json, updated_ts)
                    VALUES(?,?,?,?,?,?,?)
                    ON CONFLICT(chave) DO UPDATE SET
                      nota=excluded.nota,
                      nf5=excluded.nf5,
                      doc_digits=excluded.doc_digits,
                      source_hash=excluded.source_hash,
                      pages_json=excluded.pages_json,
                      updated_ts=excluded.updated_ts
                    """,
                    (
                        chave_s,
                        nota_s,
                        nf5,
                        doc_s,
                        source_hash,
                        pages_json,
                        int(time.time()),
                    ),
                )
                con.commit()
            return True
        except Exception as e:
            logger.warning(f"Não foi possível registrar boleto no histórico: {e}")
            return False

    def obter_por_chave(self, chave: str) -> Optional[Dict[str, Any]]:
        """Retorna {'source_path','pages','nota','nf5'} ou None."""
        try:
            chave_s = str(chave).strip()
            if not chave_s:
                return None

            with closing(self._connect()) as con:
                row = con.execute(
                    "SELECT chave, nota, nf5, doc_digits, source_hash, pages_json, updated_ts FROM boleto_map WHERE chave = ?",
                    (chave_s,),
                ).fetchone()
                if not row:
                    return None

                source_hash = str(row["source_hash"])
                src_path = self.caminho_pdf_cache(source_hash)
                if not src_path.exists():
                    return None

                pages = json.loads(row["pages_json"] or "[]")
                if not isinstance(pages, list) or not pages:
                    return None

                return {
                    "chave": row["chave"],
                    "nota": row["nota"],
                    "nf5": row["nf5"],
                    "doc_digits": row["doc_digits"],
                    "source_hash": source_hash,
                    "source_path": str(src_path),
                    "pages": [int(p) for p in pages],
                    "updated_ts": row["updated_ts"],
                }
        except Exception as e:
            logger.warning(f"Não foi possível consultar histórico de boletos: {e}")
            return None

    def obter_por_nf5(self, nf5: str, limite: int = 10) -> List[Dict[str, Any]]:
        """Consulta auxiliar (pode retornar múltiplos resultados)."""
        out: List[Dict[str, Any]] = []
        try:
            nf5_s = "".join(ch for ch in str(nf5) if ch.isdigit())
            if len(nf5_s) != 5:
                return []

            with closing(self._connect()) as con:
                rows = con.execute(
                    """
                    SELECT chave, nota, nf5, doc_digits, source_hash, pages_json, updated_ts
                    FROM boleto_map
                    WHERE nf5 = ?
                    ORDER BY updated_ts DESC
                    LIMIT ?
                    """,
                    (nf5_s, int(limite)),
                ).fetchall()

                for row in rows:
                    source_hash = str(row["source_hash"])
                    src_path = self.caminho_pdf_cache(source_hash)
                    if not src_path.exists():
                        continue
                    pages = json.loads(row["pages_json"] or "[]")
                    if not isinstance(pages, list) or not pages:
                        continue
                    out.append(
                        {
                            "chave": row["chave"],
                            "nota": row["nota"],
                            "nf5": row["nf5"],
                            "doc_digits": row["doc_digits"],
                            "source_hash": source_hash,
                            "source_path": str(src_path),
                            "pages": [int(p) for p in pages],
                            "updated_ts": row["updated_ts"],
                        }
                    )
            return out
        except Exception as e:
            logger.warning(f"Não foi possível consultar histórico de boletos por nf5: {e}")
            return []


def criar_historico_boletos_padrao() -> HistoricoBoletos:
    base = CONFIG_DIR / "historico_boletos"
    return HistoricoBoletos(
        db_path=base / "boletos.sqlite3",
        sources_dir=base / "sources",
    )
