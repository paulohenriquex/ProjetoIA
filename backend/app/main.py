import logging
import json
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import API_KEY, MODELO, PORT
from app.database import Base, SessionLocal, VagaDB, criar_tabelas, engine, get_db
from app.models import AnaliseBancoTalentosResponse, AnaliseResponse, HealthResponse, VagaTalentoInput
from app.services import vagas_service
from app.openapi_docs import (
    ANALISE_EXAMPLE,
    APP_DESCRIPTION,
    ERROR_EXAMPLES,
    HEALTH_EXAMPLE,
    TAGS_METADATA,
    TEXTO_VAGA_EXAMPLE,
)
from app.services.triagem import processar_banco_talentos, processar_triagem
from app.services.ai_service import extrair_perfil_vaga

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(
    title="Triagem de Currículos",
    description=APP_DESCRIPTION,
    version="1.0.0",
    docs_url=None,
    redoc_url="/redoc",
    openapi_tags=TAGS_METADATA,
    contact={
        "name": "Equipe de Desenvolvimento",
        "url": "https://github.com",
    },
    license_info={
        "name": "Uso interno",
    },
)


@app.on_event("startup")
def startup():
    try:
        criar_tabelas()
        logger.info("Tabelas verificadas/criadas com sucesso")
    except Exception as e:
        logger.error("Falha ao conectar/criar tabelas no MySQL: %s", e)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/docs", include_in_schema=False)
async def swagger_ui():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
        swagger_js_url="/static/swagger-ui/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui/swagger-ui.css",
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(
    "/api/health",
    response_model=HealthResponse,
    tags=["Sistema"],
    summary="Verificar status da API",
    description="""
Verifica se a API está **online** e se a chave de IA está configurada.

**Quando usar:** ao carregar o frontend ou antes de iniciar uma triagem.

**Resposta esperada:**
- `status: "ok"` — API operacional
- `api_configured: true` — pronta para analisar currículos
- `api_configured: false` — retornará HTTP 503 no `/api/analyze`
    """,
    responses={
        200: {
            "description": "API operacional",
            "content": {"application/json": {"example": HEALTH_EXAMPLE}},
        },
    },
)
def health():
    return HealthResponse(
        status="ok",
        api_configured=bool(API_KEY),
        model=MODELO,
        port=PORT,
    )


@app.post(
    "/api/analyze",
    response_model=AnaliseResponse,
    tags=["Triagem"],
    summary="Analisar currículos contra uma vaga",
    description="""
Executa a **triagem completa** de um ou mais currículos em PDF.

### Passo a passo interno
1. A IA extrai título, requisitos obrigatórios e desejáveis do `texto_vaga`
2. Para cada PDF: extrai texto, analisa requisitos e calcula score
3. Retorna ranking ordenado por score (aprovados primeiro, eliminados ao final)

### Campos do formulário (multipart/form-data)

| Campo | Descrição |
|-------|-----------|
| **texto_vaga** | Descrição completa da vaga (mín. 20 caracteres) |
| **curriculos** | Arquivo(s) PDF — selecione múltiplos repetindo o campo |

### Como testar no Swagger
1. Clique em **Try it out**
2. Cole o texto da vaga no campo `texto_vaga`
3. Em `curriculos`, clique em **Add string item** e selecione um ou mais PDFs
4. Clique em **Execute** e aguarde (pode levar minutos)

### Observações
- Apenas arquivos com extensão `.pdf` são processados
- PDFs sem texto legível retornam status `ERRO`
- Não defina header `Content-Type` manualmente — o cliente define o boundary
    """,
    responses={
        200: {
            "description": "Triagem concluída com sucesso",
            "content": {"application/json": {"example": ANALISE_EXAMPLE}},
        },
        **ERROR_EXAMPLES,
    },
)
async def analyze(
    texto_vaga: Annotated[
        str,
        Form(
            min_length=20,
            description="Descrição completa da vaga de emprego (título, requisitos, responsabilidades)",
            examples=[TEXTO_VAGA_EXAMPLE],
        ),
    ],
    curriculos: Annotated[
        list[UploadFile],
        File(
            description="Um ou mais currículos em formato PDF. Repita o campo para enviar múltiplos arquivos.",
        ),
    ],
    empresa_id: Annotated[
        int,
        Form(
            description="ID da empresa dona da vaga (padrão: 1)",
        ),
    ] = 1,
):
    if not API_KEY:
        raise HTTPException(
            status_code=503,
            detail="GEMINI_API_KEY não configurada. Defina a variável de ambiente.",
        )

    pdfs = [f for f in curriculos if f.filename and f.filename.lower().endswith(".pdf")]
    if not pdfs:
        raise HTTPException(status_code=400, detail="Envie ao menos um arquivo PDF.")

    try:
        db = next(get_db())
        # Extrai perfil e cadastra a vaga automaticamente
        perfil = extrair_perfil_vaga(texto_vaga)
        vaga = vagas_service.cadastrar_vaga(
            db,
            empresa_id=empresa_id,
            titulo=perfil.titulo if perfil else "Vaga",
            descricao=texto_vaga,
            obrigatorios=perfil.requisitos_obrigatorios if perfil else [],
            desejaveis=perfil.requisitos_desejaveis if perfil else [],
        )
        return await processar_triagem(texto_vaga, pdfs, db, vaga_id=vaga.id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        logger.exception("Erro inesperado na triagem")
        raise HTTPException(status_code=500, detail="Erro interno ao processar triagem.") from e


@app.post(
    "/api/analyze-talent-bank",
    response_model=AnaliseBancoTalentosResponse,
    tags=["Triagem"],
    summary="Analisar um candidato em várias vagas cadastradas",
    description="""
Analisa um único currículo contra várias vagas do banco de talentos.

### Regras de negócio
- A análise só é executada para vagas com `candidato_cadastrado=true`
- Vagas sem cadastro retornam status `NAO_CADASTRADO`
- Cada vaga retorna aprovação/reprovação e pontos de melhoria
    """,
    responses={
        400: {"description": "Currículo inválido ou vagas_json inválido"},
        422: {"description": "Falha de validação do currículo/vagas"},
        503: {"description": "Chave da IA não configurada"},
        500: {"description": "Erro interno inesperado"},
    },
)
async def analyze_talent_bank(
    curriculo: Annotated[
        UploadFile,
        File(description="Currículo do candidato em PDF"),
    ],
    vagas_json: Annotated[
        str,
        Form(
            description=(
                "JSON com lista de vagas. "
                "Exemplo: "
                '[{"vaga_id":"1","texto_vaga":"...","candidato_cadastrado":true}]'
            ),
        ),
    ],
):
    if not API_KEY:
        raise HTTPException(
            status_code=503,
            detail="GEMINI_API_KEY não configurada. Defina a variável de ambiente.",
        )

    if not curriculo.filename or not curriculo.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Envie um currículo em PDF.")

    try:
        vagas_raw = json.loads(vagas_json)
        if not isinstance(vagas_raw, list) or not vagas_raw:
            raise HTTPException(status_code=400, detail="Envie ao menos uma vaga em vagas_json.")
        vagas = [VagaTalentoInput.model_validate(item) for item in vagas_raw]
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors()) from e
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail="vagas_json inválido. Envie um JSON válido.") from e

    try:
        return await processar_banco_talentos(curriculo, vagas, next(get_db()))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        logger.exception("Erro inesperado na análise do banco de talentos")
        raise HTTPException(status_code=500, detail="Erro interno ao processar análise.") from e


# ==================== EMPRESAS ====================

@app.post("/api/empresas/cadastrar", tags=["Empresas"], summary="Cadastrar empresa")
def cadastrar_empresa(
    nome: Annotated[str, Form()],
    email: Annotated[str, Form()],
    senha: Annotated[str, Form()],
    db: Session = Depends(get_db),
):
    try:
        empresa = vagas_service.cadastrar_empresa(db, nome, email, senha)
        return {"id": empresa.id, "nome": empresa.nome, "email": empresa.email}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.post("/api/empresas/login", tags=["Empresas"], summary="Login da empresa")
def login_empresa(
    email: Annotated[str, Form()],
    senha: Annotated[str, Form()],
    db: Session = Depends(get_db),
):
    empresa = vagas_service.login_empresa(db, email, senha)
    if not empresa:
        raise HTTPException(status_code=401, detail="Email ou senha inválidos.")
    return {"id": empresa.id, "nome": empresa.nome, "email": empresa.email}


# ==================== VAGAS ====================

@app.post("/api/vagas", tags=["Cadastro"], summary="Cadastrar nova vaga")
def cadastrar_vaga(
    empresa_id: Annotated[int, Form(description="ID da empresa")],
    titulo: Annotated[str, Form(description="Título da vaga")],
    descricao: Annotated[str, Form(description="Descrição completa")],
    db: Session = Depends(get_db),
):
    from app.services.ai_service import extrair_perfil_vaga
    perfil = extrair_perfil_vaga(descricao)
    obrig = perfil.requisitos_obrigatorios if perfil else []
    desej = perfil.requisitos_desejaveis if perfil else []
    vaga = vagas_service.cadastrar_vaga(db, empresa_id, titulo, descricao, obrig, desej)
    return {"id": vaga.id, "titulo": vaga.titulo, "empresa_id": vaga.empresa_id, "status": vaga.status}


@app.get("/api/vagas", tags=["Cadastro"], summary="Listar vagas abertas")
def listar_vagas(
    empresa_id: int = None,
    db: Session = Depends(get_db),
):
    vagas = vagas_service.listar_vagas_abertas(db, empresa_id=empresa_id)
    return [
        {"id": v.id, "empresa_id": v.empresa_id, "titulo": v.titulo,
         "status": v.status, "criada_em": str(v.criada_em)}
        for v in vagas
    ]


@app.post("/api/vagas/{vaga_id}/analisar", tags=["Cadastro"], summary="Analisar CVs contra vaga cadastrada")
async def analisar_vaga(
    vaga_id: int,
    curriculos: Annotated[list[UploadFile], File()],
    db: Session = Depends(get_db),
):
    vaga = vagas_service.buscar_vaga(db, vaga_id)
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga não encontrada.")
    if not API_KEY:
        raise HTTPException(status_code=503, detail="API key não configurada.")
    return await processar_triagem(vaga.descricao, curriculos, db, vaga_id=vaga_id)


@app.get("/api/vagas/{vaga_id}/ranking", tags=["Cadastro"], summary="Ranking de candidatas por vaga")
def ranking_vaga(vaga_id: int, db: Session = Depends(get_db)):
    resultados = vagas_service.ranking_por_vaga(db, vaga_id)
    return [
        {"candidata": c.nome, "score": a.score, "status": a.status, "lacunas": a.lacunas}
        for a, c in resultados
    ]


# ==================== CANDIDATAS ====================

@app.get("/api/candidatas", tags=["Cadastro"], summary="Listar todas candidatas (banco compartilhado)")
def listar_candidatas(db: Session = Depends(get_db)):
    candidatas = vagas_service.listar_candidatas(db)
    return [{"id": c.id, "nome": c.nome, "email": c.email} for c in candidatas]


@app.get("/api/candidatas/{candidata_id}/vagas", tags=["Cadastro"], summary="Vagas compatíveis com a candidata")
def vagas_candidata(candidata_id: int, db: Session = Depends(get_db)):
    resultados = vagas_service.vagas_por_candidata(db, candidata_id)
    return [
        {"vaga": v.titulo, "empresa_id": v.empresa_id, "score": a.score, "status": a.status}
        for a, v in resultados
    ]
