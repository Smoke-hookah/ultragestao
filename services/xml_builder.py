"""Construtor de XML para requisições."""

from xml.dom import minidom
from utils.logger import logger


class ConstrutorXML:
    """Constrói XMLs no formato esperado pela API Meu Danfe."""
    
    @staticmethod
    def formatar_xml(xml_string: str) -> str:
        """
        Formata e valida um XML.
        
        Args:
            xml_string: XML em string
            
        Returns:
            XML formatado em string
        """
        try:
            # Parsar e reindentificar
            dom = minidom.parseString(xml_string)
            pretty_xml = dom.toprettyxml(indent="  ")
            
            # Remove a primeira linha de declaração se duplicada e linhas em branco
            linhas = pretty_xml.split('\n')
            if linhas[0].startswith('<?xml'):
                linhas = linhas[1:]  # Mantém a primeira linha
            else:
                linhas = [line for line in linhas if line.strip()]
            
            resultado = '\n'.join(linhas)
            return resultado.strip()
        except Exception as e:
            logger.error(f"Erro ao formatar XML: {e}")
            return xml_string
    
    @staticmethod
    def validar_xml(xml_string: str) -> bool:
        """
        Valida se o XML é bem formado.
        
        Args:
            xml_string: XML em string
            
        Returns:
            True se válido, False caso contrário
        """
        try:
            minidom.parseString(xml_string)
            return True
        except Exception as e:
            logger.error(f"XML inválido: {e}")
            return False
    
    @staticmethod
    def extrair_chave_do_xml(xml_string: str) -> str:
        """
        Extrai a chave de acesso do XML.
        
        Args:
            xml_string: XML em string
            
        Returns:
            Chave de acesso ou string vazia se não encontrada
        """
        try:
            dom = minidom.parseString(xml_string)
            
            # Procura por <chNFe>
            elementos = dom.getElementsByTagName("chNFe")
            if elementos:
                chave = elementos[0].firstChild.nodeValue
                return str(chave).strip()
            
            logger.warning("Chave de acesso não encontrada no XML")
            return ""
        except Exception as e:
            logger.error(f"Erro ao extrair chave do XML: {e}")
            return ""
