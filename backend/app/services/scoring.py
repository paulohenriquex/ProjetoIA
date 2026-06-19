from app.models import AnaliseCV, ScoreResult


def calcular_score_ponderado(analise: AnaliseCV) -> ScoreResult:
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
            status = "EXCELENTE"
        elif score_final >= 60:
            status = "POTENCIAL"
        else:
            status = "OK"
    elif sucesso_desej >= 1:
        status = "OPORTUNIDADE"
    elif score_final > 0:
        status = "PARCIAL"
    else:
        status = "ELIMINADO"

    return ScoreResult(score=score_final, status=status, lacunas=lacunas)
