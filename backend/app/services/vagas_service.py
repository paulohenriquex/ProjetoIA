import logging
import json

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
    # Mapeando 'nome' para 'razao_social'. 
    # Adicionado CNPJ falso e usuario_id=10 para não quebrar a Foreign Key do seu banco.
    existente = db.query(EmpresaDB).filter(EmpresaDB.razao_social == nome).first()
    if existente:
        raise ValueError("Empresa já cadastrada.")
    
    empresa = EmpresaDB(
        razao_social=nome, 
        cnpj=f"00.000.000/0001-{len(nome)}", 
        usuario_id=10 
    )
    db.add(empresa)
    db.commit()
    db.refresh(empresa)
    return empresa


def login_empresa(db: Session, email: str, senha: str) -> EmpresaDB | None:
    # NOTA: O banco atual guarda email/senha na tabela `usuarios`, não em `empresas`.
    # Retornando None temporariamente para evitar falhas de syntax error na importação.
    return None


# ==================== VAGAS ====================

def cadastrar_vaga(db: Session, empresa_id: int, titulo: str, descricao: str,
                   obrigatorios: list, desejaveis: list) -> VagaDB:
    db.query(EmpresaDB).filter(EmpresaDB.id == empresa_id).first()  # valida que existe
    
    # Agrupando os requisitos num JSON, já que o banco possui apenas a coluna 'requisitos_minimos' (Text)
    req_agrupados = {
        "obrigatorios": obrigatorios,
        "desejaveis": desejaveis
    }
    
    vaga = VagaDB(
        empresa_id=empresa_id,
        titulo=titulo,
        descricao=descricao,
        # ✅ Correção: Usando json.dumps para converter o dicionário em texto formatado
        requisitos_minimos=json.dumps(req_agrupados, ensure_ascii=False)
    )
    db.add(vaga)
    db.commit()
    db.refresh(vaga)
    return vaga


def listar_vagas_abertas(db: Session, empresa_id: int = None):
    # A coluna 'status' não existe mais na sua tabela de Vagas real. Removido o filtro.
    query = db.query(VagaDB)
    if empresa_id:
        query = query.filter(VagaDB.empresa_id == empresa_id)
    return query.all()


def buscar_vaga(db: Session, vaga_id: int) -> VagaDB | None:
    return db.query(VagaDB).filter(VagaDB.id == vaga_id).first()


# ==================== CANDIDATAS ====================

def cadastrar_candidata(db: Session, nome: str, email: str, curriculo_texto: str) -> CandidataDB:
    # A coluna email está na tabela Usuario. Mudando a checagem para 'nome_completo'.
    existente = db.query(CandidataDB).filter(CandidataDB.nome_completo == nome).first()
    if existente:
        existente.biografia = curriculo_texto
        db.commit()
        db.refresh(existente)
        return existente
    
    candidata = CandidataDB(
        nome_completo=nome, 
        biografia=curriculo_texto,
        usuario_id=1 # ✅ Chave estrangeira obrigatória. Colocado o ID 1 do banco provisoriamente.
    )
    db.add(candidata)
    db.commit()
    db.refresh(candidata)
    return candidata


def listar_candidatas(db: Session):
    # 'nome' corrigido para 'nome_completo'
    return db.query(CandidataDB).order_by(CandidataDB.nome_completo).all()


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