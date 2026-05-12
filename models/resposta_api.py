"""Modelos para respostas da API."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class RespostaConversaoXML:
    """Resposta do endpoint /fd/convert/xml-to-da"""
    name: str
    type: str
    format: str
    data: str  # PDF em BASE64


@dataclass
class RespostaAdicionarXML:
    """Resposta do endpoint /fd/add/xml"""
    value: str  # Chave de acesso
    type: str


@dataclass
class RespostaBuscaChave:
    """Resposta do endpoint /fd/add/{Chave-Acesso}"""
    value: str
    type: str
    status: str
    statusMessage: str


@dataclass
class RespostaDownloadPDF:
    """Resposta do endpoint /fd/get/da/{Chave-Acesso}"""
    name: str
    type: str
    format: str
    data: str  # PDF em BASE64


@dataclass
class RespostaDownloadXML:
    """Resposta do endpoint /fd/get/xml/{Chave-Acesso}"""
    name: str
    type: str
    format: str
    data: str  # XML em texto
