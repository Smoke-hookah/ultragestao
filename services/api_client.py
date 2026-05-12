"""Cliente da API Meu Danfe."""

import requests
import time
from typing import Optional, Tuple
from pathlib import Path
from datetime import datetime

from config import (
    API_URL,
    API_KEY,
    DELAY_BETWEEN_REQUESTS,
    MAX_REQUESTS_PER_SECOND,
    PUT_DELAY_BETWEEN_REQUESTS,
    PUT_MAX_REQUESTS_PER_SECOND,
    GET_DELAY_BETWEEN_REQUESTS,
    GET_MAX_REQUESTS_PER_SECOND,
    REQUEST_TIMEOUT,
)
from utils.logger import logger
from models.alocacao import Alocacao, RespostaAPI
from services.xml_builder import ConstrutorXML


class ClienteAPI:
    """Cliente para integração com API Meu Danfe."""
    
    def __init__(self, api_key: str | None = None):
        """Inicializa o cliente da API."""
        self.url_base = API_URL
        self.api_key = api_key or API_KEY
        self.headers_base = {
            "Api-Key": self.api_key,
            "Content-Type": "text/plain"
        }
        self.session = requests.Session()
        self._proximo_request_em = {
            "default": 0.0,
            "put": 0.0,
            "get": 0.0,
        }
    
    def _respeitar_throttle(self, kind: str = "default"):
        """Respeita limites de requisição.

        - DELAY_BETWEEN_REQUESTS: piso de espera entre chamadas.
        - MAX_REQUESTS_PER_SECOND: teto de taxa (ex.: 5 => 1 req a cada 0.2s).

        O intervalo efetivo é max(DELAY_BETWEEN_REQUESTS, 1/MAX_REQUESTS_PER_SECOND).
        """
        if kind == "get":
            delay = GET_DELAY_BETWEEN_REQUESTS
            rps = GET_MAX_REQUESTS_PER_SECOND
        elif kind == "put":
            delay = PUT_DELAY_BETWEEN_REQUESTS
            rps = PUT_MAX_REQUESTS_PER_SECOND
        else:
            delay = DELAY_BETWEEN_REQUESTS
            rps = MAX_REQUESTS_PER_SECOND

        min_interval = 0.0
        if rps and rps > 0:
            min_interval = 1.0 / float(rps)
        if delay and delay > 0:
            min_interval = max(min_interval, float(delay))

        bucket = kind if kind in self._proximo_request_em else "default"
        agora = time.time()
        if agora < self._proximo_request_em[bucket]:
            tempo_espera = self._proximo_request_em[bucket] - agora
            logger.debug(f"Aguardando {tempo_espera:.2f}s antes da próxima requisição...")
            time.sleep(tempo_espera)
        self._proximo_request_em[bucket] = time.time() + min_interval
    
    def enviar_xml(self, xml: str) -> Tuple[bool, RespostaAPI]:
        """
        Envia XML para a API usando PUT /fd/add/xml
        
        Args:
            xml: Conteúdo XML em string
            
        Returns:
            Tupla (sucesso, resposta)
        """
        self._respeitar_throttle("put")
        
        endpoint = f"{self.url_base}/fd/add/xml"
        
        try:
            logger.debug(f"Enviando XML para {endpoint}")
            
            response = self.session.put(
                endpoint,
                data=xml.encode('utf-8'),
                headers=self.headers_base,
                timeout=REQUEST_TIMEOUT
            )
            
            logger.debug(f"Response Status: {response.status_code}")
            
            if response.status_code == 200:
                dados = response.json()
                logger.debug(f"XML enviado com sucesso. Chave: {dados.get('value')}")
                return True, RespostaAPI(
                    sucesso=True,
                    codigo=200,
                    mensagem="XML enviado com sucesso",
                    dados=dados
                )
            
            elif response.status_code == 400:
                logger.error("XML vazio ou inválido")
                return False, RespostaAPI(
                    sucesso=False,
                    codigo=400,
                    mensagem="XML vazio ou inválido",
                    erro=response.text
                )
            
            elif response.status_code == 401:
                logger.error("Api-Key não informada ou inválida")
                return False, RespostaAPI(
                    sucesso=False,
                    codigo=401,
                    mensagem="Api-Key não informada ou inválida",
                    erro=response.text
                )
            
            elif response.status_code == 403:
                logger.error("Api-Key foi substituída")
                return False, RespostaAPI(
                    sucesso=False,
                    codigo=403,
                    mensagem="Api-Key foi substituída",
                    erro=response.text
                )
            
            else:
                logger.error(f"Erro na API: {response.status_code}")
                return False, RespostaAPI(
                    sucesso=False,
                    codigo=response.status_code,
                    mensagem=f"Erro ao enviar XML: {response.status_code}",
                    erro=response.text
                )
        
        except requests.exceptions.Timeout:
            logger.error("Timeout na requisição")
            return False, RespostaAPI(
                sucesso=False,
                codigo=0,
                mensagem="Timeout na requisição",
                erro="Timeout"
            )
        
        except Exception as e:
            logger.error(f"Erro ao enviar XML: {e}")
            return False, RespostaAPI(
                sucesso=False,
                codigo=0,
                mensagem="Erro ao enviar XML",
                erro=str(e)
            )
    
    def baixar_pdf(self, chave: str) -> Tuple[bool, Optional[bytes], RespostaAPI]:
        """
        Baixa o PDF (DANFE) usando GET /fd/get/da/{Chave-Acesso}
        
        Args:
            chave: Chave de acesso da NF-e
            
        Returns:
            Tupla (sucesso, pdf_bytes, resposta)
        """
        self._respeitar_throttle("get")
        
        endpoint = f"{self.url_base}/fd/get/da/{chave}"
        
        try:
            logger.debug(f"Baixando PDF da chave: {chave}")
            
            response = self.session.get(
                endpoint,
                headers=self.headers_base,
                timeout=REQUEST_TIMEOUT
            )
            
            logger.debug(f"Response Status: {response.status_code}")
            
            if response.status_code == 200:
                dados = response.json()
                pdf_base64 = dados.get('data')
                
                if pdf_base64:
                    import base64
                    pdf_bytes = base64.b64decode(pdf_base64)
                    logger.debug(f"PDF baixado com sucesso ({len(pdf_bytes)} bytes)")
                    return True, pdf_bytes, RespostaAPI(
                        sucesso=True,
                        codigo=200,
                        mensagem="PDF baixado com sucesso",
                        dados=dados
                    )
            
            elif response.status_code == 400:
                logger.error("Chave de acesso inválida")
                return False, None, RespostaAPI(
                    sucesso=False,
                    codigo=400,
                    mensagem="Chave de acesso inválida",
                    erro=response.text
                )
            
            elif response.status_code == 401:
                logger.error("Api-Key não informada ou inválida")
                return False, None, RespostaAPI(
                    sucesso=False,
                    codigo=401,
                    mensagem="Api-Key não informada ou inválida",
                    erro=response.text
                )
            
            elif response.status_code == 404:
                logger.debug("NF-e não encontrada na sua Área do Cliente")
                return False, None, RespostaAPI(
                    sucesso=False,
                    codigo=404,
                    mensagem="NF-e não encontrada",
                    erro=response.text
                )
            
            else:
                logger.error(f"Erro ao baixar PDF: {response.status_code}")
                return False, None, RespostaAPI(
                    sucesso=False,
                    codigo=response.status_code,
                    mensagem=f"Erro ao baixar PDF: {response.status_code}",
                    erro=response.text
                )
        
        except Exception as e:
            logger.error(f"Erro ao baixar PDF: {e}")
            return False, None, RespostaAPI(
                sucesso=False,
                codigo=0,
                mensagem="Erro ao baixar PDF",
                erro=str(e)
            )
    
    def baixar_xml(self, chave: str) -> Tuple[bool, Optional[str], RespostaAPI]:
        """
        Baixa o XML usando GET /fd/get/xml/{Chave-Acesso}
        
        Args:
            chave: Chave de acesso da NF-e
            
        Returns:
            Tupla (sucesso, xml_string, resposta)
        """
        self._respeitar_throttle("get")
        
        endpoint = f"{self.url_base}/fd/get/xml/{chave}"
        
        try:
            logger.info(f"Baixando XML da chave: {chave}")
            
            response = self.session.get(
                endpoint,
                headers=self.headers_base,
                timeout=REQUEST_TIMEOUT
            )
            
            logger.debug(f"Response Status: {response.status_code}")
            
            if response.status_code == 200:
                dados = response.json()
                xml_string = dados.get('data')
                
                if xml_string:
                    logger.info(f"XML baixado com sucesso")
                    return True, xml_string, RespostaAPI(
                        sucesso=True,
                        codigo=200,
                        mensagem="XML baixado com sucesso",
                        dados=dados
                    )
            
            elif response.status_code == 404:
                logger.error("NF-e/CT-e não encontrada")
                return False, None, RespostaAPI(
                    sucesso=False,
                    codigo=404,
                    mensagem="NF-e/CT-e não encontrada",
                    erro=response.text
                )
            
            else:
                logger.error(f"Erro ao baixar XML: {response.status_code}")
                return False, None, RespostaAPI(
                    sucesso=False,
                    codigo=response.status_code,
                    mensagem=f"Erro ao baixar XML: {response.status_code}",
                    erro=response.text
                )
        
        except Exception as e:
            logger.error(f"Erro ao baixar XML: {e}")
            return False, None, RespostaAPI(
                sucesso=False,
                codigo=0,
                mensagem="Erro ao baixar XML",
                erro=str(e)
            )
