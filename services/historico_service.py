import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from models.historico import Processamento, ArquivoProcessado
from models.database import SessionLocal, engine, Base

# Garante que as tabelas existem (simples para SQLite)
Base.metadata.create_all(bind=engine)

class HistoricoService:
    @staticmethod
    def criar_processamento(
        planilha_nome: str,
        tipo_separacao: str,
        filtros: Optional[Dict[str, Any]] = None
    ) -> Processamento:
        db = SessionLocal()
        try:
            p = Processamento(
                uuid=str(uuid.uuid4()),
                planilha_nome=planilha_nome,
                tipo_separacao=tipo_separacao,
                status="processando",
                filtros=filtros or {},
                timestamp=datetime.now()
            )
            db.add(p)
            db.commit()
            db.refresh(p)
            return p
        finally:
            db.close()

    @staticmethod
    def atualizar_processamento(
        p_uuid: str,
        status: str,
        mensagem: Optional[str] = None,
        resumo: Optional[Dict[str, Any]] = None
    ):
        db = SessionLocal()
        try:
            p = db.query(Processamento).filter(Processamento.uuid == p_uuid).first()
            if p:
                p.status = status
                if mensagem:
                    p.mensagem = mensagem
                if resumo:
                    p.resumo = resumo
                db.commit()
        finally:
            db.close()

    @staticmethod
    def registrar_arquivo(
        p_uuid: str,
        chave_nfe: str,
        tipo: str,
        caminho_local: str,
        cliente: Optional[str] = None,
        valor: Optional[float] = None,
        rota: Optional[str] = None,
        placa: Optional[str] = None
    ):
        db = SessionLocal()
        try:
            p = db.query(Processamento).filter(Processamento.uuid == p_uuid).first()
            if not p:
                return
            
            arq = ArquivoProcessado(
                processamento_id=p.id,
                chave_nfe=chave_nfe,
                tipo=tipo,
                caminho_local=caminho_local,
                cliente=cliente,
                valor=valor,
                rota=rota,
                placa=placa
            )
            db.add(arq)
            db.commit()
        finally:
            db.close()

    @staticmethod
    def listar_processamentos(limit: int = 50, offset: int = 0) -> List[Processamento]:
        db = SessionLocal()
        try:
            return db.query(Processamento).order_by(Processamento.timestamp.desc()).offset(offset).limit(limit).all()
        finally:
            db.close()

    @staticmethod
    def obter_detalhes(p_uuid: str) -> Optional[Dict[str, Any]]:
        db = SessionLocal()
        try:
            p = db.query(Processamento).filter(Processamento.uuid == p_uuid).first()
            if not p:
                return None
            
            # Converte para dict para evitar problemas de sessão fechada
            return {
                "id": p.id,
                "uuid": p.uuid,
                "timestamp": p.timestamp.isoformat(),
                "planilha_nome": p.planilha_nome,
                "tipo_separacao": p.tipo_separacao,
                "status": p.status,
                "mensagem": p.mensagem,
                "resumo": p.resumo,
                "filtros": p.filtros,
                "arquivos": [
                    {
                        "chave_nfe": a.chave_nfe,
                        "tipo": a.tipo,
                        "cliente": a.cliente,
                        "valor": a.valor,
                        "rota": a.rota,
                        "placa": a.placa
                    } for a in p.arquivos
                ]
            }
        finally:
            db.close()

    @staticmethod
    def buscar_por_chave(chave: str) -> List[Dict[str, Any]]:
        db = SessionLocal()
        try:
            arqs = db.query(ArquivoProcessado).filter(ArquivoProcessado.chave_nfe == chave).all()
            return [
                {
                    "processamento_uuid": a.processamento.uuid,
                    "timestamp": a.processamento.timestamp.isoformat(),
                    "tipo": a.tipo,
                    "caminho": a.caminho_local,
                    "cliente": a.cliente
                } for a in arqs
            ]
        finally:
            db.close()
