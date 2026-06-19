"""
Triagem de Currículos — versão CLI legada.

Para a interface web, use:
  Backend:  cd backend && python run.py   (porta 8080)
  Frontend: cd frontend && python serve.py (porta 6500)
  Ou execute start.bat na raiz do projeto.
"""
import os
import re
import json
import time
import logging
import pdfplumber
from pathlib import Path
from typing import List
from pydantic import BaseModel, Field
from openai import OpenAI

# ================= CONFIGURAÇÃO =================
logging.basicConfig(level=logging.ERROR)

API_KEY = os.environ.get("DEEPSEEK_API_KEY")
if not API_KEY:
    raise EnvironmentError("❌ Variável DEEPSEEK_API_KEY não encontrada no ZSH.")

# Configurando o cliente OpenAI para apontar para o DeepSeek
client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")
MODELO = "deepseek-chat"

# ================= MODELOS =================

class PerfilVaga(BaseModel):
    titulo: str
    requisitos_obrigatorios: List[str]
    requisitos_desejaveis: List[str]

class VerificacaoRequisito(BaseModel):
    requisito: str
    atende: bool
    evidencia_literal: str = Field(default="")

class AnaliseCV(BaseModel):
    analise_obrigatorios: List[VerificacaoRequisito]
    analise_desejaveis: List[VerificacaoRequisito]

# ================= IA COM RETRY =================

def chamar_ia(prompt: str, schema: type):
    for tentativa in range(4):
        try:
            res = client.chat.completions.create(
                model=MODELO,
                messages=[
                    {"role": "system", "content": "Você é um assistente especialista em triagem de currículos e extração de dados. Retorne SEMPRE em formato JSON válido."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )

            texto_resposta = res.choices[0].message.content
            data = json.loads(texto_resposta)
            return schema.model_validate(data)

        except Exception as e:
            msg = str(e).lower()
            if "429" in msg or "503" in msg or "rate limit" in msg:
                espera = (tentativa + 1) * 10
                print(f" ⏳ API instável... aguardando {espera}s")
                time.sleep(espera)
            else:
                print(f" ❌ Erro crítico na IA: {e}")
                break
    return None

# ================= SCORE =================

def calcular_score_ponderado(analise: AnaliseCV) -> dict:
    total_obrig = len(analise.analise_obrigatorios)
    sucesso_obrig = sum(1 for r in analise.analise_obrigatorios if r.atende)
    total_desej = len(analise.analise_desejaveis)
    sucesso_desej = sum(1 for r in analise.analise_desejaveis if r.atende)

    score_obrig = (sucesso_obrig / total_obrig * 80) if total_obrig > 0 else 0
    score_desej = (sucesso_desej / total_desej * 20) if total_desej > 0 else 0
    score_final = int(score_obrig + score_desej)

    lacunas = [r.requisito for r in analise.analise_obrigatorios if not r.atende]
    todos_obrig = total_obrig == 0 or sucesso_obrig == total_obrig

    if todos_obrig:
        if score_final >= 85:
            status = "⭐ EXCELENTE"
        elif score_final >= 60:
            status = "✅ POTENCIAL"
        else:
            status = "⚠️ OK"
    elif sucesso_desej >= 1:
        status = "🎯 OPORTUNIDADE"
    elif score_final > 0:
        status = "📋 PARCIAL"
    else:
        status = "❌ ELIMINADO"

    return {"score": score_final, "status": status, "lacunas": lacunas}

# ================= INPUT EM BLOCO =================

def coletar_texto_vaga():
    print("\n📌 Cole o texto completo da vaga abaixo.")
    print("(Quando terminar de colar, digite 'FIM' em uma nova linha e aperte Enter para iniciar)\n")
    
    linhas = []
    while True:
        try:
            linha = input()
            if linha.strip().upper() == "FIM":
                break
            linhas.append(linha)
        except EOFError:
            break
            
    return "\n".join(linhas)

# ================= EXECUÇÃO =================

def executar():
    pdfs = list(Path(".").glob("*.pdf"))
    if not pdfs:
        return print("❌ Coloque os PDFs na mesma pasta do script.")

    print("\n" + "="*50)
    print("📋 TRIAGEM DE CURRÍCULOS (DeepSeek Edition)")
    print("="*50)

    # Coleta todo o texto de uma vez
    texto_vaga = coletar_texto_vaga()

    print("\n🤖 Estruturando os requisitos da vaga com IA...")
    
    # Pede para a IA extrair os dados e colocar no modelo PerfilVaga
    prompt_estruturacao = f"""
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
    
    perfil = chamar_ia(prompt_estruturacao, PerfilVaga)
    
    if not perfil:
        return print("❌ Falha ao processar o texto da vaga. Verifique a API e tente novamente.")

    print(f"\n🚀 Analisando {len(pdfs)} currículos para: {perfil.titulo}")
    print(f"   -> {len(perfil.requisitos_obrigatorios)} Obrigatórios detectados")
    print(f"   -> {len(perfil.requisitos_desejaveis)} Desejáveis detectados\n")

    ranking = []

    for arq in pdfs:
        print(f"🧐 {arq.name}...", end=" ")

        try:
            with pdfplumber.open(arq) as pdf:
                texto = "\n".join(p.extract_text() or "" for p in pdf.pages[:3])

            prompt_cv = f"""
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
            {texto[:4000]}
            """

            analise = chamar_ia(prompt_cv, AnaliseCV)

            if analise:
                res = calcular_score_ponderado(analise)

                if res["status"] == "❌ ELIMINADO":
                    print("Eliminado")
                    continue

                ranking.append({
                    "nome": arq.stem.title(),
                    "score": res["score"],
                    "status": res["status"]
                })

                print(f"{res['score']} pts")

            time.sleep(1) # O DeepSeek permite uma taxa de requisição que não necessita de tanto delay, ajustei para 1s

        except Exception as e:
            print(f"Erro: {e}")

    # ================= RESULTADO =================

    print("\n" + "🏆 RANKING FINAL ".center(50, "="))

    if not ranking:
        print("Nenhum candidato aprovado nos requisitos obrigatórios.")
    else:
        for i, r in enumerate(sorted(ranking, key=lambda x: x["score"], reverse=True), 1):
            print(f"{i}º {r['nome']} - {r['score']} pts | {r['status']}")

# ================= MAIN =================

if __name__ == "__main__":
    executar()