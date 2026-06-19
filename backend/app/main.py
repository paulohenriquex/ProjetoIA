import logging
import json
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app.config import API_KEY, MODELO, PORT
from app.models import AnaliseBancoTalentosResponse, AnaliseResponse, HealthResponse, VagaTalentoInput
from app.openapi_docs import (
    ANALISE_EXAMPLE,
    APP_DESCRIPTION,
    ERROR_EXAMPLES,
    HEALTH_EXAMPLE,
    TAGS_METADATA,
    TEXTO_VAGA_EXAMPLE,
)
from app.services.triagem import processar_banco_talentos, processar_triagem

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
        return await processar_triagem(texto_vaga, pdfs)
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
        return await processar_banco_talentos(curriculo, vagas)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        logger.exception("Erro inesperado na análise do banco de talentos")
        raise HTTPException(status_code=500, detail="Erro interno ao processar análise.") from e
