import io
import json
import logging
import re
import time
from typing import Optional, Type, TypeVar

import google.generativeai as genai
import pdfplumber

from app.config import API_KEY, MAX_CV_CHARS, MAX_PDF_PAGES, MODELO
from app.models import AnaliseCV, PerfilVaga

logger = logging.getLogger(__name__)
T = TypeVar("T")

SYSTEM_PROMPT = (
    "Você é um assistente especialista em triagem de currículos e extração de dados. "
    "Retorne SEMPRE em formato JSON válido, sem markdown."
)

_model: genai.GenerativeModel | None = None


def get_model() -> genai.GenerativeModel:
    global _model
    if not API_KEY:
        raise RuntimeError("Variável GEMINI_API_KEY não configurada.")
    if _model is None:
        genai.configure(api_key=API_KEY)
        _model = genai.GenerativeModel(
            model_name=MODELO,
            system_instruction=SYSTEM_PROMPT,
            generation_config=genai.GenerationConfig(
                temperature=0.1,
                response_mime_type="application/json",
            ),
        )
    return _model


def parse_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)


def chamar_ia(prompt: str, schema: Type[T]) -> Optional[T]:
    model = get_model()

    for tentativa in range(4):
        try:
            res = model.generate_content(prompt)
            data = parse_json(res.text)
            return schema.model_validate(data)
        except Exception as e:
            msg = str(e).lower()
            if "429" in msg or "503" in msg or "rate limit" in msg or "resource_exhausted" in msg:
                time.sleep((tentativa + 1) * 10)
            else:
                logger.exception("Erro na chamada à IA: %s", e)
                break
    return None


def extrair_perfil_vaga(texto_vaga: str) -> Optional[PerfilVaga]:
    prompt = f"""
    Extraia o título da vaga, os requisitos obrigatórios e os desejáveis do texto abaixo.
    Retorne estritamente o JSON no seguinte formato:
    {{
      "titulo": "...",
      "requisitos_obrigatorios": ["...", "..."],
      "requisitos_desejaveis": ["...", "..."]
    }}

    TEXTO DA VAGA:
    {texto_vaga}
    """
    return chamar_ia(prompt, PerfilVaga)


def analisar_cv(texto_cv: str, perfil: PerfilVaga) -> Optional[AnaliseCV]:
    prompt = f"""
    Avalie este currículo.

    REGRAS:
    - Seja rigoroso com obrigatórios
    - Sem evidência clara = NÃO atende
    - Não inventar informação

    Retorne JSON:

    {{
      "analise_obrigatorios": [
        {{"requisito": "...", "atende": true/false, "evidencia_literal": "..."}}
      ],
      "analise_desejaveis": [
        {{"requisito": "...", "atende": true/false, "evidencia_literal": "..."}}
      ]
    }}

    OBRIGATÓRIOS:
    {perfil.requisitos_obrigatorios}

    DESEJÁVEIS:
    {perfil.requisitos_desejaveis}

    CV:
    {texto_cv[:MAX_CV_CHARS]}
    """
    return chamar_ia(prompt, AnaliseCV)


def extrair_texto_pdf(conteudo: bytes) -> str:
    with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages[:MAX_PDF_PAGES])
