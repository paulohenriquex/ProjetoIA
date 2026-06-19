import asyncio
import logging
from typing import List

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models import (
    AnaliseBancoTalentosResponse,
    AnaliseResponse,
    CandidatoResultado,
    ResultadoVagaTalento,
    VagaTalentoInput,
)
from app.services.ai_service import analisar_cv, extrair_perfil_vaga, extrair_texto_pdf
from app.services.scoring import calcular_score_ponderado
from app.services.vagas_service import salvar_analise

logger = logging.getLogger(__name__)


def _extrair_nome_candidato(nome_arquivo: str | None) -> str:
    nome = nome_arquivo or "Candidato"
    return nome.rsplit(".", 1)[0].replace("_", " ").title()


async def processar_triagem(
    texto_vaga: str,
    arquivos: List[UploadFile],
    db: Session,
    vaga_id: int | None = None,
) -> AnaliseResponse:
    perfil = extrair_perfil_vaga(texto_vaga)
    if not perfil:
        raise ValueError("Falha ao processar o texto da vaga. Verifique a API e tente novamente.")

    candidatos: List[CandidatoResultado] = []
    eliminados = 0

    for arquivo in arquivos:
        nome = arquivo.filename or "Candidato"
        nome_exibicao = _extrair_nome_candidato(nome)

        try:
            conteudo = await arquivo.read()
            texto_cv = extrair_texto_pdf(conteudo)

            if not texto_cv.strip():
                candidatos.append(
                    CandidatoResultado(
                        nome=nome_exibicao, score=0, status="ERRO", eliminado=True,
                        lacunas=["PDF sem texto legível"],
                    )
                )
                eliminados += 1
                continue

            analise = analisar_cv(texto_cv, perfil)
            if not analise:
                candidatos.append(
                    CandidatoResultado(
                        nome=nome_exibicao, score=0, status="ERRO", eliminado=True,
                        lacunas=["Falha na análise por IA"],
                    )
                )
                eliminados += 1
                continue

            resultado = calcular_score_ponderado(analise)
            eliminado = resultado.status == "ELIMINADO"

            obrig_dicts = [r.model_dump() for r in analise.analise_obrigatorios]
            desej_dicts = [r.model_dump() for r in analise.analise_desejaveis]

            # Salva no banco se houver vaga cadastrada
            if vaga_id and db:
                try:
                    from app.services.vagas_service import cadastrar_candidata
                    email_base = nome_exibicao.lower().replace(" ", ".") + "@cv.com"
                    candidata = cadastrar_candidata(db, nome_exibicao, email_base, texto_cv)
                    salvar_analise(
                        db, vaga_id, candidata.id,
                        resultado.score, resultado.status, resultado.lacunas,
                        obrig_dicts, desej_dicts,
                    )
                    logger.info("Análise salva no banco: candidata=%s vaga=%d score=%d", nome_exibicao, vaga_id, resultado.score)
                except Exception as e:
                    logger.warning("Falha ao salvar análise no banco: %s", e)

            candidatos.append(
                CandidatoResultado(
                    nome=nome_exibicao,
                    score=resultado.score,
                    status=resultado.status,
                    eliminado=eliminado,
                    lacunas=resultado.lacunas,
                    analise_obrigatorios=analise.analise_obrigatorios,
                    analise_desejaveis=analise.analise_desejaveis,
                )
            )
            if eliminado:
                eliminados += 1

            await asyncio.sleep(1)

        except Exception as e:
            logger.exception("Erro ao processar %s: %s", nome, e)
            candidatos.append(
                CandidatoResultado(
                    nome=nome_exibicao, score=0, status="ERRO", eliminado=True,
                    lacunas=[str(e)],
                )
            )
            eliminados += 1

    aprovados = [c for c in candidatos if not c.eliminado]
    aprovados.sort(key=lambda c: c.score, reverse=True)
    eliminados_list = [c for c in candidatos if c.eliminado]

    return AnaliseResponse(
        titulo_vaga=perfil.titulo,
        total_cvs=len(arquivos),
        aprovados=len(aprovados),
        eliminados=eliminados,
        requisitos_obrigatorios=perfil.requisitos_obrigatorios,
        requisitos_desejaveis=perfil.requisitos_desejaveis,
        candidatos=aprovados + eliminados_list,
    )


async def processar_banco_talentos(
    curriculo: UploadFile,
    vagas: List[VagaTalentoInput],
    db: Session,
) -> AnaliseBancoTalentosResponse:
    candidato = _extrair_nome_candidato(curriculo.filename)
    resultados: List[ResultadoVagaTalento] = []

    conteudo = await curriculo.read()
    texto_cv = extrair_texto_pdf(conteudo)
    if not texto_cv.strip():
        raise ValueError("Currículo sem texto legível.")

    vagas_analisadas = 0
    vagas_nao_cadastradas = 0
    vagas_aprovadas = 0
    vagas_reprovadas = 0

    for vaga in vagas:
        if not vaga.candidato_cadastrado:
            resultados.append(ResultadoVagaTalento(
                vaga_id=vaga.vaga_id, titulo_vaga="Não analisada",
                candidato_cadastrado=False, analisado=False,
                status="NAO_CADASTRADO",
            ))
            vagas_nao_cadastradas += 1
            continue

        perfil = extrair_perfil_vaga(vaga.texto_vaga)
        if not perfil:
            resultados.append(ResultadoVagaTalento(
                vaga_id=vaga.vaga_id, titulo_vaga="Erro ao processar vaga",
                candidato_cadastrado=True, analisado=False, status="ERRO_VAGA",
            ))
            vagas_reprovadas += 1
            continue

        analise = analisar_cv(texto_cv, perfil)
        if not analise:
            resultados.append(ResultadoVagaTalento(
                vaga_id=vaga.vaga_id, titulo_vaga=perfil.titulo,
                candidato_cadastrado=True, analisado=False, status="ERRO_ANALISE",
            ))
            vagas_reprovadas += 1
            continue

        resultado = calcular_score_ponderado(analise)
        aprovado = not resultado.lacunas
        status = "APROVADA" if aprovado else "REPROVADA"

        # Salva no banco
        if db:
            try:
                from app.services.vagas_service import cadastrar_candidata
                email_base = candidato.lower().replace(" ", ".") + "@cv.com"
                candidata = cadastrar_candidata(db, candidato, email_base, texto_cv)
                obrig = [r.model_dump() for r in analise.analise_obrigatorios]
                desej = [r.model_dump() for r in analise.analise_desejaveis]
                salvar_analise(db, int(vaga.vaga_id), candidata.id,
                               resultado.score, status, resultado.lacunas, obrig, desej)
            except Exception as e:
                logger.warning("Falha ao salvar análise no banco: %s", e)

        resultados.append(ResultadoVagaTalento(
            vaga_id=vaga.vaga_id, titulo_vaga=perfil.titulo,
            candidato_cadastrado=True, analisado=True,
            score=resultado.score, status=status,
            lacunas=resultado.lacunas,
            analise_obrigatorios=analise.analise_obrigatorios,
            analise_desejaveis=analise.analise_desejaveis,
        ))
        vagas_analisadas += 1
        if aprovado:
            vagas_aprovadas += 1
        else:
            vagas_reprovadas += 1

        await asyncio.sleep(1)

    return AnaliseBancoTalentosResponse(
        candidato=candidato,
        total_vagas_recebidas=len(vagas),
        vagas_analisadas=vagas_analisadas,
        vagas_nao_cadastradas=vagas_nao_cadastradas,
        vagas_aprovadas=vagas_aprovadas,
        vagas_reprovadas=vagas_reprovadas,
        resultados=resultados,
    )
