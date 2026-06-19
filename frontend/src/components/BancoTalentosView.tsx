import { useCallback, useState } from "react";
import { analyzeTalentBank } from "../api";
import type { AnaliseBancoTalentosResponse, ResultadoVagaTalento, VagaTalentoInput } from "../types";

function statusClass(status: string): string {
  return status.toLowerCase().replace(/_/g, "-");
}

function novaVaga(index: number): VagaTalentoInput {
  return {
    vaga_id: String(index + 1),
    texto_vaga: "",
    candidato_cadastrado: true,
  };
}

function VagaResultadoCard({ resultado }: { resultado: ResultadoVagaTalento }) {
  const [expanded, setExpanded] = useState(false);
  const cls = statusClass(resultado.status);

  return (
    <div className={`candidato-card vaga-card ${expanded ? "expanded" : ""}`}>
      <div className="candidato-header" onClick={() => setExpanded(!expanded)}>
        <div className="candidato-info">
          <h3>{resultado.titulo_vaga}</h3>
          <div className="candidato-meta">ID: {resultado.vaga_id}</div>
        </div>
        {resultado.analisado && (
          <span className={`score-badge ${cls}`}>{resultado.score}</span>
        )}
        <span className={`status-label ${cls}`}>{resultado.status.replace(/_/g, " ")}</span>
        <span className="chevron">▼</span>
      </div>

      {expanded && (
        <div className="candidato-details">
          {!resultado.candidato_cadastrado && (
            <div className="info-box muted">
              Candidato não cadastrado nesta vaga — análise não executada.
            </div>
          )}

          {resultado.pontos_melhorar.length > 0 && (
            <div className="lacunas melhorias">
              <strong>Pontos a melhorar:</strong>
              <ul>
                {resultado.pontos_melhorar.map((p) => (
                  <li key={p}>{p}</li>
                ))}
              </ul>
            </div>
          )}

          {resultado.lacunas.length > 0 && (
            <div className="lacunas">
              <strong>Lacunas:</strong>
              <ul>
                {resultado.lacunas.map((l) => (
                  <li key={l}>{l}</li>
                ))}
              </ul>
            </div>
          )}

          {resultado.analise_obrigatorios && resultado.analise_obrigatorios.length > 0 && (
            <>
              <div className="section-title">Requisitos obrigatórios</div>
              <div className="requisito-grid">
                {resultado.analise_obrigatorios.map((r) => (
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

          {resultado.analise_desejaveis && resultado.analise_desejaveis.length > 0 && (
            <>
              <div className="section-title">Requisitos desejáveis</div>
              <div className="requisito-grid">
                {resultado.analise_desejaveis.map((r) => (
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

interface BancoTalentosViewProps {
  disabled: boolean;
  onError: (msg: string | null) => void;
}

export default function BancoTalentosView({ disabled, onError }: BancoTalentosViewProps) {
  const [curriculo, setCurriculo] = useState<File | null>(null);
  const [vagas, setVagas] = useState<VagaTalentoInput[]>([novaVaga(0)]);
  const [loading, setLoading] = useState(false);
  const [resultado, setResultado] = useState<AnaliseBancoTalentosResponse | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const setVaga = (index: number, patch: Partial<VagaTalentoInput>) => {
    setVagas((prev) =>
      prev.map((v, i) => (i === index ? { ...v, ...patch } : v)),
    );
  };

  const addVaga = () => {
    setVagas((prev) => [...prev, novaVaga(prev.length)]);
  };

  const removeVaga = (index: number) => {
    setVagas((prev) => (prev.length > 1 ? prev.filter((_, i) => i !== index) : prev));
  };

  const handleFile = useCallback((file: File | null) => {
    if (file && file.name.toLowerCase().endsWith(".pdf")) {
      setCurriculo(file);
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  const handleSubmit = async () => {
    if (!curriculo) {
      onError("Envie o currículo do candidato em PDF.");
      return;
    }

    const vagasValidas = vagas.filter((v) => v.texto_vaga.trim().length >= 20);
    if (vagasValidas.length === 0) {
      onError("Adicione ao menos uma vaga com descrição de 20+ caracteres.");
      return;
    }

    const ids = new Set<string>();
    for (const vaga of vagasValidas) {
      if (!vaga.vaga_id.trim()) {
        onError("Todas as vagas precisam de um ID.");
        return;
      }
      if (ids.has(vaga.vaga_id)) {
        onError("Cada vaga deve ter um ID único.");
        return;
      }
      ids.add(vaga.vaga_id);
    }

    onError(null);
    setLoading(true);
    setResultado(null);

    try {
      const res = await analyzeTalentBank(curriculo, vagasValidas);
      setResultado(res);
    } catch (e) {
      onError(e instanceof Error ? e.message : "Erro desconhecido");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="grid banco-grid">
        <section className="card">
          <h2>
            <span className="card-icon">📄</span>
            Currículo do candidato
          </h2>
          <div
            className={`dropzone ${dragOver ? "dragover" : ""}`}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => document.getElementById("banco-file-input")?.click()}
          >
            <p>
              <strong>Clique</strong> ou arraste um PDF aqui
            </p>
            <p>Apenas um currículo por análise</p>
          </div>
          <input
            id="banco-file-input"
            type="file"
            accept=".pdf"
            hidden
            onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
          />
          {curriculo && (
            <div className="file-list">
              <div className="file-item">
                <span>{curriculo.name}</span>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setCurriculo(null);
                  }}
                  disabled={loading}
                >
                  ×
                </button>
              </div>
            </div>
          )}
        </section>

        <section className="card vagas-card">
          <div className="card-header-row">
            <h2>
              <span className="card-icon">💼</span>
              Vagas cadastradas
            </h2>
            <button type="button" className="btn-secondary" onClick={addVaga} disabled={loading}>
              + Vaga
            </button>
          </div>

          <div className="vagas-list">
            {vagas.map((vaga, index) => (
              <div key={index} className="vaga-form">
                <div className="vaga-form-header">
                  <label className="field-inline">
                    <span>ID</span>
                    <input
                      type="text"
                      value={vaga.vaga_id}
                      onChange={(e) => setVaga(index, { vaga_id: e.target.value })}
                      disabled={loading}
                      placeholder="ex: vaga-001"
                    />
                  </label>
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={vaga.candidato_cadastrado}
                      onChange={(e) =>
                        setVaga(index, { candidato_cadastrado: e.target.checked })
                      }
                      disabled={loading}
                    />
                    Candidato cadastrado
                  </label>
                  {vagas.length > 1 && (
                    <button
                      type="button"
                      className="btn-remove"
                      onClick={() => removeVaga(index)}
                      disabled={loading}
                      aria-label="Remover vaga"
                    >
                      ×
                    </button>
                  )}
                </div>
                <textarea
                  className="vaga-input vaga-input-sm"
                  placeholder="Descrição completa da vaga (mín. 20 caracteres)..."
                  value={vaga.texto_vaga}
                  onChange={(e) => setVaga(index, { texto_vaga: e.target.value })}
                  disabled={loading}
                />
              </div>
            ))}
          </div>
        </section>
      </div>

      <div className="actions">
        <button
          className="btn-primary"
          onClick={handleSubmit}
          disabled={loading || disabled}
        >
          {loading ? "Analisando..." : "Analisar candidato nas vagas"}
        </button>
      </div>

      {loading && (
        <div className="loading">
          <div className="spinner" />
          <p>Analisando currículo contra as vagas... Isso pode levar alguns minutos.</p>
        </div>
      )}

      {resultado && !loading && (
        <section className="results">
          <div className="results-header">
            <h2>{resultado.candidato}</h2>
            <div className="stats">
              <span className="stat">
                <strong>{resultado.total_vagas_recebidas}</strong> vagas
              </span>
              <span className="stat">
                <strong>{resultado.vagas_aprovadas}</strong> aprovadas
              </span>
              <span className="stat">
                <strong>{resultado.vagas_reprovadas}</strong> reprovadas
              </span>
              <span className="stat">
                <strong>{resultado.vagas_nao_cadastradas}</strong> não cadastradas
              </span>
            </div>
          </div>

          <div className="section-title">Resultado por vaga</div>
          <div className="candidatos-list">
            {resultado.resultados.map((r) => (
              <VagaResultadoCard key={r.vaga_id} resultado={r} />
            ))}
          </div>
        </section>
      )}
    </>
  );
}
