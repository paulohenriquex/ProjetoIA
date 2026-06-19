import { useState } from "react";
import type { CandidatoResultado } from "../types";

function statusClass(status: string): string {
  return status.toLowerCase().replace(/\s/g, "-");
}

function metaCandidato(c: CandidatoResultado): string {
  if (c.eliminado) return "Não atende requisitos mínimos";
  if (c.status === "OPORTUNIDADE") {
    return `${c.score} pts — faltam obrigatórios, mas atende desejáveis`;
  }
  if (c.status === "PARCIAL") return `${c.score} pts — atende parte dos requisitos`;
  return `${c.score} pontos`;
}

export default function CandidatoCard({
  candidato,
  rank,
}: {
  candidato: CandidatoResultado;
  rank: number;
}) {
  const [expanded, setExpanded] = useState(false);
  const cls = statusClass(candidato.status);

  return (
    <div className={`candidato-card ${expanded ? "expanded" : ""}`}>
      <div className="candidato-header" onClick={() => setExpanded(!expanded)}>
        <span className="candidato-rank">{rank}º</span>
        <div className="candidato-info">
          <h3>{candidato.nome}</h3>
          <div className="candidato-meta">{metaCandidato(candidato)}</div>
        </div>
        {!candidato.eliminado && (
          <span className={`score-badge ${cls}`}>{candidato.score}</span>
        )}
        <span className={`status-label ${cls}`}>{candidato.status}</span>
        <span className="chevron">▼</span>
      </div>

      {expanded && (
        <div className="candidato-details">
          {candidato.lacunas.length > 0 && (
            <div className="lacunas">
              <strong>Lacunas identificadas:</strong>
              <ul>
                {candidato.lacunas.map((l) => (
                  <li key={l}>{l}</li>
                ))}
              </ul>
            </div>
          )}

          {candidato.analise_obrigatorios && candidato.analise_obrigatorios.length > 0 && (
            <>
              <div className="section-title">Requisitos obrigatórios</div>
              <div className="requisito-grid">
                {candidato.analise_obrigatorios.map((r) => (
                  <div key={r.requisito} className="requisito-item">
                    <span className="icon">{r.atende ? "✅" : "❌"}</span>
                    <div>
                      {r.requisito}
                      {r.evidencia_literal && (
                        <span className="evidencia">"{r.evidencia_literal}"</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}

          {candidato.analise_desejaveis && candidato.analise_desejaveis.length > 0 && (
            <>
              <div className="section-title">Requisitos desejáveis</div>
              <div className="requisito-grid">
                {candidato.analise_desejaveis.map((r) => (
                  <div key={r.requisito} className="requisito-item">
                    <span className="icon">{r.atende ? "✅" : "➖"}</span>
                    <div>
                      {r.requisito}
                      {r.evidencia_literal && (
                        <span className="evidencia">"{r.evidencia_literal}"</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
