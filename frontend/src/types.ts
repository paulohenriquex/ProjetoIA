export interface VerificacaoRequisito {
  requisito: string;
  atende: boolean;
  evidencia_literal: string;
}

export type StatusCandidato =
  | "EXCELENTE"
  | "POTENCIAL"
  | "OK"
  | "OPORTUNIDADE"
  | "PARCIAL"
  | "ELIMINADO"
  | "ERRO";

export interface CandidatoResultado {
  nome: string;
  score: number;
  status: StatusCandidato | string;
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

export interface VagaTalentoInput {
  vaga_id: string;
  texto_vaga: string;
  candidato_cadastrado: boolean;
}

export type StatusVagaTalento =
  | "APROVADA"
  | "REPROVADA"
  | "NAO_CADASTRADO"
  | "ERRO_VAGA"
  | "ERRO_ANALISE";

export interface ResultadoVagaTalento {
  vaga_id: string;
  titulo_vaga: string;
  candidato_cadastrado: boolean;
  analisado: boolean;
  score: number;
  status: StatusVagaTalento | string;
  lacunas: string[];
  pontos_melhorar: string[];
  analise_obrigatorios?: VerificacaoRequisito[];
  analise_desejaveis?: VerificacaoRequisito[];
}

export interface AnaliseBancoTalentosResponse {
  candidato: string;
  total_vagas_recebidas: number;
  vagas_analisadas: number;
  vagas_nao_cadastradas: number;
  vagas_aprovadas: number;
  vagas_reprovadas: number;
  resultados: ResultadoVagaTalento[];
}
