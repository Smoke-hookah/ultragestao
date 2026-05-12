"""
Módulo para leitura de XMLs de uma pasta
"""

from pathlib import Path
import logging
from typing import Any, List, Dict, Tuple, Optional, Set

logger = logging.getLogger(__name__)


class LeitorXML:
    """Lê e processa XMLs de uma pasta"""
    
    def __init__(self, pasta_xmls: str):
        """
        Inicializa o leitor de XMLs
        
        Args:
            pasta_xmls: Caminho da pasta contendo XMLs
            
        Raises:
            ValueError: Se a pasta não existir ou não for um diretório
        """
        self.pasta_xmls = Path(pasta_xmls)
        
        if not self.pasta_xmls.exists():
            raise ValueError(f"Pasta não existe: {pasta_xmls}")
        
        if not self.pasta_xmls.is_dir():
            raise ValueError(f"Caminho não é um diretório: {pasta_xmls}")
        
        logger.info(f"Leitor de XMLs inicializado: {pasta_xmls}")
    
    def listar_xmls(self) -> List[Path]:
        """
        Lista todos os XMLs na pasta
        
        Returns:
            List[Path]: Lista de caminhos dos arquivos XML
        """
        xmls = list(self.pasta_xmls.glob("*.xml"))
        logger.info(f"Encontrados {len(xmls)} arquivos XML")
        return sorted(xmls)
    
    def ler_xml(self, arquivo: Path) -> Tuple[bool, str]:
        """
        Lê conteúdo de um arquivo XML
        
        Args:
            arquivo: Caminho do arquivo XML
            
        Returns:
            Tuple[bool, str]: (sucesso, conteúdo_ou_erro)
        """
        try:
            try:
                with open(arquivo, 'r', encoding='utf-8') as f:
                    conteudo = f.read()
            except UnicodeDecodeError:
                with open(arquivo, 'r', encoding='latin-1', errors='replace') as f:
                    conteudo = f.read()
            logger.debug(f"XML lido: {arquivo.name}")
            return True, conteudo
        except Exception as e:
            erro = f"Erro ao ler {arquivo.name}: {str(e)}"
            logger.error(erro)
            return False, erro

    def ler_preview_xml(self, arquivo: Path, max_chars: int = 8192) -> Tuple[bool, str]:
        """Lê só o começo do XML para validações baratas de tipo."""
        try:
            try:
                with open(arquivo, "r", encoding="utf-8") as f:
                    conteudo = f.read(max_chars)
            except UnicodeDecodeError:
                with open(arquivo, "r", encoding="latin-1", errors="replace") as f:
                    conteudo = f.read(max_chars)
            return True, conteudo
        except Exception as e:
            erro = f"Erro ao ler preview de {arquivo.name}: {str(e)}"
            logger.error(erro)
            return False, erro

    def xml_parece_nfe_renderizavel(self, xml: str) -> bool:
        """Filtra XMLs que realmente parecem DANFE/NF-e renderizavel."""
        texto = str(xml or "").strip().lower()
        if not texto:
            return False

        if "<retinutnfe" in texto or "<inutnfe" in texto:
            return False
        if "<proceventonfe" in texto or "<evento" in texto:
            return False

        return (
            "<infnfe" in texto
            or "<nfeproc" in texto
            or "<nfe " in texto
            or "<nfe>" in texto
        )

    def extrair_chave_do_conteudo(self, xml: str) -> Optional[str]:
        """Extrai chave de acesso do conteúdo XML (fallback quando o nome não ajuda)."""
        import re

        # Padrão comum: <chNFe>44-dígitos</chNFe>
        m = re.search(r"<chNFe>\s*(\d{44})\s*</chNFe>", xml)
        if m:
            return m.group(1)

        # Padrão comum: Id="NFe44-dígitos"
        m = re.search(r"Id\s*=\s*\"NFe(\d{44})\"", xml)
        if m:
            return m.group(1)

        # Último recurso: qualquer sequência de 44 dígitos
        m = re.search(r"\d{44}", xml)
        if m:
            return m.group(0)

        return None
    
    def extrair_chave_de_arquivo(self, arquivo: Path) -> Tuple[bool, str]:
        """
        Extrai a chave de acesso do nome do arquivo XML
        Assume formato: *NFE-44DIGITOS* ou similar
        
        Args:
            arquivo: Caminho do arquivo XML
            
        Returns:
            Tuple[bool, str]: (sucesso, chave_ou_erro)
        """
        nome = arquivo.stem  # Nome sem extensão
        
        # Procura por chave (44 dígitos) no nome.
        # Atenção: alguns XMLs de evento começam com código (ex.: 110111...) e a chave fica no meio.
        import re

        # Caso clássico: prefixo literal 'NFe'
        m = re.search(r"NFe(\d{44})", nome, flags=re.IGNORECASE)
        if m:
            chave = m.group(1)
            logger.debug(f"Chave extraída de {arquivo.name}: {chave}")
            return True, chave

        # Captura sobreposta (para sequências longas só de dígitos)
        candidatos = [m.group(1) for m in re.finditer(r"(?=(\d{44}))", nome)]
        if candidatos:
            # Preferir chave iniciando por 35 (SP) quando existir no nome
            for c in candidatos:
                if c.startswith("35"):
                    logger.debug(f"Chave extraída de {arquivo.name}: {c}")
                    return True, c
            chave = candidatos[0]
            logger.debug(f"Chave extraída de {arquivo.name}: {chave}")
            return True, chave
        
        logger.debug(f"Não foi possível extrair chave de: {arquivo.name}")
        return False, f"Formato inválido: {nome}"

    def carregar_mapa_chave_para_caminho(
        self,
        chaves_desejadas: Optional[Set[str]] = None
    ) -> Tuple[Dict[str, str], Dict[str, int]]:
        """Indexa XMLs da pasta e retorna um mapa {chave: caminho_arquivo}."""
        inventory = self.inventariar_chaves(chaves_desejadas)
        return inventory["mapa"], inventory["stats"]

    def inventariar_chaves(
        self,
        chaves_desejadas: Optional[Set[str]] = None,
    ) -> Dict[str, Any]:
        """Indexa XMLs e registra motivos detalhados para cobertura/auditoria."""
        xmls = self.listar_xmls()
        mapa: Dict[str, str] = {}
        duplicadas: Dict[str, List[str]] = {}
        nao_renderizaveis: Dict[str, List[str]] = {}
        erros_leitura: Dict[str, List[str]] = {}
        erros_sem_chave: List[str] = []
        lidos_conteudo = 0

        chaves_filtradas = None
        if chaves_desejadas:
            chaves_filtradas = {
                str(chave).strip() for chave in chaves_desejadas if str(chave).strip()
            }

        for arquivo in xmls:
            ok_nome, chave_ou_erro = self.extrair_chave_de_arquivo(arquivo)
            chave: Optional[str] = None

            if ok_nome:
                chave = str(chave_ou_erro).strip()
                ok_preview, preview_ou_erro = self.ler_preview_xml(arquivo)
                if not ok_preview:
                    if chave and (chaves_filtradas is None or chave in chaves_filtradas):
                        erros_leitura.setdefault(chave, []).append(str(arquivo))
                    else:
                        erros_sem_chave.append(str(arquivo))
                    continue

                if not self.xml_parece_nfe_renderizavel(preview_ou_erro):
                    if chave and (chaves_filtradas is None or chave in chaves_filtradas):
                        nao_renderizaveis.setdefault(chave, []).append(str(arquivo))
                    continue
            else:
                ok_ler, conteudo_ou_erro = self.ler_xml(arquivo)
                if not ok_ler:
                    erros_sem_chave.append(str(arquivo))
                    continue

                lidos_conteudo += 1
                chave = self.extrair_chave_do_conteudo(conteudo_ou_erro)
                if not chave:
                    erros_sem_chave.append(str(arquivo))
                    continue

                chave = str(chave).strip()
                if not self.xml_parece_nfe_renderizavel(conteudo_ou_erro):
                    if chaves_filtradas is None or chave in chaves_filtradas:
                        nao_renderizaveis.setdefault(chave, []).append(str(arquivo))
                    continue

            if not chave:
                erros_sem_chave.append(str(arquivo))
                continue

            if chaves_filtradas is not None and chave not in chaves_filtradas:
                continue

            if chave in mapa:
                paths = duplicadas.setdefault(chave, [mapa[chave]])
                paths.append(str(arquivo))
                continue

            mapa[chave] = str(arquivo)

        chaves_restantes = None
        if chaves_filtradas is not None:
            chaves_restantes = chaves_filtradas - set(mapa.keys())

        stats = {
            "total": len(xmls),
            "mapeadas": len(mapa),
            "duplicadas": sum(max(0, len(paths) - 1) for paths in duplicadas.values()),
            "erros": sum(len(paths) for paths in erros_leitura.values()) + len(erros_sem_chave),
            "lidos_conteudo": lidos_conteudo,
            "ignorados_tipo": sum(len(paths) for paths in nao_renderizaveis.values()),
            "filtradas": len(chaves_filtradas) if chaves_filtradas else 0,
            "faltantes": len(chaves_restantes) if chaves_restantes is not None else 0,
        }
        return {
            "mapa": mapa,
            "stats": stats,
            "duplicates": duplicadas,
            "non_renderable": nao_renderizaveis,
            "read_errors": erros_leitura,
            "unknown_read_errors": erros_sem_chave,
            "missing_keys": sorted(chaves_restantes) if chaves_restantes is not None else [],
        }
    
    def processar_todos_xmls(self) -> Dict:
        """
        Processa todos os XMLs da pasta
        
        Returns:
            Dict: {
                'total': int,
                'processados': int,
                'erros': int,
                'arquivos': [
                    {
                        'nome': str,
                        'caminho': str,
                        'chave': str,
                        'conteudo': str,
                        'sucesso': bool,
                        'erro': str
                    }
                ]
            }
        """
        resultado = {
            'total': 0,
            'processados': 0,
            'erros': 0,
            'arquivos': []
        }
        
        xmls = self.listar_xmls()
        resultado['total'] = len(xmls)
        
        for arquivo in xmls:
            item = {
                'nome': arquivo.name,
                'caminho': str(arquivo),
                'chave': None,
                'conteudo': None,
                'sucesso': False,
                'erro': None
            }
            
            # Lê conteúdo
            sucesso_leitura, conteudo_ou_erro = self.ler_xml(arquivo)
            
            if not sucesso_leitura:
                item['erro'] = conteudo_ou_erro
                resultado['erros'] += 1
                resultado['arquivos'].append(item)
                continue

            item['conteudo'] = conteudo_ou_erro

            if not self.xml_parece_nfe_renderizavel(conteudo_ou_erro):
                item['erro'] = "XML nao e NF-e renderizavel"
                resultado['erros'] += 1
                resultado['arquivos'].append(item)
                continue

            # Extrai chave (primeiro do nome, depois do conteúdo)
            sucesso_chave, chave_ou_erro = self.extrair_chave_de_arquivo(arquivo)
            if sucesso_chave:
                item['chave'] = chave_ou_erro
            else:
                chave_conteudo = self.extrair_chave_do_conteudo(conteudo_ou_erro)
                if chave_conteudo:
                    item['chave'] = chave_conteudo
                else:
                    item['erro'] = chave_ou_erro
                    resultado['erros'] += 1
                    resultado['arquivos'].append(item)
                    continue
            item['sucesso'] = True
            resultado['processados'] += 1
            resultado['arquivos'].append(item)
        
        return resultado

    def carregar_mapa_chave_para_xml(self) -> Tuple[Dict[str, str], Dict[str, int]]:
        """Carrega todos os XMLs e retorna um mapa {chave: conteudo} e contadores."""
        resultado = self.processar_todos_xmls()
        mapa: Dict[str, str] = {}
        duplicadas = 0
        for item in resultado.get('arquivos', []):
            if not item.get('sucesso'):
                continue
            chave = item.get('chave')
            conteudo = item.get('conteudo')
            if not chave or not conteudo:
                continue
            if chave in mapa:
                duplicadas += 1
                continue
            mapa[chave] = conteudo

        stats = {
            'total': int(resultado.get('total', 0)),
            'processados': int(resultado.get('processados', 0)),
            'erros': int(resultado.get('erros', 0)),
            'duplicadas': duplicadas,
            'mapeadas': len(mapa),
        }
        return mapa, stats
