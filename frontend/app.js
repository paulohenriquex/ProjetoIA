const API_BASE = "";

let files = [];

const $ = (sel) => document.querySelector(sel);

function showError(msg) {
  const el = $("#error-banner");
  el.textContent = msg;
  el.classList.remove("hidden");
}

function hideError() {
  $("#error-banner").classList.add("hidden");
}

function statusClass(status) {
  return status.toLowerCase().replace(/\s/g, "-").replace(/[^\w-]/g, "");
}

function metaCandidato(c) {
  if (c.eliminado) return "Não atende requisitos mínimos";
  if (c.status === "OPORTUNIDADE") return `${c.score} pts — faltam obrigatórios, mas atende desejáveis`;
  if (c.status === "PARCIAL") return `${c.score} pts — atende parte dos requisitos`;
  return `${c.score} pontos`;
}

async function checkHealth() {
  const badge = $("#status-badge");
  const text = $("#status-text");
  badge.classList.remove("hidden");

  try {
    const res = await fetch(`${API_BASE}/api/health`);
    if (!res.ok) throw new Error();
    const data = await res.json();
    badge.classList.remove("offline");
    badge.classList.add("online");
    text.textContent = data.api_configured
      ? "Backend online (porta 8080)"
      : "Backend online — configure GEMINI_API_KEY";
  } catch {
    badge.classList.remove("online");
    badge.classList.add("offline");
    text.textContent = "Backend offline (porta 8080)";
    $("#btn-submit").disabled = true;
  }
}

function renderFiles() {
  const list = $("#file-list");
  list.innerHTML = files
    .map(
      (f, i) => `
    <div class="file-item">
      <span>${f.name}</span>
      <button type="button" data-index="${i}" aria-label="Remover">×</button>
    </div>`,
    )
    .join("");

  list.querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      files.splice(Number(btn.dataset.index), 1);
      renderFiles();
    });
  });
}

function addFiles(newFiles) {
  const pdfs = Array.from(newFiles).filter((f) => f.name.toLowerCase().endsWith(".pdf"));
  const names = new Set(files.map((f) => f.name));
  files = [...files, ...pdfs.filter((f) => !names.has(f.name))];
  renderFiles();
}

function renderRequisitos(items, cls) {
  if (!items.length) return "";
  const tags = items.map((r) => `<span class="tag ${cls}">${r}</span>`).join("");
  return `<div class="requisitos">${tags}</div>`;
}

function renderRequisitoGrid(items, iconFn) {
  if (!items?.length) return "";
  const rows = items
    .map(
      (r) => `
        <div class="requisito-item">
          <span>${iconFn(r)}</span>
          <div>
            ${r.requisito}
            ${r.evidencia_literal ? `<span class="evidencia">"${r.evidencia_literal}"</span>` : ""}
          </div>
        </div>`,
    )
    .join("");
  return `<div class="requisito-grid">${rows}</div>`;
}

function renderCandidato(c, rank) {
  const cls = statusClass(c.status);
  const scoreBadge = !c.eliminado ? `<span class="score-badge ${cls}">${c.score}</span>` : "";
  const lacunas = c.lacunas?.length
    ? `<div class="lacunas"><strong>Lacunas:</strong><ul>${c.lacunas.map((l) => `<li>${l}</li>`).join("")}</ul></div>`
    : "";
  const obrig = c.analise_obrigatorios?.length
    ? `<div class="section-title">Requisitos obrigatórios</div>${renderRequisitoGrid(c.analise_obrigatorios, (r) => (r.atende ? "✅" : "❌"))}`
    : "";
  const desej = c.analise_desejaveis?.length
    ? `<div class="section-title">Requisitos desejáveis</div>${renderRequisitoGrid(c.analise_desejaveis, (r) => (r.atende ? "✅" : "➖"))}`
    : "";

  return `
    <div class="candidato-card" data-rank="${rank}">
      <div class="candidato-header">
        <span class="candidato-rank">${rank}º</span>
        <div class="candidato-info">
          <h3>${c.nome}</h3>
          <div class="candidato-meta">${metaCandidato(c)}</div>
        </div>
        ${scoreBadge}
        <span class="status-label ${cls}">${c.status}</span>
        <span class="chevron">▼</span>
      </div>
      <div class="candidato-details">
        ${lacunas}
        ${obrig}
        ${desej}
      </div>
    </div>`;
}

function renderResults(data) {
  const el = $("#results");
  const reqObrig = data.requisitos_obrigatorios.length
    ? `<div class="section-title">Requisitos obrigatórios detectados</div>${renderRequisitos(data.requisitos_obrigatorios, "obrigatorio")}`
    : "";
  const reqDesej = data.requisitos_desejaveis.length
    ? `<div class="section-title">Requisitos desejáveis detectados</div>${renderRequisitos(data.requisitos_desejaveis, "desejavel")}`
    : "";

  el.innerHTML = `
    <div class="results-header">
      <h2>${data.titulo_vaga}</h2>
      <div class="stats">
        <span class="stat"><strong>${data.total_cvs}</strong> CVs</span>
        <span class="stat"><strong>${data.aprovados}</strong> aprovados</span>
        <span class="stat"><strong>${data.eliminados}</strong> eliminados</span>
      </div>
    </div>
    ${reqObrig}
    ${reqDesej}
    <div class="section-title">Ranking de candidatos</div>
    <div class="candidatos-list">
      ${data.candidatos.map((c, i) => renderCandidato(c, i + 1)).join("")}
    </div>`;
  el.classList.remove("hidden");

  el.querySelectorAll(".candidato-header").forEach((header) => {
    header.addEventListener("click", () => {
      header.parentElement.classList.toggle("expanded");
    });
  });
}

async function submit() {
  const texto = $("#texto-vaga").value.trim();
  hideError();

  if (texto.length < 20) {
    showError("Cole a descrição completa da vaga (mínimo 20 caracteres).");
    return;
  }
  if (!files.length) {
    showError("Adicione ao menos um currículo em PDF.");
    return;
  }

  const form = new FormData();
  form.append("texto_vaga", texto);
  files.forEach((f) => form.append("curriculos", f));

  $("#btn-submit").disabled = true;
  $("#loading").classList.remove("hidden");
  $("#results").classList.add("hidden");

  try {
    const res = await fetch(`${API_BASE}/api/analyze`, { method: "POST", body: form });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = Array.isArray(data.detail)
        ? data.detail.map((d) => d.msg || d).join(", ")
        : data.detail || "Erro ao processar triagem";
      throw new Error(detail);
    }
    renderResults(data);
  } catch (e) {
    showError(e.message || "Erro desconhecido");
  } finally {
    $("#loading").classList.add("hidden");
    $("#btn-submit").disabled = false;
  }
}

function init() {
  const dropzone = $("#dropzone");
  const fileInput = $("#file-input");

  dropzone.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", (e) => addFiles(e.target.files));

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });
  dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
    addFiles(e.dataTransfer.files);
  });

  $("#btn-submit").addEventListener("click", submit);
  checkHealth();
}

init();

