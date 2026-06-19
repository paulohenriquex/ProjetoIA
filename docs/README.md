# Documentação — Triagem de Currículos com IA

Sistema web para análise e ranking de candidatos a partir da descrição de uma vaga e currículos em PDF, utilizando **Google Gemini 3.1 Flash Lite**.

## Índice

| Documento | Conteúdo |
|-----------|----------|
| [01 — Visão Geral](01-visao-geral.md) | Objetivo, funcionalidades e fluxo do sistema |
| [02 — Arquitetura](02-arquitetura.md) | Estrutura do projeto, APIs e componentes |
| [03 — Motor de Match](03-motor-de-match.md) | Pseudocódigo, fórmulas matemáticas e validação do score |
| [04 — Instalação e Uso](04-instalacao-uso.md) | Como configurar, executar e utilizar a aplicação |
| [05 — Integração Frontend](05-integracao-frontend.md) | Guia para implementar no frontend do seu site |

## Versão Word (.docx) — para entrega

| Arquivo | Conteúdo |
|---------|----------|
| **03-Motor-de-Match.docx** | Motor de match: pseudocódigo e validação matemática |
| **Documentacao_Completa.docx** | Documentação técnica completa (visão geral + arquitetura + motor + instalação) |
| **05-Integracao-Frontend.txt** | Guia de integração API para copiar no seu site |

Para regenerar os `.docx` após editar os `.md`:

```bash
cd docs
python gerar_docx.py
```

## Resumo técnico

- **Backend:** FastAPI — porta `8080`
- **Frontend:** HTML/CSS/JS — porta `6500`
- **IA:** `gemini-3.1-flash-lite` (Google Generative AI)
- **Score:** cobertura ponderada (80% obrigatórios + 20% desejáveis)

## Estrutura do repositório

```
IA_Projeto/
├── backend/          # API FastAPI
├── frontend/         # Interface web
├── docs/             # Esta documentação
├── ProjetoMulher.py  # Versão CLI legada
├── .env.example      # Modelo de variáveis de ambiente
└── start.bat         # Script de inicialização (Windows)
```
