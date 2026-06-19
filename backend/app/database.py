import hashlib
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class EmpresaDB(Base):
    __tablename__ = "empresas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(200), nullable=False)
    email = Column(String(200), unique=True, nullable=False)
    senha = Column(String(255), nullable=False)
    criada_em = Column(DateTime, default=datetime.utcnow)


class VagaDB(Base):
    __tablename__ = "vagas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False)
    titulo = Column(String(200), nullable=False)
    descricao = Column(Text, nullable=False)
    requisitos_obrigatorios = Column(JSON, nullable=True)
    requisitos_desejaveis = Column(JSON, nullable=True)
    status = Column(String(20), default="ABERTA")
    criada_em = Column(DateTime, default=datetime.utcnow)


class CandidataDB(Base):
    __tablename__ = "candidatas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(200), nullable=False)
    email = Column(String(200), unique=True, nullable=False)
    curriculo_texto = Column(Text, nullable=False)
    criada_em = Column(DateTime, default=datetime.utcnow)


class AnaliseDB(Base):
    __tablename__ = "analises"
    __table_args__ = (
        UniqueConstraint("vaga_id", "candidata_id", name="unica_analise"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    vaga_id = Column(Integer, ForeignKey("vagas.id", ondelete="CASCADE"), nullable=False)
    candidata_id = Column(Integer, ForeignKey("candidatas.id", ondelete="CASCADE"), nullable=False)
    score = Column(Integer, nullable=False)
    status = Column(String(30), nullable=False)
    lacunas = Column(JSON, nullable=True)
    analise_obrigatorios = Column(JSON, nullable=True)
    analise_desejaveis = Column(JSON, nullable=True)
    criada_em = Column(DateTime, default=datetime.utcnow)


def hash_senha(senha: str) -> str:
    return hashlib.sha256(senha.encode()).hexdigest()


def verificar_senha(senha: str, hash_str: str) -> bool:
    return hash_senha(senha) == hash_str


def criar_tabelas():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
