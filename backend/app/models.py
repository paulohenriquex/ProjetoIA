from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from app.openapi_docs import ANALISE_EXAMPLE, HEALTH_EXAMPLE


class PerfilVaga(BaseModel):
    titulo: str = Field(description="Título da vaga extraído pela IA")
    requisitos_obrigatorios: List[str] = Field(description="Lista de requisitos obrigatórios detectados")
    requisitos_desejaveis: List[str] = Field(description="Lista de requisitos desejáveis detectados")


class VerificacaoRequisito(BaseModel):
    requisito: str = Field(description="Texto do requisito avaliado")
    atende: bool = Field(description="Se o candidato atende a este requisito")
    evidencia_literal: str = Field(
        default="",
        description="Trecho literal do currículo que comprova o atendimento (vazio se não atende)",
    )


class AnaliseCV(BaseModel):
    analise_obrigatorios: List[VerificacaoRequisito]
    analise_desejaveis: List[VerificacaoRequisito]


class ScoreResult(BaseModel):
    score: int = Field(ge=0, le=100, description="Score ponderado de 0 a 100")
    status: str = Field(description="Classificação do candidato")
    lacunas: List[str] = Field(description="Requisitos obrigatórios não atendidos")


StatusCandidato = Literal[
    "EXCELENTE",
    "POTENCIAL",
    "OK",
    "OPORTUNIDADE",
    "PARCIAL",
    "ELIMINADO",
    "ERRO",
]


class CandidatoResultado(BaseModel):
    nome: str = Field(description="Nome do candidato (extraído do nome do arquivo PDF)")
    score: int = Field(ge=0, le=100, description="Score ponderado: 80% obrigatórios + 20% desejáveis")
    status: StatusCandidato = Field(
        description=(
            "Classificação: EXCELENTE (≥85), POTENCIAL (≥60), OK, "
            "OPORTUNIDADE, PARCIAL, ELIMINADO ou ERRO"
        ),
    )
    eliminado: bool = Field(
        default=False,
        description="True se o candidato não atende requisitos mínimos ou houve erro no processamento",
    )
    lacunas: List[str] = Field(
        default_factory=list,
        description="Requisitos obrigatórios não atendidos pelo candidato",
    )
    analise_obrigatorios: Optional[List[VerificacaoRequisito]] = Field(
        default=None,
        description="Detalhamento da verificação de cada requisito obrigatório",
    )
    analise_desejaveis: Optional[List[VerificacaoRequisito]] = Field(
        default=None,
        description="Detalhamento da verificação de cada requisito desejável",
    )


class AnaliseResponse(BaseModel):
    titulo_vaga: str = Field(description="Título da vaga identificado pela IA")
    total_cvs: int = Field(description="Quantidade total de PDFs enviados")
    aprovados: int = Field(description="Candidatos que atendem requisitos mínimos (não eliminados)")
    eliminados: int = Field(description="Candidatos eliminados ou com erro de processamento")
    requisitos_obrigatorios: List[str] = Field(
        description="Requisitos obrigatórios extraídos da descrição da vaga",
    )
    requisitos_desejaveis: List[str] = Field(
        description="Requisitos desejáveis extraídos da descrição da vaga",
    )
    candidatos: List[CandidatoResultado] = Field(
        description="Ranking de candidatos ordenado por score (decrescente); eliminados ao final",
    )

    model_config = {
        "json_schema_extra": {"examples": [ANALISE_EXAMPLE]},
    }


class HealthResponse(BaseModel):
    status: str = Field(description="Estado da API — 'ok' quando operacional")
    api_configured: bool = Field(
        description="True se GEMINI_API_KEY está definida no servidor",
    )
    model: str = Field(description="Modelo de IA configurado (ex: gemini-3.1-flash-lite)")
    port: int = Field(description="Porta HTTP em que a API está escutando")

    model_config = {
        "json_schema_extra": {"examples": [HEALTH_EXAMPLE]},
    }


class ErrorResponse(BaseModel):
    detail: str | list = Field(description="Mensagem de erro ou lista de erros de validação")


class VagaTalentoInput(BaseModel):
    vaga_id: str = Field(description="Identificador único da vaga no banco de talentos")
    texto_vaga: str = Field(min_length=20, description="Descrição completa da vaga informada pelo recrutador")
    candidato_cadastrado: bool = Field(
        description="Indica se o candidato está cadastrado nesta vaga",
    )


class ResultadoVagaTalento(BaseModel):
    vaga_id: str = Field(description="Identificador da vaga analisada")
    titulo_vaga: str = Field(description="Título da vaga identificado pela IA")
    candidato_cadastrado: bool = Field(description="Se o candidato está cadastrado na vaga")
    analisado: bool = Field(
        description="True quando a análise foi executada (somente para vagas com cadastro)",
    )
    score: int = Field(
        ge=0,
        le=100,
        default=0,
        description="Score ponderado do candidato para a vaga",
    )
    status: str = Field(
        description=(
            "Resultado da vaga: APROVADA, REPROVADA, NAO_CADASTRADO, "
            "ERRO_VAGA ou ERRO_ANALISE"
        ),
    )
    lacunas: List[str] = Field(
        default_factory=list,
        description="Requisitos obrigatórios não atendidos para a vaga",
    )
    pontos_melhorar: List[str] = Field(
        default_factory=list,
        description="Pontos sugeridos para evolução do candidato nesta vaga",
    )
    analise_obrigatorios: Optional[List[VerificacaoRequisito]] = Field(
        default=None,
        description="Detalhamento da verificação de requisitos obrigatórios",
    )
    analise_desejaveis: Optional[List[VerificacaoRequisito]] = Field(
        default=None,
        description="Detalhamento da verificação de requisitos desejáveis",
    )


class AnaliseBancoTalentosResponse(BaseModel):
    candidato: str = Field(description="Nome do candidato extraído do nome do arquivo PDF")
    total_vagas_recebidas: int = Field(description="Quantidade de vagas enviadas pelo recrutador")
    vagas_analisadas: int = Field(description="Quantidade de vagas efetivamente analisadas")
    vagas_nao_cadastradas: int = Field(description="Quantidade de vagas ignoradas por falta de cadastro")
    vagas_aprovadas: int = Field(description="Quantidade de vagas aprovadas")
    vagas_reprovadas: int = Field(description="Quantidade de vagas reprovadas")
    resultados: List[ResultadoVagaTalento] = Field(
        description="Lista de resultados por vaga",
    )
