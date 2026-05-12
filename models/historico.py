from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Processamento(Base):
    __tablename__ = "processamentos"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True)
    timestamp = Column(DateTime, default=datetime.now)
    planilha_nome = Column(String(255))
    tipo_separacao = Column(String(50))
    status = Column(String(50))  # 'processando', 'concluido', 'erro'
    mensagem = Column(String(500))
    
    # JSON com resumo: {"sucesso": 10, "falha": 2, "total": 12}
    resumo = Column(JSON)
    # JSON com filtros usados: {"rotas": [...], "placas": [...]}
    filtros = Column(JSON)
    
    arquivos = relationship("ArquivoProcessado", back_populates="processamento", cascade="all, delete-orphan")

class ArquivoProcessado(Base):
    __tablename__ = "arquivos_processados"

    id = Column(Integer, primary_key=True, index=True)
    processamento_id = Column(Integer, ForeignKey("processamentos.id"))
    
    chave_nfe = Column(String(44), index=True)
    tipo = Column(String(10))  # 'pdf', 'xml'
    caminho_local = Column(String(1000))
    
    # Metadados úteis para busca
    cliente = Column(String(255), index=True)
    valor = Column(Float)
    rota = Column(String(100), index=True)
    placa = Column(String(20), index=True)

    processamento = relationship("Processamento", back_populates="arquivos")
