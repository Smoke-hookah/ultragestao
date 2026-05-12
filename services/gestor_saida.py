"""Gestor de saida de arquivos."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
import re
import tempfile
import io

from pypdf import PdfReader, PdfWriter

from config import OUTPUT_DIR
from utils.logger import logger


class GestorSaida:
    """Gerencia a estrutura de saida de PDFs e XMLs."""

    # Estrutura: DATA_HORA_EXECUCAO / TIPO_SEPARACAO / VALOR_SEPARACAO / {pdf, xml}

    def __init__(self):
        """Inicializa o gestor."""
        self.output_base = OUTPUT_DIR
        self.execucao_timestamp: Optional[str] = None
        self._estruturas_logadas: set[str] = set()
        self._docling_converter: Optional[Any] = None
        self._docling_indisponivel = False
        self._rapidocr_engine: Optional[Any] = None
        self._rapidocr_indisponivel = False

    def _get_docling_converter(self) -> Optional[Any]:
        """Inicializa o Docling sob demanda para OCR/extracao mais robusta."""
        if self._docling_indisponivel:
            return None
        if self._docling_converter is not None:
            return self._docling_converter

        try:
            import logging
            from docling.document_converter import DocumentConverter

            logging.getLogger("RapidOCR").setLevel(logging.WARNING)
            logging.getLogger("rapidocr").setLevel(logging.WARNING)
            logging.getLogger("docling").setLevel(logging.WARNING)

            self._docling_converter = DocumentConverter()
            logger.info("Docling carregado para leitura de boletos.")
            return self._docling_converter
        except Exception as e:
            self._docling_indisponivel = True
            logger.warning(f"Docling indisponivel para leitura de boletos: {e}")
            return None

    def _normalizar_documento_boleto(self, valor: str) -> Optional[str]:
        original_limpo = str(valor or "").strip()
        # Se for explicitamente uma data formatada, rejeita
        if re.fullmatch(r"\d{2}[/\-]\d{2}[/\-]\d{4}", original_limpo):
            return None

        digits = re.sub(r"\D", "", original_limpo)
        if 5 <= len(digits) <= 20:
            # Rejeita datas concatenadas (DDMMAAAA) que costumam confundir (Data Proc)
            if len(digits) == 8:
                try:
                    dia = int(digits[:2])
                    mes = int(digits[2:4])
                    ano = int(digits[4:])
                    if 1 <= dia <= 31 and 1 <= mes <= 12 and 1900 <= ano <= 2100:
                        return None
                except ValueError:
                    pass
            return digits
        return None

    def _extrair_candidatos_documento(self, texto: str) -> List[str]:
        """Extrai candidatos ao numero do documento do boleto."""
        texto_norm = str(texto or "").replace("\x00", " ")
        if not texto_norm.strip():
            return []

        padroes = [
            # Bradesco: "N° do documento" / "N.o do documento" / "No do documento"
            re.compile(
                r"N\s*(?:[^\w\s]|o|º|°)?\s*(?:do\s*)?documento\s*[:\-]?\s*([0-9][0-9\-\./]*)",
                re.IGNORECASE,
            ),
            # Santander: "No Documento" separado do valor por newline (table cell)
            # Captura número logo apos o label, mesmo com espacos internos tipo "1  000244416001"
            re.compile(
                r"No?\s*(?:do?\s*)?Documento\s*[:\-]?\s*[\r\n\s]*([0-9][0-9\s\-\./]{3,}[0-9])",
                re.IGNORECASE,
            ),
            re.compile(
                r"n(?:u|ú)?m(?:ero|\.)?\s+do\s+documento\s*[:\-]?\s*([0-9][0-9\-\./]*)",
                re.IGNORECASE,
            ),
            re.compile(
                r"n(?:u|ú)?m(?:ero|\.)?\s+documento\s*[:\-]?\s*([0-9][0-9\-\./]*)",
                re.IGNORECASE,
            ),
            re.compile(
                r"seu\s+n(?:u|ú)?m(?:ero|\.)?\s*[:\-]?\s*([0-9][0-9\-\./]*)",
                re.IGNORECASE,
            ),
            re.compile(
                r"nosso\s+n(?:u|ú)?m(?:ero|\.)?\s*[:\-]?\s*([0-9][0-9\-\./]*)",
                re.IGNORECASE,
            ),
        ]

        candidatos: List[str] = []
        vistos: set[str] = set()
        for padrao in padroes:
            for match in padrao.finditer(texto_norm):
                raw = str(match.group(1) or "")
                # Remove espacos internos antes de normalizar (ex: "1  000244416001")
                raw_sem_espacos = re.sub(r"\s+", "", raw)
                documento = self._normalizar_documento_boleto(raw_sem_espacos)
                if not documento or documento in vistos:
                    continue
                vistos.add(documento)
                candidatos.append(documento)

        return candidatos

    def _extrair_numero_documento(self, texto: str) -> Optional[str]:
        """Extrai os digitos do numero do documento do boleto."""
        candidatos = self._extrair_candidatos_documento(texto)
        return candidatos[0] if candidatos else None

    def _mesclar_textos(self, *textos: str) -> str:
        """Une textos vindos de fontes diferentes sem repetir o mesmo bloco."""
        partes: List[str] = []
        vistos: set[str] = set()

        for texto in textos:
            bloco = str(texto or "").strip()
            if not bloco:
                continue
            chave = re.sub(r"\s+", " ", bloco)
            if chave in vistos:
                continue
            vistos.add(chave)
            partes.append(bloco)

        return "\n\n".join(partes)

    def _extrair_pagador(self, texto: str) -> str:
        """Extrai o nome do pagador do boleto."""
        texto_norm = str(texto or "")
        if not texto_norm.strip():
            return ""

        linhas = [
            re.sub(r"\s+", " ", linha).strip(" -")
            for linha in re.split(r"[\r\n]+", texto_norm)
            if str(linha).strip()
        ]

        for idx, linha in enumerate(linhas):
            if not re.search(r"^Pagador\s*:", linha, re.IGNORECASE):
                continue

            resto = re.sub(r"^Pagador\s*:\s*", "", linha, flags=re.IGNORECASE).strip()
            resto = re.split(r"(?:CNPJ/CPF|CPF/CNPJ|CNPJ|CPF)\s*:", resto, maxsplit=1, flags=re.IGNORECASE)[0].strip()
            if resto and not re.search(r"(?:INSTRU|RECIBO|AUTENTI)", resto, re.IGNORECASE):
                return resto[:180]

            for prox in linhas[idx + 1 : idx + 6]:
                candidato = re.split(
                    r"(?:CNPJ/CPF|CPF/CNPJ|CNPJ|CPF)\s*:",
                    prox,
                    maxsplit=1,
                    flags=re.IGNORECASE,
                )[0].strip()
                if not candidato:
                    continue
                if re.search(r"(?:ENDERE|INSTRU|RECIBO|AUTENTI|NOME DO PAGADOR)", candidato, re.IGNORECASE):
                    continue
                return candidato[:180]

        padrao_fallback = re.compile(
            r"Nome do Pagador(?:/Avalista/CPF/CNPJ/Endere[cç]o)?\s*:\s*(?:\r?\n\s*){0,3}(.+?)(?:\r?\n\s*Instru|\r?\n\s*Recibo|\r?\n\s*Autent)",
            re.IGNORECASE | re.DOTALL,
        )
        match = padrao_fallback.search(texto_norm)
        if match:
            bruto = str(match.group(1) or "").strip()
            for linha in [re.sub(r"\s+", " ", item).strip(" -") for item in re.split(r"[\r\n]+", bruto) if str(item).strip()]:
                if re.search(r"(?:CNPJ|CPF|ENDERE|INSTRU|RECIBO|AUTENTI)", linha, re.IGNORECASE):
                    continue
                return linha[:180]

        return ""

    def _extrair_pagador_cnpj(self, texto: str) -> str:
        """Extrai o CNPJ/CPF do pagador quando presente no boleto."""
        texto_norm = str(texto or "")
        if not texto_norm.strip():
            return ""

        padroes = [
            re.compile(
                r"Pagador\s*:.*?(?:CNPJ/CPF|CPF/CNPJ|CNPJ|CPF)\s*:\s*([0-9.\-/]+)",
                re.IGNORECASE | re.DOTALL,
            ),
            re.compile(
                r"Nome do Pagador(?:/Avalista/CPF/CNPJ/Endere[cç]o)?\s*:.*?(?:CNPJ/CPF|CPF/CNPJ|CNPJ|CPF)\s*:\s*([0-9.\-/]+)",
                re.IGNORECASE | re.DOTALL,
            ),
            re.compile(r"(?:CNPJ/CPF|CPF/CNPJ)\s*:\s*([0-9.\-/]+)", re.IGNORECASE),
        ]

        for padrao in padroes:
            match = padrao.search(texto_norm)
            if not match:
                continue
            digits = re.sub(r"\D", "", str(match.group(1) or ""))
            if len(digits) in {11, 14}:
                return digits

        return ""

    def _parse_valor_brl(self, valor: str) -> Optional[float]:
        """Converte string monetaria brasileira em float."""
        bruto = str(valor or "").strip()
        if not bruto:
            return None

        bruto = re.sub(r"[^0-9,.\-]", "", bruto)
        if not bruto:
            return None

        if "," in bruto and "." in bruto:
            bruto = bruto.replace(".", "").replace(",", ".")
        elif "," in bruto:
            bruto = bruto.replace(",", ".")

        try:
            return float(bruto)
        except Exception:
            return None

    def _extrair_valor_documento(self, texto: str) -> Optional[float]:
        """Extrai o valor do documento do boleto."""
        texto_norm = str(texto or "")
        if not texto_norm.strip():
            return None

        padroes = [
            re.compile(
                r"Valor\s+do\s+documento\s*(?:\r?\n\s*){0,4}([0-9][0-9\.,]*)",
                re.IGNORECASE,
            ),
            re.compile(
                r"\(=\)\s*Valor\s+do\s+documento\s*(?:\r?\n\s*){0,4}([0-9][0-9\.,]*)",
                re.IGNORECASE,
            ),
        ]

        for padrao in padroes:
            match = padrao.search(texto_norm)
            if not match:
                continue
            valor = self._parse_valor_brl(match.group(1))
            if valor is not None:
                return valor

        return None

    def _extrair_blocos_numericos(self, texto: str) -> List[str]:
        """Extrai blocos numericos relevantes do texto do boleto."""
        texto_norm = str(texto or "")
        if not texto_norm.strip():
            return []

        blocos: set[str] = set(re.findall(r"\b\d{4,20}\b", texto_norm))

        for match in re.finditer(r"(?<!\d)(\d[\d.\-/]{2,}\d)(?!\d)", texto_norm):
            digits = re.sub(r"\D", "", str(match.group(1) or ""))
            if 4 <= len(digits) <= 20:
                blocos.add(digits)

        return sorted(blocos)

    def _get_rapidocr_engine(self) -> Optional[Any]:
        """Inicializa o motor RapidOCR sob demanda."""
        if self._rapidocr_indisponivel:
            return None
        if self._rapidocr_engine is not None:
            return self._rapidocr_engine
        try:
            import logging
            logging.getLogger("RapidOCR").setLevel(logging.WARNING)
            logging.getLogger("rapidocr").setLevel(logging.WARNING)
            from rapidocr import RapidOCR
            self._rapidocr_engine = RapidOCR()
            return self._rapidocr_engine
        except Exception as e:
            self._rapidocr_indisponivel = True
            logger.warning(f"RapidOCR indisponivel para OCR de boletos: {e}")
            return None

    def _extrair_texto_ocr_pagina(self, reader: PdfReader, page_index: int) -> str:
        """Usa RapidOCR para extrair texto de uma pagina via renderizacao em imagem.

        Util para PDFs com fontes customizadas (ex: Bradesco) onde pypdf/Docling falham.
        """
        engine = self._get_rapidocr_engine()
        if engine is None:
            return ""

        try:
            # Tenta renderizar a pagina como imagem usando pdf2image (poppler) ou fitz (pymupdf)
            img_array = None

            # Tentativa 1: pymupdf (fitz) — rápido, sem dependência externa
            try:
                import fitz  # type: ignore
                import numpy as np

                with tempfile.TemporaryDirectory(prefix="ultradanfe_ocr_") as tmpdir:
                    pagina_pdf = Path(tmpdir) / f"page-{page_index}.pdf"
                    writer = PdfWriter()
                    writer.add_page(reader.pages[page_index])
                    with open(pagina_pdf, "wb") as f:
                        writer.write(f)

                    doc_fitz = fitz.open(str(pagina_pdf))
                    page_fitz = doc_fitz[0]
                    mat = fitz.Matrix(2.0, 2.0)  # 2x zoom = ~144 DPI
                    pix = page_fitz.get_pixmap(matrix=mat, alpha=False)
                    img_bytes = pix.tobytes("png")
                    doc_fitz.close()

                from PIL import Image  # type: ignore
                img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                img_array = np.array(img)
            except Exception:
                img_array = None

            # Tentativa 2: pdf2image (poppler)
            if img_array is None:
                try:
                    import numpy as np
                    from pdf2image import convert_from_bytes  # type: ignore

                    writer = PdfWriter()
                    writer.add_page(reader.pages[page_index])
                    buf = io.BytesIO()
                    writer.write(buf)
                    buf.seek(0)

                    images = convert_from_bytes(buf.read(), dpi=150, first_page=1, last_page=1)
                    if images:
                        from PIL import Image  # type: ignore
                        img_array = np.array(images[0].convert("RGB"))
                except Exception:
                    img_array = None

            if img_array is None:
                return ""

            result = engine(img_array)
            if not result:
                return ""

            # Trata retorno nas versoes mais recentes do RapidOCR (objeto) e antigas (tupla)
            if hasattr(result, "txts") and result.txts:
                linhas = [t for t in result.txts if t]
            elif isinstance(result, tuple) and len(result) == 2:
                res = result[0]
                if res:
                    linhas = [item[1] for item in res if item and len(item) >= 2 and item[1]]
                else:
                    linhas = []
            elif isinstance(result, list):
                # Caso onde o result retornado for a propria lista
                linhas = [item[1] for item in result if item and len(item) >= 2 and item[1]]
            else:
                linhas = []
                
            return "\n".join(linhas)

        except Exception as e:
            logger.warning(f"OCR via RapidOCR falhou na pagina {page_index + 1}: {e}")
            return ""

    def _texto_e_apenas_imagem(self, texto: str) -> bool:
        """Retorna True quando o Docling retornou apenas marcadores de imagem sem texto util."""
        if not texto or not texto.strip():
            return True
        # Remove marcadores de imagem e espacos
        limpo = re.sub(r"<!--\s*image\s*-->", "", texto, flags=re.IGNORECASE).strip()
        return len(limpo) < 20

    def _extrair_texto_pagina_docling(self, reader: PdfReader, page_index: int) -> str:
        """Converte uma pagina isolada do PDF com o Docling.

        Se o Docling retornar apenas marcadores de imagem (PDFs com fontes customizadas
        como os do Bradesco), aplica OCR via RapidOCR como fallback.
        """
        converter = self._get_docling_converter()
        if converter is None:
            # Docling indisponivel: tenta OCR direto
            return self._extrair_texto_ocr_pagina(reader, page_index)

        try:
            with tempfile.TemporaryDirectory(prefix="ultradanfe_docling_") as tmpdir:
                pagina_pdf = Path(tmpdir) / f"boleto-page-{page_index + 1}.pdf"
                writer = PdfWriter()
                writer.add_page(reader.pages[page_index])
                with open(pagina_pdf, "wb") as handle:
                    writer.write(handle)

                result = converter.convert(pagina_pdf)
                document = getattr(result, "document", None)
                if document is None:
                    return self._extrair_texto_ocr_pagina(reader, page_index)

                texto = ""
                if hasattr(document, "export_to_text"):
                    texto = document.export_to_text() or ""
                if not texto and hasattr(document, "export_to_markdown"):
                    texto = document.export_to_markdown() or ""

                # Fallback para OCR quando Docling retorna apenas marcadores de imagem
                if self._texto_e_apenas_imagem(texto):
                    texto_ocr = self._extrair_texto_ocr_pagina(reader, page_index)
                    if texto_ocr.strip():
                        return texto_ocr

                return str(texto)
        except Exception as e:
            logger.warning(
                f"Docling falhou ao ler a pagina {page_index + 1} do PDF de boletos: {e}"
            )
            return self._extrair_texto_ocr_pagina(reader, page_index)

    def _anexar_pagina_documento(
        self,
        documento: Dict[str, Any],
        page_index: int,
        texto_pagina: str,
        pagador: str,
        pagador_cnpj: str,
        valor_documento: Optional[float],
        blocos_numericos: List[str],
        doc_candidates: List[str],
    ) -> None:
        """Atualiza um documento ja identificado com a pagina atual."""
        documento.setdefault("pages", []).append(page_index)
        documento["texto"] = self._mesclar_textos(str(documento.get("texto") or ""), texto_pagina)
        if not documento.get("pagador") and pagador:
            documento["pagador"] = pagador
        if not documento.get("pagador_cnpj") and pagador_cnpj:
            documento["pagador_cnpj"] = pagador_cnpj
        if documento.get("valor_documento") is None and valor_documento is not None:
            documento["valor_documento"] = valor_documento
        documento["numeric_blocks"] = sorted(
            set(documento.get("numeric_blocks") or []).union(blocos_numericos)
        )
        documento["doc_candidates"] = list(
            dict.fromkeys(list(documento.get("doc_candidates") or []) + list(doc_candidates))
        )
        if not documento.get("doc_digits") and documento.get("doc_candidates"):
            documento["doc_digits"] = documento["doc_candidates"][0]

    def extrair_documentos_boletos(self, caminho_pdf: str) -> Tuple[List[Dict[str, Any]], List[int]]:
        """Extrai documentos de boleto com texto enriquecido por Docling."""
        try:
            reader = PdfReader(str(caminho_pdf))
        except Exception as e:
            logger.error(f"Erro ao abrir PDF de boletos: {e}")
            return [], []

        documentos: List[Dict[str, Any]] = []
        nao_identificadas: List[int] = []
        doc_atual: Optional[Dict[str, Any]] = None
        paginas_docling = 0

        for idx, page in enumerate(reader.pages):
            try:
                texto_pdf = page.extract_text() or ""
            except Exception:
                texto_pdf = ""

            texto_docling = self._extrair_texto_pagina_docling(reader, idx)
            if texto_docling.strip():
                paginas_docling += 1

            texto_pagina = self._mesclar_textos(texto_pdf, texto_docling)
            doc_candidates = self._extrair_candidatos_documento(texto_pagina)
            doc_pagina = doc_candidates[0] if doc_candidates else None
            blocos_numericos = self._extrair_blocos_numericos(texto_pagina)
            pagador = self._extrair_pagador(texto_pagina)
            pagador_cnpj = self._extrair_pagador_cnpj(texto_pagina)
            valor_documento = self._extrair_valor_documento(texto_pagina)

            if doc_pagina:
                if doc_atual is not None:
                    atuais = set(doc_atual.get("doc_candidates") or [])
                    if doc_pagina in atuais or atuais.intersection(doc_candidates):
                        self._anexar_pagina_documento(
                            doc_atual,
                            idx,
                            texto_pagina,
                            pagador,
                            pagador_cnpj,
                            valor_documento,
                            blocos_numericos,
                            doc_candidates,
                        )
                        continue

                doc_atual = {
                    "doc_digits": doc_pagina,
                    "doc_candidates": doc_candidates,
                    "pages": [idx],
                    "texto": texto_pagina,
                    "pagador": pagador,
                    "pagador_cnpj": pagador_cnpj,
                    "valor_documento": valor_documento,
                    "numeric_blocks": blocos_numericos,
                    "anonimo": False,
                }
                documentos.append(doc_atual)
                continue

            if doc_atual is not None:
                self._anexar_pagina_documento(
                    doc_atual,
                    idx,
                    texto_pagina,
                    pagador,
                    pagador_cnpj,
                    valor_documento,
                    blocos_numericos,
                    doc_candidates,
                )
                continue

            nao_identificadas.append(idx)
            documentos.append(
                {
                    "doc_digits": None,
                    "doc_candidates": doc_candidates,
                    "pages": [idx],
                    "texto": texto_pagina,
                    "pagador": pagador,
                    "pagador_cnpj": pagador_cnpj,
                    "valor_documento": valor_documento,
                    "numeric_blocks": blocos_numericos,
                    "anonimo": True,
                }
            )

        if paginas_docling:
            logger.info(
                f"Boletos: Docling aplicado em {paginas_docling}/{len(reader.pages)} pagina(s)"
            )

        return documentos, nao_identificadas

    def iniciar_execucao(self, timestamp: Optional[str] = None) -> str:
        """Define o timestamp fixo da execucao usado em toda a saida."""
        if self.execucao_timestamp:
            return self.execucao_timestamp
        self.execucao_timestamp = timestamp or datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return self.execucao_timestamp

    def _safe_dir_name(self, valor: str) -> str:
        """Normaliza nomes de pastas para Windows."""
        s = str(valor).strip()
        if not s:
            return "(vazio)"
        for ch in '<>:"/\\|?*':
            s = s.replace(ch, "-")
        s = s.rstrip(" .")
        return s

    def _safe_file_stem(self, valor: str) -> str:
        """Normaliza nomes de arquivo sem extensao para Windows."""
        s = str(valor).strip()
        if not s:
            return "(vazio)"
        for ch in '<>:"/\\|?*':
            s = s.replace(ch, "-")
        s = s.rstrip(" .")
        return s

    def criar_estrutura_diretorios(
        self,
        tipo_separacao: str,
        valor_separacao: str,
        separar_em_pastas: bool = True,
    ) -> Path:
        """
        Cria a estrutura de diretorios para saida.

        Se separar_em_pastas for True:
        Estrutura: DATA_HORA_EXECUCAO / TIPO_SEPARACAO / VALOR_SEPARACAO

        Se separar_em_pastas for False:
        Estrutura: DATA_HORA_EXECUCAO
        """
        timestamp = self.iniciar_execucao()

        if separar_em_pastas:
            caminho = (
                self.output_base
                / timestamp
                / tipo_separacao
                / self._safe_dir_name(valor_separacao)
            )
        else:
            caminho = self.output_base / timestamp

        caminho.mkdir(parents=True, exist_ok=True)
        (caminho / "pdf").mkdir(exist_ok=True)
        (caminho / "xml").mkdir(exist_ok=True)

        caminho_s = str(caminho)
        if caminho_s not in self._estruturas_logadas:
            self._estruturas_logadas.add(caminho_s)
            logger.info(f"Estrutura de diretorios criada: {caminho}")
        return caminho

    def salvar_pdf(
        self,
        pdf_bytes: bytes,
        nome_planilha: str,
        tipo_separacao: str,
        valor_separacao: str,
        chave: str,
        separar_em_pastas: bool = True,
    ) -> Tuple[bool, str]:
        """Salva um PDF na estrutura correta."""
        try:
            estrutura = self.criar_estrutura_diretorios(
                tipo_separacao,
                valor_separacao,
                separar_em_pastas=separar_em_pastas,
            )

            nome_arquivo = f"NFE-{chave}.pdf"
            caminho_arquivo = estrutura / "pdf" / nome_arquivo

            with open(caminho_arquivo, "wb") as f:
                f.write(pdf_bytes)

            logger.info(f"PDF salvo: {caminho_arquivo}")
            return True, str(caminho_arquivo)

        except Exception as e:
            logger.error(f"Erro ao salvar PDF: {e}")
            return False, ""

    def salvar_xml(
        self,
        xml_string: str,
        nome_planilha: str,
        tipo_separacao: str,
        valor_separacao: str,
        chave: str,
        separar_em_pastas: bool = True,
    ) -> Tuple[bool, str]:
        """Salva um XML na estrutura correta."""
        try:
            estrutura = self.criar_estrutura_diretorios(
                tipo_separacao,
                valor_separacao,
                separar_em_pastas=separar_em_pastas,
            )

            nome_arquivo = f"NFE-{chave}.xml"
            caminho_arquivo = estrutura / "xml" / nome_arquivo

            with open(caminho_arquivo, "w", encoding="utf-8") as f:
                f.write(xml_string)

            logger.info(f"XML salvo: {caminho_arquivo}")
            return True, str(caminho_arquivo)

        except Exception as e:
            logger.error(f"Erro ao salvar XML: {e}")
            return False, ""

    def obter_estrutura_processamento(
        self,
        nome_planilha: str,
        tipo_separacao: str,
        valor_separacao: str,
    ) -> dict:
        """Obtem informacoes sobre a estrutura de um processamento."""
        timestamp = self.iniciar_execucao()

        return {
            "timestamp": timestamp,
            "planilha": nome_planilha,
            "tipo_separacao": tipo_separacao,
            "valor_separacao": str(valor_separacao),
            "caminho_base": str(self.output_base / timestamp),
        }

    def juntar_pdfs(
        self,
        pdf_paths: Iterable[str],
        caminho_saida: str,
        ordenar_por_nome: bool = True,
    ) -> Tuple[bool, str]:
        """Junta varios PDFs em um unico arquivo."""
        try:
            paths = [Path(p) for p in pdf_paths if p]
            paths = [p for p in paths if p.exists() and p.is_file()]
            if not paths:
                return False, "Nenhum PDF para juntar"

            if ordenar_por_nome:
                paths.sort(key=lambda p: p.name)

            writer = PdfWriter()
            for p in paths:
                reader = PdfReader(str(p))
                for page in reader.pages:
                    writer.add_page(page)

            out = Path(caminho_saida)
            out.parent.mkdir(parents=True, exist_ok=True)
            with open(out, "wb") as f:
                writer.write(f)

            logger.info(f"PDF unido salvo: {out}")
            return True, str(out)
        except Exception as e:
            logger.error(f"Erro ao juntar PDFs: {e}")
            return False, ""

    def extrair_paginas_boletos_por_nf(self, caminho_pdf: str) -> Tuple[Dict[str, List[int]], List[int]]:
        """Extrai um mapeamento NF -> indices de paginas do PDF de boletos."""
        documentos, nao_identificadas = self.extrair_documentos_boletos(caminho_pdf)
        por_nf: Dict[str, List[int]] = {}

        for documento in documentos:
            doc_digits = str(documento.get("doc_digits") or "").strip()
            paginas = [int(p) for p in (documento.get("pages") or []) if isinstance(p, int)]
            if not doc_digits or not paginas:
                continue
            por_nf.setdefault(doc_digits, []).extend(paginas)

        return por_nf, nao_identificadas

    def salvar_pdf_com_paginas(
        self,
        caminho_pdf_origem: str,
        paginas: List[int],
        caminho_pdf_saida: str,
    ) -> Tuple[bool, str]:
        """Salva um novo PDF contendo apenas as paginas informadas."""
        try:
            if not paginas:
                return False, "Sem paginas para salvar"

            reader = PdfReader(str(caminho_pdf_origem))
            writer = PdfWriter()

            for idx in paginas:
                if 0 <= idx < len(reader.pages):
                    writer.add_page(reader.pages[idx])

            out = Path(caminho_pdf_saida)
            out.parent.mkdir(parents=True, exist_ok=True)
            with open(out, "wb") as f:
                writer.write(f)

            return True, str(out)
        except Exception as e:
            logger.error(f"Erro ao salvar PDF por paginas: {e}")
            return False, ""
