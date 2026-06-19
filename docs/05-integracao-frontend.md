# 05 — Integração Frontend (seu site)

Guia para consumir a API de Triagem de Currículos a partir de qualquer frontend: React, Vue, Angular, HTML puro, Next.js, etc.

---

## 1. URL base da API

| Ambiente | URL |
|----------|-----|
| Desenvolvimento local | `http://localhost:8080` |
| Produção | `https://seu-dominio.com` ou subdomínio da API |

Configure via variável de ambiente no seu projeto:

```env
# .env do seu site
VITE_API_URL=http://localhost:8080
# ou NEXT_PUBLIC_API_URL=...
# ou REACT_APP_API_URL=...
```

```javascript
const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8080";
```

---

## 2. CORS

O backend já aceita requisições de **qualquer origem** (`allow_origins: ["*"]`).

Seu site pode chamar a API diretamente do navegador, desde que:

- O backend esteja acessível na URL configurada
- Em produção, use **HTTPS** na API se o site for HTTPS (evita mixed content)

### Alternativa: proxy no seu servidor

Se preferir não expor a porta 8080, configure proxy no Nginx/Vercel/Netlify:

```nginx
# Nginx — seu-site.com/api → backend:8080/api
location /api/ {
    proxy_pass http://127.0.0.1:8080/api/;
    proxy_read_timeout 600s;
    client_max_body_size 50M;
}
```

Com proxy, use `API_BASE = ""` (mesma origem) ou `API_BASE = "https://seu-site.com"`.

---

## 3. Endpoints

### `GET /api/health`

Verifica se a API está online.

**Request:** sem corpo.

**Response 200:**
```json
{
  "status": "ok",
  "api_configured": true,
  "model": "gemini-3.1-flash-lite",
  "port": 8080
}
```

**Uso:** exibir status "API online/offline" e desabilitar botão se offline.

---

### `POST /api/analyze`

Executa a triagem completa.

**Content-Type:** `multipart/form-data` (não envie JSON).

**Campos:**

| Campo | Tipo | Obrigatório | Regra |
|-------|------|-------------|-------|
| `texto_vaga` | string | Sim | Mínimo 20 caracteres |
| `curriculos` | File[] | Sim | Um ou mais PDFs; campo repetido para múltiplos arquivos |

**Response 200:**
```json
{
  "titulo_vaga": "Desenvolvedor Python",
  "total_cvs": 3,
  "aprovados": 2,
  "eliminados": 1,
  "requisitos_obrigatorios": ["Python 3 anos", "Git"],
  "requisitos_desejaveis": ["FastAPI", "Docker"],
  "candidatos": [
    {
      "nome": "Joao Silva",
      "score": 90,
      "status": "EXCELENTE",
      "eliminado": false,
      "lacunas": [],
      "analise_obrigatorios": [
        {
          "requisito": "Python 3 anos",
          "atende": true,
          "evidencia_literal": "5 anos de experiência com Python"
        }
      ],
      "analise_desejaveis": [
        {
          "requisito": "FastAPI",
          "atende": true,
          "evidencia_literal": "Projetos com FastAPI"
        }
      ]
    }
  ]
}
```

**Erros comuns:**

| HTTP | detail | Causa |
|------|--------|-------|
| 400 | Envie ao menos um arquivo PDF. | Nenhum PDF válido |
| 422 | Falha ao processar o texto da vaga... | IA não estruturou a vaga |
| 422 | String should have at least 20 characters | `texto_vaga` muito curto |
| 503 | GEMINI_API_KEY não configurada | Backend sem chave |
| 500 | Erro interno ao processar triagem. | Erro inesperado |

---

## 4. Tipos TypeScript

Copie para o seu projeto (`types/triagem.ts`):

```typescript
export interface VerificacaoRequisito {
  requisito: string;
  atende: boolean;
  evidencia_literal: string;
}

export interface CandidatoResultado {
  nome: string;
  score: number;
  status: "EXCELENTE" | "POTENCIAL" | "OK" | "OPORTUNIDADE" | "PARCIAL" | "ELIMINADO" | "ERRO";
  eliminado: boolean;
  lacunas: string[];
  analise_obrigatorios?: VerificacaoRequisito[];
  analise_desejaveis?: VerificacaoRequisito[];
}

export interface AnaliseResponse {
  titulo_vaga: string;
  total_cvs: number;
  aprovados: number;
  eliminados: number;
  requisitos_obrigatorios: string[];
  requisitos_desejaveis: string[];
  candidatos: CandidatoResultado[];
}

export interface HealthResponse {
  status: string;
  api_configured: boolean;
  model: string;
  port: number;
}
```

---

## 5. Cliente API (JavaScript/TypeScript)

```typescript
const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8080";

export async function checkHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/api/health`);
  if (!res.ok) throw new Error("API indisponível");
  return res.json();
}

export async function analyzeResumes(
  textoVaga: string,
  files: File[],
): Promise<AnaliseResponse> {
  const form = new FormData();
  form.append("texto_vaga", textoVaga);

  files
    .filter((f) => f.name.toLowerCase().endsWith(".pdf"))
    .forEach((file) => form.append("curriculos", file));

  const res = await fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    body: form,
    // Não defina Content-Type — o browser define o boundary do multipart
  });

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    const msg = Array.isArray(data.detail)
      ? data.detail.map((d: { msg?: string }) => d.msg ?? d).join(", ")
      : data.detail ?? "Erro ao processar triagem";
    throw new Error(msg);
  }

  return data;
}
```

---

## 6. Exemplo React

```tsx
import { useState } from "react";
import { analyzeResumes, checkHealth } from "./api/triagem";
import type { AnaliseResponse } from "./types/triagem";

export function TriagemPage() {
  const [textoVaga, setTextoVaga] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [resultado, setResultado] = useState<AnaliseResponse | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErro(null);

    if (textoVaga.trim().length < 20) {
      setErro("Descrição da vaga deve ter pelo menos 20 caracteres.");
      return;
    }
    if (!files.length) {
      setErro("Adicione ao menos um PDF.");
      return;
    }

    setLoading(true);
    try {
      const res = await analyzeResumes(textoVaga, files);
      setResultado(res);
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Erro desconhecido");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <textarea
        value={textoVaga}
        onChange={(e) => setTextoVaga(e.target.value)}
        placeholder="Cole a descrição da vaga..."
        rows={10}
      />

      <input
        type="file"
        accept=".pdf"
        multiple
        onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
      />

      <button type="submit" disabled={loading}>
        {loading ? "Analisando..." : "Iniciar triagem"}
      </button>

      {erro && <p className="erro">{erro}</p>}

      {resultado && (
        <section>
          <h2>{resultado.titulo_vaga}</h2>
          <p>{resultado.aprovados} aprovados / {resultado.eliminados} eliminados</p>

          {resultado.candidatos.map((c, i) => (
            <article key={c.nome + i}>
              <h3>{i + 1}º — {c.nome}</h3>
              <span>{c.score} pts</span>
              <span>{c.status}</span>
              {c.lacunas.length > 0 && (
                <ul>{c.lacunas.map((l) => <li key={l}>{l}</li>)}</ul>
              )}
            </article>
          ))}
        </section>
      )}
    </form>
  );
}
```

---

## 7. Exemplo fetch puro (HTML + JS)

```html
<textarea id="vaga" rows="8"></textarea>
<input id="pdfs" type="file" accept=".pdf" multiple />
<button id="btn">Analisar</button>
<pre id="out"></pre>

<script>
  const API = "http://localhost:8080";

  document.getElementById("btn").onclick = async () => {
    const texto = document.getElementById("vaga").value.trim();
    const input = document.getElementById("pdfs");
    const form = new FormData();

    form.append("texto_vaga", texto);
    Array.from(input.files).forEach((f) => form.append("curriculos", f));

    const res = await fetch(`${API}/api/analyze`, { method: "POST", body: form });
    const data = await res.json();
    document.getElementById("out").textContent = JSON.stringify(data, null, 2);
  };
</script>
```

---

## 8. Fluxo recomendado na UI

```
1. Ao carregar a página → GET /api/health
2. Usuário preenche vaga + seleciona PDFs
3. Validação local (≥20 chars, ≥1 PDF)
4. POST /api/analyze com loading (pode levar minutos)
5. Exibir:
   - Título da vaga detectado
   - Tags de requisitos obrigatórios/desejáveis
   - Ranking de candidatos (score decrescente)
   - Detalhes expandíveis: lacunas, evidências
```

### Tempo de resposta

- 1 CV ≈ 10–30 segundos (depende da IA)
- N CVs ≈ N × (tempo por CV + 1s de intervalo interno)
- Configure timeout alto no fetch ou use `AbortController` com aviso ao usuário

```javascript
// Sem timeout no fetch — aguarda até completar
await fetch(`${API_BASE}/api/analyze`, { method: "POST", body: form });
```

---

## 9. Status dos candidatos (para exibir no site)

| status | Cor sugerida | Label no site |
|--------|--------------|---------------|
| `EXCELENTE` | Roxo/verde | Excelente candidato |
| `POTENCIAL` | Verde | Bom potencial |
| `OK` | Amarelo | Atende o básico |
| `OPORTUNIDADE` | Azul | Oportunidade (desejáveis atendidos) |
| `PARCIAL` | Amarelo escuro | Perfil parcial |
| `ELIMINADO` | Vermelho | Não recomendado |
| `ERRO` | Cinza | Erro no processamento |

```javascript
function labelStatus(status) {
  const map = {
    EXCELENTE: "Excelente",
    POTENCIAL: "Bom potencial",
    OK: "Atende o básico",
    OPORTUNIDADE: "Oportunidade",
    PARCIAL: "Perfil parcial",
    ELIMINADO: "Eliminado",
    ERRO: "Erro",
  };
  return map[status] ?? status;
}
```

---

## 10. Checklist de implementação

- [ ] Definir `API_BASE` (env ou proxy)
- [ ] Tela com textarea da vaga
- [ ] Upload múltiplo de PDF (`accept=".pdf"`)
- [ ] Validação local antes do POST
- [ ] Indicador de loading durante análise
- [ ] Tratamento de erros (`detail` da API)
- [ ] Listagem do ranking com score e status
- [ ] Detalhe por candidato (lacunas + evidências)
- [ ] Health check no carregamento da página
- [ ] Timeout/proxy configurado em produção

---

## 11. Swagger (documentação interativa)

Com o backend rodando, acesse:

- **Swagger UI:** http://localhost:8080/docs
- **ReDoc:** http://localhost:8080/redoc

Útil para testar endpoints antes de integrar no site.
