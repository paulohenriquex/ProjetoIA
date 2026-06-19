import { useCallback, useState } from "react";
import { analyzeResumes } from "../api";
import type { AnaliseResponse } from "../types";
import CandidatoCard from "./CandidatoCard";

interface TriagemViewProps {
  disabled: boolean;
  onError: (msg: string | null) => void;
}

export default function TriagemView({ disabled, onError }: TriagemViewProps) {
  const [textoVaga, setTextoVaga] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [resultado, setResultado] = useState<AnaliseResponse | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const addFiles = useCallback((newFiles: FileList | File[]) => {
    const pdfs = Array.from(newFiles).filter((f) =>
      f.name.toLowerCase().endsWith(".pdf"),
    );
    setFiles((prev) => {
      const names = new Set(prev.map((f) => f.name));
      return [...prev, ...pdfs.filter((f) => !names.has(f.name))];
    });
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      addFiles(e.dataTransfer.files);
    },
    [addFiles],
  );

  const handleSubmit = async () => {
    if (textoVaga.trim().length < 20) {
      onError("Cole a descrição completa da vaga (mínimo 20 caracteres).");
      return;
    }
    if (files.length === 0) {
      onError("Adicione ao menos um currículo em PDF.");
      return;
    }

    onError(null);
    setLoading(true);
    setResultado(null);

    try {
      const res = await analyzeResumes(textoVaga, files);
      setResultado(res);
    } catch (e) {
      onError(e instanceof Error ? e.message : "Erro desconhecido");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="grid">
        <section className="card">
          <h2>
            <span className="card-icon">📋</span>
            Descrição da vaga
          </h2>
          <textarea
            className="vaga-input"
            placeholder="Cole aqui o texto completo da vaga: título, requisitos obrigatórios, desejáveis, responsabilidades..."
            value={textoVaga}
            onChange={(e) => setTextoVaga(e.target.value)}
            disabled={loading}
          />
        </section>

        <section className="card">
          <h2>
            <span className="card-icon">📄</span>
            Currículos (PDF)
          </h2>
          <div
            className={`dropzone ${dragOver ? "dragover" : ""}`}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => document.getElementById("triagem-file-input")?.click()}
          >
            <p>
              <strong>Clique</strong> ou arraste PDFs aqui
            </p>
            <p>Múltiplos arquivos suportados</p>
          </div>
          <input
            id="triagem-file-input"
            type="file"
            accept=".pdf"
            multiple
            hidden
            onChange={(e) => e.target.files && addFiles(e.target.files)}
          />
          {files.length > 0 && (
            <div className="file-list">
              {files.map((f) => (
                <div key={f.name} className="file-item">
                  <span>{f.name}</span>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setFiles((prev) => prev.filter((x) => x.name !== f.name));
                    }}
                    disabled={loading}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      <div className="actions">
        <button
          className="btn-primary"
          onClick={handleSubmit}
          disabled={loading || disabled}
        >
          {loading ? "Analisando..." : "Iniciar triagem"}
        </button>
      </div>

      {loading && (
        <div className="loading">
          <div className="spinner" />
          <p>Processando vaga e currículos... Isso pode levar alguns minutos.</p>
        </div>
      )}

      {resultado && !loading && (
        <section className="results">
          <div className="results-header">
            <h2>{resultado.titulo_vaga}</h2>
            <div className="stats">
              <span className="stat">
                <strong>{resultado.total_cvs}</strong> CVs
              </span>
              <span className="stat">
                <strong>{resultado.aprovados}</strong> aprovados
              </span>
              <span className="stat">
                <strong>{resultado.eliminados}</strong> eliminados
              </span>
            </div>
          </div>

          {resultado.requisitos_obrigatorios.length > 0 && (
            <>
              <div className="section-title">Requisitos obrigatórios detectados</div>
              <div className="requisitos">
                {resultado.requisitos_obrigatorios.map((r) => (
                  <span key={r} className="tag obrigatorio">
                    {r}
                  </span>
                ))}
              </div>
            </>
          )}

          {resultado.requisitos_desejaveis.length > 0 && (
            <>
              <div className="section-title">Requisitos desejáveis detectados</div>
              <div className="requisitos">
                {resultado.requisitos_desejaveis.map((r) => (
                  <span key={r} className="tag desejavel">
                    {r}
                  </span>
                ))}
              </div>
            </>
          )}

          <div className="section-title">Ranking de candidatos</div>
          <div className="candidatos-list">
            {resultado.candidatos.map((c, i) => (
              <CandidatoCard key={c.nome + i} candidato={c} rank={i + 1} />
            ))}
          </div>
        </section>
      )}
    </>
  );
}
