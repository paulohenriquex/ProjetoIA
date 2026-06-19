import type {
  AnaliseBancoTalentosResponse,
  AnaliseResponse,
  HealthResponse,
  VagaTalentoInput,
} from "./types";

function parseApiError(data: unknown, fallback: string): string {
  if (!data || typeof data !== "object") return fallback;
  const detail = (data as { detail?: unknown }).detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => {
        if (typeof d === "string") return d;
        if (d && typeof d === "object" && "msg" in d) {
          return String((d as { msg?: string }).msg ?? d);
        }
        return String(d);
      })
      .join(", ");
  }
  if (typeof detail === "string") return detail;
  return fallback;
}

export async function checkHealth(): Promise<HealthResponse> {
  const res = await fetch("/api/health");
  if (!res.ok) throw new Error("Backend indisponível");
  return res.json();
}

export async function analyzeResumes(
  textoVaga: string,
  files: File[],
): Promise<AnaliseResponse> {
  const form = new FormData();
  form.append("texto_vaga", textoVaga);
  files.forEach((file) => form.append("curriculos", file));

  const res = await fetch("/api/analyze", {
    method: "POST",
    body: form,
  });

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    throw new Error(parseApiError(data, "Erro ao processar triagem"));
  }

  return data;
}

export async function analyzeTalentBank(
  curriculo: File,
  vagas: VagaTalentoInput[],
): Promise<AnaliseBancoTalentosResponse> {
  const form = new FormData();
  form.append("curriculo", curriculo);
  form.append("vagas_json", JSON.stringify(vagas));

  const res = await fetch("/api/analyze-talent-bank", {
    method: "POST",
    body: form,
  });

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    throw new Error(parseApiError(data, "Erro ao analisar banco de talentos"));
  }

  return data;
}
