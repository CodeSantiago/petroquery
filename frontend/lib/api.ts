const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
    cache: "no-store" 
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

export async function askQuestion(question: string, chatId?: number): Promise<AnswerResponse> {
  const token = getAuthToken();
  const body: { question: string; chat_id?: number } = { question };
  if (chatId) body.chat_id = chatId;
  
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

export async function ingestPdf(file: File, title: string): Promise<{
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

export async function fetchChatMessages(chatId: number): Promise<ChatMessage[]> {
  const token = getAuthToken();
  const res = await fetch(`${API_BASE}/api/v1/chats/${chatId}/messages`, {
    cache: "no-store",
    headers: token ? { "Authorization": `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error("Failed to fetch chat messages");
  return res.json();
}

export async function deleteChat(chatId: number): Promise<{ message: string }> {
  const token = getAuthToken();
  const res = await fetch(`${API_BASE}/api/v1/chats/${chatId}`, {
    method: "DELETE",
    headers: token ? { "Authorization": `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error("Failed to delete chat");
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