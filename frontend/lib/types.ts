export interface OGTMetadata {
  cuenca?: string;
  tipo_equipo?: string;
  normativa_aplicable?: string;
  tipo_documento?: string;
  pozo_referencia?: string;
}

export interface SourceReference {
  documento: string;
  pagina: number;
  seccion?: string;
  tabla_referencia?: string;
  figura_referencia?: string;
  score_confianza: number;
  contenido_citado: string;
  cuenca?: string;
  normativa_aplicable?: string;
}

export interface OGTechnicalAnswer {
  respuesta_tecnica: string;
  advertencia_seguridad?: string;
  fuentes: SourceReference[];
  score_global_confianza: number;
  necesita_revision_humana: boolean;
  tipo_consulta: string;
  chat_id?: number;
}

export interface FilterParams {
  cuenca?: string;
  tipo_documento?: string;
  tipo_equipo?: string;
  normativa_aplicable?: string;
}

export interface Chat {
  id: number;
  title: string;
  created_at: string;
  updated_at?: string;
}

export interface Message {
  id: number | string;
  chat_id?: number;
  role: "user" | "assistant";
  content: string;
  created_at?: string;
  answer_data?: OGTechnicalAnswer;
  structured_response?: OGTechnicalAnswer;
}
