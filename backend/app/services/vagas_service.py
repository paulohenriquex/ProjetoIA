import logging

from sqlalchemy.orm import Session

from app.database import (
    AnaliseDB,
    CandidataDB,
    EmpresaDB,
    VagaDB,
    hash_senha,
    verificar_senha,
)

logger = logging.getLogger(__name__)


# ==================== EMPRESAS ====================

def cadastrar_empresa(db: Session, nome: str, email: str, senha: str) -> EmpresaDB:
    existente = db.query(EmpresaDB).filter(EmpresaDB.email == email).first()
    if existente:
        raise ValueError("Email já cadastrado.")
    empresa = EmpresaDB(nome=nome, email=email, senha=hash_senha(senha))
    db.add(empresa)
    db.commit()
    db.refresh(empresa)
    return empresa


def login_empresa(db: Session, email: str, senha: str) -> EmpresaDB | None:
    empresa = db.query(EmpresaDB).filter(EmpresaDB.email == email).first()
    if empresa and verificar_senha(senha, empresa.senha):
        return empresa
    return None


# ==================== VAGAS ====================

def cadastrar_vaga(db: Session, empresa_id: int, titulo: str, descricao: str,
                   obrigatorios: list, desejaveis: list) -> VagaDB:
    db.query(EmpresaDB).filter(EmpresaDB.id == empresa_id).first()  # valida que existe
    vaga = VagaDB(
        empresa_id=empresa_id,
        titulo=titulo,
        descricao=descricao,
        requisitos_obrigatorios=obrigatorios,
        requisitos_desejaveis=desejaveis,
    )
    db.add(vaga)
    db.commit()
    db.refresh(vaga)
    return vaga


def listar_vagas_abertas(db: Session, empresa_id: int = None):
    query = db.query(VagaDB).filter(VagaDB.status == "ABERTA")
    if empresa_id:
        query = query.filter(VagaDB.empresa_id == empresa_id)
    return query.all()


def buscar_vaga(db: Session, vaga_id: int) -> VagaDB | None:
    return db.query(VagaDB).filter(VagaDB.id == vaga_id).first()


# ==================== CANDIDATAS (banco compartilhado) ====================

def cadastrar_candidata(db: Session, nome: str, email: str, curriculo_texto: str) -> CandidataDB:
    existente = db.query(CandidataDB).filter(CandidataDB.email == email).first()
    if existente:
        existente.nome = nome
        existente.curriculo_texto = curriculo_texto
        db.commit()
        db.refresh(existente)
        return existente
    candidata = CandidataDB(nome=nome, email=email, curriculo_texto=curriculo_texto)
    db.add(candidata)
    db.commit()
    db.refresh(candidata)
    return candidata


def listar_candidatas(db: Session):
    return db.query(CandidataDB).order_by(CandidataDB.nome).all()


# ==================== ANÁLISES ====================

def salvar_analise(db: Session, vaga_id: int, candidata_id: int, score: int, status: str,
                   lacunas: list, analise_obrig: list, analise_desej: list):
    existente = db.query(AnaliseDB).filter(
        AnaliseDB.vaga_id == vaga_id, AnaliseDB.candidata_id == candidata_id
    ).first()
    if existente:
        existente.score = score
        existente.status = status
        existente.lacunas = lacunas
        existente.analise_obrigatorios = analise_obrig
        existente.analise_desejaveis = analise_desej
    else:
        existente = AnaliseDB(
            vaga_id=vaga_id, candidata_id=candidata_id, score=score,
            status=status, lacunas=lacunas,
            analise_obrigatorios=analise_obrig, analise_desejaveis=analise_desej,
        )
        db.add(existente)
    db.commit()
    return existente


def ranking_por_vaga(db: Session, vaga_id: int):
    return (
        db.query(AnaliseDB, CandidataDB)
        .join(CandidataDB, AnaliseDB.candidata_id == CandidataDB.id)
        .filter(AnaliseDB.vaga_id == vaga_id)
        .order_by(AnaliseDB.score.desc())
        .all()
    )


def vagas_por_candidata(db: Session, candidata_id: int):
    return (
        db.query(AnaliseDB, VagaDB)
        .join(VagaDB, AnaliseDB.vaga_id == VagaDB.id)
        .filter(AnaliseDB.candidata_id == candidata_id)
        .order_by(AnaliseDB.score.desc())
        .all()
    )
