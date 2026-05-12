from dataclasses import dataclass
from typing import Optional
from datetime import datetime

from utils.validators import normalizar_chave_acesso


@dataclass
class Alocacao:
    """Representa uma linha da planilha de alocação."""
    
    # Campos obrigatórios
    chave: str  # Chave de acesso da NF-e
    
    # Campos para separação
    placa: str  # ABC1234
    rota: str   # 26 GRU - BOM RETIRO
    
    # Dados adicionais
    pedido: str
    nf: str
    cliente: str
    cidade: str
    tipo_cliente: str

    # ID único da quebra (usado para evitar colisões quando rota/placa se repetem)
    id_quebra: Optional[str] = None
    bairro: Optional[str] = None
    endereco: Optional[str] = None
    cep: Optional[str] = None
    valor_total: float = 0.0
    qtd_caixas: float = 0.0
    peso_bruto: float = 0.0
    distancia: float = 0.0
    codigo_cliente: Optional[str] = None
    
    # Informações de processamento
    xml: Optional[str] = None
    pdf_base64: Optional[str] = None
    timestamp_processamento: Optional[datetime] = None
    status: str = "pendente"  # pendente, enviado, sucesso, erro
    mensagem_erro: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Converte para dicionário."""
        return {
            "chave": self.chave,
            "placa": self.placa,
            "rota": self.rota,
            "id_quebra": self.id_quebra,
            "pedido": self.pedido,
            "nf": self.nf,
            "cliente": self.cliente,
            "cidade": self.cidade,
            "tipo_cliente": self.tipo_cliente,
            "bairro": self.bairro,
            "endereco": self.endereco,
            "cep": self.cep,
            "valor_total": self.valor_total,
            "qtd_caixas": self.qtd_caixas,
            "peso_bruto": self.peso_bruto,
            "distancia": self.distancia,
            "codigo_cliente": self.codigo_cliente,
            "status": self.status,
            "timestamp": self.timestamp_processamento.isoformat() if self.timestamp_processamento else None,
            "mensagem_erro": self.mensagem_erro
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'Alocacao':
        """Cria a partir de um dicionário."""
        chave = normalizar_chave_acesso(data.get("CHAVE", ""))

        def _to_float(valor) -> float:
            if valor is None:
                return 0.0
            if isinstance(valor, (int, float)):
                return float(valor)
            texto = str(valor).strip()
            if not texto:
                return 0.0
            if texto.startswith("Total:"):
                texto = texto.replace("Total:", "", 1).strip()
            texto = texto.replace(".", "").replace(",", ".") if texto.count(",") == 1 and texto.count(".") >= 1 else texto
            try:
                return float(texto)
            except Exception:
                return 0.0
        
        return Alocacao(
            chave=chave,
            placa=data.get("Placa", ""),
            rota=data.get("Identificador da rota") or data.get("Identificador") or "",
            id_quebra=(str(data.get("ID_QUEBRA")).strip() if data.get("ID_QUEBRA") is not None and str(data.get("ID_QUEBRA")).strip() else None),
            pedido=data.get("Pedido", ""),
            nf=data.get("NF", ""),
            cliente=data.get("Cliente", ""),
            cidade=data.get("Cidade", ""),
            tipo_cliente=data.get("Tipo cliente", ""),
            bairro=data.get("Bairro"),
            endereco=data.get("Endereço"),
            cep=data.get("Cep"),
            valor_total=_to_float(data.get("Valor total pedido")),
            qtd_caixas=_to_float(data.get("Qtd. caixas")),
            peso_bruto=_to_float(data.get("Peso bruto pedido")),
            distancia=_to_float(data.get("Distância calculado")),
            codigo_cliente=data.get("Código cliente")
        )


@dataclass
class RespostaAPI:
    """Representa a resposta da API."""
    
    sucesso: bool
    codigo: int
    mensagem: str
    dados: Optional[dict] = None
    erro: Optional[str] = None


@dataclass
class ResultadoProcessamento:
    """Resultado do processamento de uma alocação."""
    
    alocacao: Alocacao
    sucesso: bool
    etapa: str  # "upload_xml", "download_pdf", etc
    arquivo_pdf: Optional[str] = None  # Caminho do arquivo salvo
    arquivo_xml: Optional[str] = None
    mensagem: str = ""
