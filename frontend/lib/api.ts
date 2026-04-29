const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

import { OGTechnicalAnswer, FilterParams, Chat, Message } from "@/lib/types";

export interface User {
  id: number;
  email: string;
  username: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
}

export interface Document {
  id: number;
  title: string;
  content: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface Source {
  id: number;
  title: string;
  similarity: number;
}

export interface AnswerResponse {
  answer: string;
  sources: Source[];
  chat_id: number;
}

export interface ChatMessage {
  id: number;
  chat_id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface IngestedDocument {
  id: number;
  title: string;
  chat_id: number;
  created_at: string | null;
}

export interface Token {
  access_token: string;
  token_type: string;
}

let authToken: string | null = null;

export function getAuthToken(): string | null {
  if (typeof window !== "undefined") {
    authToken = authToken || localStorage.getItem("auth_token");
  }
  return authToken;
}

export function setAuthToken(token: string | null): void {
  authToken = token;
  if (typeof window !== "undefined") {
    if (token) {
      localStorage.setItem("auth_token", token);
    } else {
      localStorage.removeItem("auth_token");
    }
  }
}

export async function login(username: string, password: string): Promise<Token> {
  const formData = new FormData();
  formData.append("username", username);
  formData.append("password", password);

  const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const error = await res.text();
    throw new Error(`Login failed: ${error}`);
  }

  const token: Token = await res.json();
  setAuthToken(token.access_token);
  return token;
}

export async function register(data: {
  email: string;
  username: string;
  password: string;
  full_name?: string;
}): Promise<User> {
  const res = await fetch(`${API_BASE}/api/v1/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const error = await res.text();
    throw new Error(`Registration failed: ${error}`);
  }

  return res.json();
}

export async function getCurrentUser(): Promise<User> {
  const token = getAuthToken();
  if (!token) throw new Error("Not authenticated");

  const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
    headers: { "Authorization": `Bearer ${token}` },
  });

  if (!res.ok) {
    setAuthToken(null);
    throw new Error("Failed to get user");
  }

  return res.json();
}

export function logout(): void {
  setAuthToken(null);
}

export async function fetchDocuments(): Promise<Document[]> {
  const res = await fetch(`${API_BASE}/documents`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch documents");
  return res.json();
}

export async function getDocument(id: number): Promise<Document> {
  const res = await fetch(`${API_BASE}/documents/${id}`);
  if (!res.ok) throw new Error("Failed to fetch document");
  return res.json();
}

export async function createDocument(data: {
  title: string;
  content: string;
  metadata: Record<string, unknown>;
}): Promise<Document> {
  const res = await fetch(`${API_BASE}/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to create document");
  return res.json();
}

export async function askQuestion(
  question: string,
  chatId?: number,
  filters?: FilterParams,
  projectId?: number
): Promise<OGTechnicalAnswer> {
  const token = getAuthToken();
  const body: {
    question: string;
    chat_id?: number;
    project_id?: number;
    filters?: FilterParams;
  } = { question };
  if (chatId) body.chat_id = chatId;
  if (projectId) body.project_id = projectId;
  if (filters && Object.keys(filters).length > 0) body.filters = filters;

  const res = await fetch(`${API_BASE}/api/v1/ask`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { "Authorization": `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const error = await res.text();
    throw new Error(`Failed to ask question: ${error}`);
  }
  return res.json();
}

export async function uploadPDF(
  file: File,
  projectId: number,
  metadata?: {
    cuenca?: string;
    tipo_equipo?: string;
    normativa_aplicable?: string;
    tipo_documento?: string;
    pozo_referencia?: string;
  }
): Promise<{ status: string; document_id: number | string; chat_id?: number }> {
  const token = getAuthToken();
  const formData = new FormData();
  formData.append("file", file);
  formData.append("project_id", String(projectId));
  if (metadata) {
    formData.append("og_metadata", JSON.stringify(metadata));
  }

  const res = await fetch(`${API_BASE}/api/v1/ingest/pdf`, {
    method: "POST",
    headers: token ? { "Authorization": `Bearer ${token}` } : {},
    body: formData,
  });
  if (!res.ok) {
    const error = await res.text();
    throw new Error(`Failed to ingest PDF: ${error}`);
  }
  return res.json();
}

export async function getUploadStatus(
  documentId: number | string
): Promise<{ status: string; progress: number; title?: string; insights?: { summary?: string; sections?: string[]; questions?: string[] } | null }> {
  const token = getAuthToken();
  const res = await fetch(`${API_BASE}/api/v1/ingest/status/${documentId}`, {
    headers: token ? { "Authorization": `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error("Failed to get upload status");
  return res.json();
}

export async function listChats(): Promise<Chat[]> {
  const token = getAuthToken();
  const res = await fetch(`${API_BASE}/api/v1/chats`, {
    cache: "no-store",
    headers: token ? { "Authorization": `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error("Failed to list chats");
  return res.json();
}

export async function getChatMessages(chatId: number): Promise<Message[]> {
  const token = getAuthToken();
  const res = await fetch(`${API_BASE}/api/v1/chats/${chatId}/messages`, {
    cache: "no-store",
    headers: token ? { "Authorization": `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error("Failed to fetch chat messages");
  return res.json();
}

export async function deleteChat(chatId: number): Promise<void> {
  const token = getAuthToken();
  const res = await fetch(`${API_BASE}/api/v1/chats/${chatId}`, {
    method: "DELETE",
    headers: token ? { "Authorization": `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error("Failed to delete chat");
}

export async function renameChat(chatId: number, title: string): Promise<void> {
  const token = getAuthToken();
  const res = await fetch(`${API_BASE}/api/v1/chats/${chatId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { "Authorization": `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error("Failed to rename chat");
}

export async function ingestPdf(
  file: File,
  title: string
): Promise<{
  message: string;
  filename: string;
  chunks_created: number;
  total_text_length: number;
}> {
  const token = getAuthToken();
  const formData = new FormData();
  formData.append("file", file);
  formData.append("title", title);

  const res = await fetch(`${API_BASE}/api/v1/ingest/pdf`, {
    method: "POST",
    headers: token ? { "Authorization": `Bearer ${token}` } : {},
    body: formData,
  });
  if (!res.ok) {
    const error = await res.text();
    throw new Error(`Failed to ingest PDF: ${error}`);
  }
  return res.json();
}

export async function fetchIngestedDocuments(): Promise<IngestedDocument[]> {
  const token = getAuthToken();
  const res = await fetch(`${API_BASE}/api/v1/ingest/documents`, {
    cache: "no-store",
    headers: token ? { "Authorization": `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error("Failed to fetch ingested documents");
  return res.json();
}

export async function fetchChatMessagesLegacy(chatId: number): Promise<ChatMessage[]> {
  const token = getAuthToken();
  const res = await fetch(`${API_BASE}/api/v1/chats/${chatId}/messages`, {
    cache: "no-store",
    headers: token ? { "Authorization": `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error("Failed to fetch chat messages");
  return res.json();
}

export async function clearChatMessages(chatId: number): Promise<{ message: string }> {
  const token = getAuthToken();
  const res = await fetch(`${API_BASE}/api/v1/chats/${chatId}/messages`, {
    method: "DELETE",
    headers: token ? { "Authorization": `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error("Failed to clear messages");
  return res.json();
}

export async function deleteChatDocuments(chatId: number): Promise<{ message: string }> {
  const token = getAuthToken();
  const res = await fetch(`${API_BASE}/api/v1/chats/${chatId}/documents`, {
    method: "DELETE",
    headers: token ? { "Authorization": `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error("Failed to delete documents");
  return res.json();
}

export async function inviteUser(data: {
  email: string;
  username: string;
  role: string;
  project_id: number;
}): Promise<User> {
  const token = getAuthToken();
  if (!token) throw new Error("Not authenticated");

  const res = await fetch(`${API_BASE}/api/v1/admin/invite`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const error = await res.text();
    throw new Error(`Invite failed: ${error}`);
  }

  return res.json();
}
