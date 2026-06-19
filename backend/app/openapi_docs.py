"""Metadados, exemplos e textos da documentação Swagger/OpenAPI."""

APP_DESCRIPTION = """
## Triagem de Currículos com IA

API REST para **análise automatizada de currículos (PDF)** com base na descrição de uma vaga de emprego.

Utiliza **Google Gemini 3.1 Flash Lite** para:
1. Extrair requisitos obrigatórios e desejáveis da vaga
2. Analisar cada currículo contra esses requisitos
3. Calcular score ponderado e classificar candidatos

---

### Fluxo de utilização

```
1. GET  /api/health   → Verificar se a API está online e configurada
2. POST /api/analyze  → Enviar texto da vaga + PDFs dos currículos
3. Receber ranking ordenado por score com detalhes por candidato
```

---

### Autenticação

Esta API **não exige token** do cliente. A chave `GEMINI_API_KEY` é configurada no servidor (variável de ambiente).

---

### Formato de requisição — POST /api/analyze

| Campo | Tipo | Obrigatório | Regra |
|-------|------|-------------|-------|
| `texto_vaga` | string (form) | Sim | Mínimo 20 caracteres — cole a descrição completa da vaga |
| `curriculos` | file[] (form) | Sim | Um ou mais arquivos **PDF**; repita o campo para múltiplos CVs |

**Content-Type:** `multipart/form-data`

**Exemplo com curl:**
```bash
curl -X POST "http://localhost:8080/api/analyze" \\
  -F "texto_vaga=Desenvolvedor Python com 3 anos de experiência. Obrigatório: Python, Git. Desejável: FastAPI, Docker." \\
  -F "curriculos=@curriculo_joao.pdf" \\
  -F "curriculos=@curriculo_maria.pdf"
```

---

### Fórmula de score

```
score = (obrigatórios_atendidos / total_obrig × 80) + (desejáveis_atendidos / total_desej × 20)
```

| Status | Condição |
|--------|----------|
| `EXCELENTE` | Todos obrigatórios + score ≥ 85 |
| `POTENCIAL` | Todos obrigatórios + score ≥ 60 |
| `OK` | Todos obrigatórios + score < 60 |
| `OPORTUNIDADE` | Falta obrigatório, mas atende desejável |
| `PARCIAL` | Score > 0, perfil incompleto |
| `ELIMINADO` | Score = 0 |
| `ERRO` | Falha no processamento do PDF ou IA |

---

### Tempo de resposta

- **1 CV:** ~10–30 segundos
- **N CVs:** N × (tempo por CV + 1s de intervalo interno)
- Configure timeout alto no cliente (recomendado: **600s**)

---

### CORS

Requisições de **qualquer origem** são permitidas (`Access-Control-Allow-Origin: *`).

---

### Integração com frontend

O frontend React (porta 6500) consome esta API via proxy `/api/*`.
Documentação completa: `docs/05-integracao-frontend.md`
"""

TAGS_METADATA = [
    {
        "name": "Sistema",
        "description": "Endpoints de monitoramento e status da API.",
    },
    {
        "name": "Triagem",
        "description": "Análise de currículos contra descrição de vaga com IA.",
    },
]

HEALTH_EXAMPLE = {
    "status": "ok",
    "api_configured": True,
    "model": "gemini-3.1-flash-lite",
    "port": 8080,
}

ANALISE_EXAMPLE = {
    "titulo_vaga": "Desenvolvedor Python",
    "total_cvs": 3,
    "aprovados": 2,
    "eliminados": 1,
    "requisitos_obrigatorios": ["Python 3 anos", "Experiência com Git"],
    "requisitos_desejaveis": ["FastAPI", "Docker", "PostgreSQL"],
    "candidatos": [
        {
            "nome": "Joao Silva",
            "score": 90,
            "status": "EXCELENTE",
            "eliminado": False,
            "lacunas": [],
            "analise_obrigatorios": [
                {
                    "requisito": "Python 3 anos",
                    "atende": True,
                    "evidencia_literal": "5 anos de experiência com Python em projetos web",
                },
                {
                    "requisito": "Experiência com Git",
                    "atende": True,
                    "evidencia_literal": "Controle de versão Git/GitHub em todos os projetos",
                },
            ],
            "analise_desejaveis": [
                {
                    "requisito": "FastAPI",
                    "atende": True,
                    "evidencia_literal": "API REST desenvolvida com FastAPI",
                },
                {
                    "requisito": "Docker",
                    "atende": True,
                    "evidencia_literal": "Containerização com Docker Compose",
                },
                {
                    "requisito": "PostgreSQL",
                    "atende": False,
                    "evidencia_literal": "",
                },
            ],
        },
        {
            "nome": "Maria Santos",
            "score": 65,
            "status": "POTENCIAL",
            "eliminado": False,
            "lacunas": [],
            "analise_obrigatorios": [
                {
                    "requisito": "Python 3 anos",
                    "atende": True,
                    "evidencia_literal": "3 anos como desenvolvedora Python",
                },
                {
                    "requisito": "Experiência com Git",
                    "atende": True,
                    "evidencia_literal": "Uso diário de Git",
                },
            ],
            "analise_desejaveis": [
                {
                    "requisito": "FastAPI",
                    "atende": False,
                    "evidencia_literal": "",
                },
                {
                    "requisito": "Docker",
                    "atende": False,
                    "evidencia_literal": "",
                },
                {
                    "requisito": "PostgreSQL",
                    "atende": True,
                    "evidencia_literal": "Banco PostgreSQL em projeto anterior",
                },
            ],
        },
        {
            "nome": "Pedro Costa",
            "score": 0,
            "status": "ELIMINADO",
            "eliminado": True,
            "lacunas": ["Python 3 anos", "Experiência com Git"],
            "analise_obrigatorios": [
                {
                    "requisito": "Python 3 anos",
                    "atende": False,
                    "evidencia_literal": "",
                },
                {
                    "requisito": "Experiência com Git",
                    "atende": False,
                    "evidencia_literal": "",
                },
            ],
            "analise_desejaveis": [],
        },
    ],
}

ERROR_EXAMPLES = {
    400: {
        "description": "Nenhum PDF válido enviado",
        "content": {
            "application/json": {
                "example": {"detail": "Envie ao menos um arquivo PDF."},
            }
        },
    },
    422: {
        "description": "Validação ou falha ao processar a vaga",
        "content": {
            "application/json": {
                "examples": {
                    "texto_curto": {
                        "summary": "Texto da vaga insuficiente",
                        "value": {
                            "detail": [
                                {
                                    "loc": ["body", "texto_vaga"],
                                    "msg": "String should have at least 20 characters",
                                    "type": "string_too_short",
                                }
                            ]
                        },
                    },
                    "vaga_invalida": {
                        "summary": "IA não estruturou a vaga",
                        "value": {
                            "detail": "Falha ao processar o texto da vaga. Verifique a API e tente novamente."
                        },
                    },
                }
            }
        },
    },
    503: {
        "description": "Chave da IA não configurada no servidor",
        "content": {
            "application/json": {
                "example": {
                    "detail": "GEMINI_API_KEY não configurada. Defina a variável de ambiente."
                },
            }
        },
    },
    500: {
        "description": "Erro interno inesperado",
        "content": {
            "application/json": {
                "example": {"detail": "Erro interno ao processar triagem."},
            }
        },
    },
}

TEXTO_VAGA_EXAMPLE = (
    "Vaga: Desenvolvedor Python Pleno\n\n"
    "Requisitos obrigatórios:\n"
    "- 3+ anos de experiência com Python\n"
    "- Conhecimento em Git\n"
    "- Experiência com APIs REST\n\n"
    "Requisitos desejáveis:\n"
    "- FastAPI ou Django\n"
    "- Docker\n"
    "- PostgreSQL"
)
