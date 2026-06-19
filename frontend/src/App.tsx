import { useEffect, useState } from "react";
import { checkHealth } from "./api";
import BancoTalentosView from "./components/BancoTalentosView";
import TriagemView from "./components/TriagemView";

type Modo = "triagem" | "banco";

export default function App() {
  const [modo, setModo] = useState<Modo>("triagem");
  const [error, setError] = useState<string | null>(null);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
  const [backendPort, setBackendPort] = useState<number | null>(null);
  const [apiConfigured, setApiConfigured] = useState(true);
  const [model, setModel] = useState<string | null>(null);

  useEffect(() => {
    checkHealth()
      .then((h) => {
        setBackendOnline(h.status === "ok");
        setBackendPort(h.port);
        setApiConfigured(h.api_configured);
        setModel(h.model);
      })
      .catch(() => setBackendOnline(false));
  }, []);

  const handleModoChange = (novoModo: Modo) => {
    setModo(novoModo);
    setError(null);
  };

  const backendDisabled = backendOnline === false || !apiConfigured;

  return (
    <div className="app">
      <header className="header">
        <h1>Triagem de Currículos</h1>
        <p>Análise inteligente de candidatos com IA — Gemini</p>
        {backendOnline !== null && (
          <div
            className={`status-badge ${backendOnline && apiConfigured ? "online" : "offline"}`}
          >
            <span className="status-dot" />
            {backendOnline
              ? apiConfigured
                ? `Backend online (porta ${backendPort ?? "8080"}) · ${model ?? "IA"}`
                : "Backend online — configure GEMINI_API_KEY"
              : "Backend offline"}
          </div>
        )}
      </header>

      <nav className="tabs">
        <button
          type="button"
          className={`tab ${modo === "triagem" ? "active" : ""}`}
          onClick={() => handleModoChange("triagem")}
        >
          Triagem de currículos
        </button>
        <button
          type="button"
          className={`tab ${modo === "banco" ? "active" : ""}`}
          onClick={() => handleModoChange("banco")}
        >
          Banco de talentos
        </button>
      </nav>

      {error && <div className="error-banner">{error}</div>}

      {modo === "triagem" ? (
        <TriagemView disabled={backendDisabled} onError={setError} />
      ) : (
        <BancoTalentosView disabled={backendDisabled} onError={setError} />
      )}
    </div>
  );
}
