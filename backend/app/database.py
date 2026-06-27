import hashlib
from datetime import datetime

from sqlalchemy import JSON, BigInteger, Column, DateTime, ForeignKey, Integer, String, Text, Numeric, UniqueConstraint, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class UsuarioDB(Base):
    __tablename__ = "usuarios"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    email = Column(String(150), unique=True, nullable=False)
    tipo = Column(String(20)) # 'candidata' ou 'empresa'
    provider = Column(String(20), default="google")
    provider_user_id = Column(String(100), nullable=False)
    foto_url = Column(String(255))
    data_criacao = Column(DateTime, default=datetime.utcnow)


class EmpresaDB(Base):
    __tablename__ = "empresas"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    usuario_id = Column(BigInteger, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    razao_social = Column(String(150), nullable=False)
    cnpj = Column(String(18), unique=True, nullable=False)
    descricao_empresa = Column(Text)
    setor = Column(String(100))


class VagaDB(Base):
    __tablename__ = "vagas"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    empresa_id = Column(BigInteger, ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False)
    titulo = Column(String(100), nullable=False)
    descricao = Column(Text, nullable=False)
    requisitos_minimos = Column(Text)
    modalidade = Column(String(20)) # enum('presencial','remoto','hibrido')
    nivel = Column(String(20)) # enum('junior','pleno','senior','estagio')
    salario_estimado = Column(Numeric(10, 2))
    data_publicacao = Column(DateTime, default=datetime.utcnow)


class CandidataDB(Base):
    __tablename__ = "candidatas"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    usuario_id = Column(BigInteger, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    nome_completo = Column(String(150), nullable=False)
    cpf = Column(String(14), unique=True)
    biografia = Column(Text)
    linkedin_url = Column(String(255))
    status_vulnerabilidade = Column(Integer, default=0) # tinyint(1) no banco


class AnaliseDB(Base):
    __tablename__ = "analises"
    __table_args__ = (
        UniqueConstraint("vaga_id", "candidata_id", name="unica_analise"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    vaga_id = Column(BigInteger, ForeignKey("vagas.id", ondelete="CASCADE"), nullable=False)
    candidata_id = Column(BigInteger, ForeignKey("candidatas.id", ondelete="CASCADE"), nullable=False)
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