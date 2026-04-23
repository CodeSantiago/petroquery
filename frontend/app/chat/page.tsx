"use client";

import { useState, useRef, useEffect, useCallback, memo, useMemo } from "react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { 
  askQuestion, 
  fetchIngestedDocuments, 
  fetchChatMessages,
  deleteChat,
  clearChatMessages,
  deleteChatDocuments,
  getCurrentUser,
  getAuthToken,
  logout as apiLogout,
  type AnswerResponse, 
  type IngestedDocument,
  type User,
  type ChatMessage,
} from "@/lib/api";
import {
  Send,
  FileText,
  Plus,
  Command,
  X,
  Sparkles,
  Bot,
  User as UserIcon,
  Loader2,
  ChevronRight,
  LogOut,
  MessageCircle,
  Trash2,
  FileX,
  RotateCcw,
  MoreVertical,
} from "lucide-react";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: { id: number; title: string; similarity: number }[];
}

interface SelectedFile {
  file: File;
  name: string;
  size: number;
}

const MessageBubble = memo(function MessageBubble({ message }: { message: Message }) {
  return (
    <div className={cn("flex gap-4 max-w-4xl", message.role === "user" ? "ml-auto flex-row-reverse" : "")}>
      <div className={cn("w-10 h-10 rounded-2xl flex items-center justify-center flex-shrink-0", message.role === "user" ? "bg-gradient-to-br from-orange-400 to-amber-400" : "bg-gradient-to-br from-amber-300 to-yellow-300")}>
        {message.role === "user" ? <UserIcon className="w-5 h-5 text-white" /> : <Bot className="w-5 h-5 text-white" />}
      </div>
      <div className={cn("flex-1 space-y-2", message.role === "user" ? "text-right" : "")}>
        <div className={cn("inline-block px-5 py-4 rounded-3xl max-w-[80%]", message.role === "user" ? "bg-gradient-to-r from-orange-500 to-amber-500 text-white" : "glass-card")}>
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
        </div>
        {message.role === "assistant" && message.sources && message.sources.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-2">
            {message.sources.map((source) => (
              <span key={source.id} className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full bg-orange-100 text-orange-600 text-xs font-medium">
                <FileText className="w-3 h-3" />
                {source.title.slice(0, 15)}
                <span className="text-amber-500">{(source.similarity * 100).toFixed(0)}%</span>
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
});

const LoadingIndicator = memo(function LoadingIndicator() {
  return (
    <div className="flex gap-4 max-w-4xl">
      <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-amber-300 to-yellow-300 flex items-center justify-center">
        <Bot className="w-5 h-5 text-white" />
      </div>
      <div className="flex items-center gap-2 px-5 py-4 rounded-3xl glass-card">
        <div className="flex gap-1">
          <span className="w-2.5 h-2.5 rounded-full bg-orange-400 animate-bounce" style={{ animationDelay: '0ms' }} />
          <span className="w-2.5 h-2.5 rounded-full bg-orange-400 animate-bounce" style={{ animationDelay: '150ms' }} />
          <span className="w-2.5 h-2.5 rounded-full bg-amber-400 animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
        <span className="text-sm text-slate-500">Pensando...</span>
      </div>
    </div>
  );
});

const Sidebar = memo(function Sidebar({ documents, onNewIngest, onDocumentClick, activeDocument, currentUser, onLogout, isRefreshing, onRefresh, onDeleteChat, onClearMessages, onDeleteDocs }: {
  documents: IngestedDocument[];
  onNewIngest: () => void;
  onDocumentClick?: (doc: IngestedDocument) => void;
  activeDocument: IngestedDocument | null;
  currentUser: User | null;
  onLogout?: () => void;
  isRefreshing?: boolean;
  onRefresh?: () => void;
  onDeleteChat?: (chatId: number) => void;
  onClearMessages?: (chatId: number) => void;
  onDeleteDocs?: (chatId: number) => void;
}) {
  return (
    <aside className="w-80 border-r border-orange-100/50 bg-white/40 bg-white/40 flex flex-col">
      <div className="p-5 border-b border-orange-100/50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-orange-400 to-amber-400 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <span className="font-bold text-lg text-slate-700">Brain-API</span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        <button onClick={onNewIngest} className="w-full flex items-center gap-3 px-4 py-3.5 rounded-2xl bg-gradient-to-r from-orange-500 to-amber-500 text-white font-medium hover:shadow-lg hover:scale-[1.02] transition-all duration-200">
          <Plus className="w-5 h-5" />
          Nuevo Documento
        </button>

        <div className="mt-6 px-3 text-xs font-semibold text-orange-400 uppercase tracking-wider flex items-center gap-2">
          Mis Documentos
          {isRefreshing && <Loader2 className="w-3 h-3 animate-spin text-orange-400" />}
        </div>

        {documents.length === 0 ? (
          <div className="px-3 py-8 text-center">
            <MessageCircle className="w-10 h-10 text-orange-200 mx-auto mb-2" />
            <p className="text-slate-400 text-sm">Sin documentos aún</p>
            <p className="text-slate-300 text-xs mt-1">Sube tu primer archivo</p>
          </div>
        ) : (
          documents.map((doc) => (
            <div key={doc.id} className="relative group">
              <button onClick={() => onDocumentClick?.(doc)} className={cn("w-full text-left px-4 py-3 rounded-2xl transition-all duration-200", activeDocument?.id === doc.id ? "bg-orange-100 border border-orange-200" : "hover:bg-orange-50")}>
                <div className="flex items-center justify-between">
                  <span className={cn("truncate font-medium", activeDocument?.id === doc.id ? "text-orange-600" : "text-slate-600")}>{doc.title}</span>
                  <ChevronRight className={cn("w-4 h-4 transition-opacity", activeDocument?.id === doc.id ? "text-orange-500" : "text-slate-300 opacity-0 group-hover:opacity-100")} />
                </div>
                <div className="text-xs text-slate-400 mt-0.5">{doc.created_at ? new Date(doc.created_at).toLocaleDateString() : ""}</div>
              </button>
              {activeDocument?.id === doc.id && (
                <div className="flex gap-1 mt-1 px-1">
                  <button onClick={(e) => { e.stopPropagation(); onDeleteDocs?.(doc.chat_id); }} className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 text-xs text-red-500 hover:bg-red-50 rounded-lg" title="Borrar documentos">
                    <FileX className="w-3 h-3" />Docs
                  </button>
                  <button onClick={(e) => { e.stopPropagation(); onClearMessages?.(doc.chat_id); }} className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 text-xs text-orange-500 hover:bg-orange-50 rounded-lg" title="Limpiar mensajes">
                    <RotateCcw className="w-3 h-3" />Msgs
                  </button>
                  <button onClick={(e) => { e.stopPropagation(); onDeleteChat?.(doc.chat_id); }} className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 text-xs text-red-600 hover:bg-red-100 rounded-lg" title="Borrar chat">
                    <Trash2 className="w-3 h-3" />Chat
                  </button>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      <div className="p-4 border-t border-orange-100/50 space-y-2">
        {currentUser && (
          <div className="flex items-center gap-3 px-3 py-3 rounded-2xl bg-orange-50">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-orange-400 to-amber-400 flex items-center justify-center">
              <UserIcon className="w-5 h-5 text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-700 truncate">{currentUser.username}</p>
              <p className="text-xs text-slate-400 truncate">{currentUser.email}</p>
            </div>
          </div>
        )}
        <button onClick={onLogout} className="w-full flex items-center gap-3 px-4 py-3 rounded-2xl text-slate-500 hover:text-red-500 hover:bg-red-50 transition-colors text-sm">
          <LogOut className="w-4 h-4" />
          Cerrar Sesión
        </button>
      </div>
    </aside>
  );
});

function ChatInput({ input, onChange, onSubmit, isLoading }: { input: string; onChange: (v: string) => void; onSubmit: (e: React.FormEvent) => void; isLoading: boolean }) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); onSubmit(e as unknown as React.FormEvent); }
  }, [onSubmit]);

  return (
    <div className="p-4 border-t border-orange-100/50 bg-white/60 bg-white/40">
      <form onSubmit={onSubmit} className="flex items-end gap-3 max-w-4xl mx-auto">
        <div className="flex-1 relative">
          <div className="absolute left-4 top-1/2 -translate-y-1/2 flex items-center gap-1.5 text-orange-400 text-xs pointer-events-none">
            <Command className="w-3 h-3" /><span>K</span>
          </div>
          <textarea ref={textareaRef} value={input} onChange={(e) => onChange(e.target.value)} onKeyDown={handleKeyDown} placeholder="Pregunta algo..." className="w-full pl-12 pr-4 py-4 bg-white/80 border border-orange-100 rounded-2xl text-slate-700 placeholder:text-slate-400 focus:outline-none focus:border-orange-300 focus:ring-2 focus:ring-orange-100 resize-none" rows={1} />
        </div>
        <button type="submit" disabled={!input.trim() || isLoading} className="p-4 rounded-2xl bg-gradient-to-r from-orange-500 to-amber-500 hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200">
          {isLoading ? <Loader2 className="w-5 h-5 text-white animate-spin" /> : <Send className="w-5 h-5 text-white" />}
        </button>
      </form>
    </div>
  );
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

const FileCard = memo(function FileCard({ file, onRemove }: { file: SelectedFile; onRemove: () => void }) {
  return (
    <div className="flex items-center justify-between p-4 glass-card rounded-2xl">
      <div className="flex items-center gap-3">
        <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-amber-200 to-orange-300 flex items-center justify-center">
          <FileText className="w-6 h-6 text-orange-600" />
        </div>
        <div>
          <p className="text-sm font-medium text-slate-700 truncate max-w-[200px]">{file.name}</p>
          <p className="text-xs text-slate-400">{formatFileSize(file.size)}</p>
        </div>
      </div>
      <button onClick={onRemove} className="p-2 rounded-full hover:bg-orange-100 transition-colors">
        <X className="w-4 h-4 text-slate-400" />
      </button>
    </div>
  );
});

const UploadModal = memo(function UploadModal({ isOpen, onClose, onUploadSuccess }: { isOpen: boolean; onClose: () => void; onUploadSuccess?: () => void }) {
  const [uploadTitle, setUploadTitle] = useState("");
  const [uploadContent, setUploadContent] = useState("");
  const [selectedFile, setSelectedFile] = useState<SelectedFile | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [showConfetti, setShowConfetti] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const resetForm = useCallback(() => { setUploadTitle(""); setUploadContent(""); setSelectedFile(null); if (fileInputRef.current) fileInputRef.current.value = ""; }, []);
  const handleClose = useCallback(() => { resetForm(); onClose(); }, [onClose, resetForm]);

  const handleFileSelect = useCallback((file: File) => { setSelectedFile({ file, name: file.name, size: file.size }); setUploadTitle(file.name.replace(/\.[^/.]+$/, "")); }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => { e.preventDefault(); setIsDragging(true); }, []);
  const handleDragLeave = useCallback((e: React.DragEvent) => { e.preventDefault(); setIsDragging(false); }, []);
  const handleDrop = useCallback((e: React.DragEvent) => { e.preventDefault(); setIsDragging(false); const file = e.dataTransfer.files[0]; if (file) handleFileSelect(file); }, [handleFileSelect]);
  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => { const file = e.target.files?.[0]; if (file) handleFileSelect(file); }, [handleFileSelect]);
  const handleRemoveFile = useCallback(() => { setSelectedFile(null); if (fileInputRef.current) fileInputRef.current.value = ""; }, []);

  const handleUpload = useCallback(async () => {
    if (!uploadTitle.trim()) return;
    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append("title", uploadTitle.trim());
      if (selectedFile) {
        formData.append("file", selectedFile.file);
        const res = await fetch("http://localhost:8000/api/v1/ingest/pdf", { method: "POST", headers: { "Authorization": `Bearer ${localStorage.getItem("auth_token")}` }, body: formData });
        if (!res.ok) {
          const errText = await res.text();
          console.error("Upload failed:", res.status, errText);
          throw new Error(errText || "Failed");
        }
      } else if (uploadContent.trim()) {
        const res = await fetch("http://localhost:8000/ingest", { method: "POST", headers: { "Content-Type": "application/json", "Authorization": `Bearer ${localStorage.getItem("auth_token")}` }, body: JSON.stringify({ title: uploadTitle, content: uploadContent, metadata: {} }) });
        if (!res.ok) throw new Error("Failed");
      } else return;
      setShowConfetti(true);
      setTimeout(() => setShowConfetti(false), 2000);
      resetForm();
      onUploadSuccess?.();
      handleClose();
    } catch (error) { console.error("Upload failed:", error); } finally { setIsUploading(false); }
  }, [uploadTitle, uploadContent, selectedFile, resetForm, handleClose, onUploadSuccess]);

  const canUpload = uploadTitle.trim() && (selectedFile || uploadContent.trim());

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-white/80 bg-white/80" onClick={handleClose} />
      {showConfetti && (
        <div className="fixed inset-0 pointer-events-none z-[60]">
          {[...Array(20)].map((_, i) => (
            <div key={i} className="confetti-piece" style={{ left: `${Math.random() * 100}%`, top: `${Math.random() * 50}%`, background: ['#c4b5fd', '#86efac', '#f9a8d4', '#67e8f9', '#fcd34d'][i % 5], animationDelay: `${i * 0.1}s` }} />
          ))}
        </div>
      )}
      <div className="relative w-full max-w-lg mx-4 p-6 glass-card rounded-3xl">
        <button onClick={handleClose} className="absolute top-4 right-4 p-2 rounded-full hover:bg-orange-100 transition-colors">
          <X className="w-5 h-5 text-slate-400" />
        </button>

        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-orange-400 to-amber-400 flex items-center justify-center">
            <FileText className="w-5 h-5 text-white" />
          </div>
          <h3 className="text-lg font-bold text-slate-700">Subir Documento</h3>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1.5">Título</label>
            <input type="text" value={uploadTitle} onChange={(e) => setUploadTitle(e.target.value)} placeholder="Nombre del documento..." className="w-full px-4 py-3 bg-white/80 border border-orange-100 rounded-2xl text-slate-700 placeholder:text-slate-400 focus:outline-none focus:border-orange-300" />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1.5">Contenido</label>
            {selectedFile ? <FileCard file={selectedFile} onRemove={handleRemoveFile} /> : <textarea value={uploadContent} onChange={(e) => setUploadContent(e.target.value)} placeholder="Pega el contenido aquí..." rows={5} className="w-full px-4 py-3 bg-white/80 border border-orange-100 rounded-2xl text-slate-700 placeholder:text-slate-400 focus:outline-none focus:border-orange-300 resize-none" />}
          </div>

          <input ref={fileInputRef} type="file" accept=".txt,.md,.pdf" onChange={handleFileInputChange} className="hidden" />

          <div onClick={() => fileInputRef.current?.click()} onDragOver={handleDragOver} onDragLeave={handleDragLeave} onDrop={handleDrop} className={cn("border-2 border-dashed rounded-2xl p-6 text-center transition-all duration-200 cursor-pointer", isDragging ? "border-orange-400 bg-orange-50" : "border-orange-200 hover:border-orange-300")}>
            <FileText className="w-8 h-8 text-orange-300 mx-auto mb-2" />
            <p className="text-sm text-slate-500">{selectedFile ? "Click para cambiar" : "Arrastra un archivo o haz click para buscar"}</p>
          </div>

          <button onClick={handleUpload} disabled={!canUpload || isUploading} className="w-full py-3.5 bg-gradient-to-r from-orange-500 to-amber-500 hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed rounded-2xl text-white font-semibold transition-all duration-200 flex items-center justify-center gap-2">
            {isUploading ? <><Loader2 className="w-5 h-5 animate-spin" /> Procesando...</> : "Subir Documento"}
          </button>
        </div>
      </div>
    </div>
  );
});

const WelcomeScreen = memo(function WelcomeScreen() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center">
      <div className="w-24 h-24 rounded-3xl bg-gradient-to-br from-orange-400 to-amber-400 flex items-center justify-center mb-6 shadow-xl">
        <Bot className="w-12 h-12 text-white" />
      </div>
      <h2 className="text-2xl font-bold text-slate-700 mb-2">Bienvenido a Brain-API</h2>
      <p className="text-slate-500 max-w-md">Sube tus documentos y haz preguntas. La IA te responderá usando RAG con fuentes verificadas.</p>
    </div>
  );
});

export default function ChatPage() {
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [documents, setDocuments] = useState<IngestedDocument[]>([]);
  const [activeDocument, setActiveDocument] = useState<IngestedDocument | null>(null);
  const [showUpload, setShowUpload] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [isRefreshingDocuments, setIsRefreshingDocuments] = useState(false);
  const [activeChatId, setActiveChatId] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const loadDocuments = useCallback(async () => {
    const docs = await fetchIngestedDocuments();
    setDocuments(docs);
    const urlParams = new URLSearchParams(window.location.search);
    const docIdFromUrl = urlParams.get("doc");
    if (docIdFromUrl) {
      const activeDoc = docs.find(d => d.id.toString() === docIdFromUrl);
      if (activeDoc) setActiveDocument(activeDoc);
    }
  }, []);

  const loadChatMessages = useCallback(async (chatId: number) => {
    try {
      const chatMsgs = await fetchChatMessages(chatId);
      const msgs: Message[] = chatMsgs.map(m => ({
        id: m.id.toString(),
        role: m.role,
        content: m.content,
      }));
      setMessages(msgs);
    } catch (e) {
      console.error("Failed to load chat messages:", e);
    }
  }, []);

  const handleRefreshDocuments = useCallback(async () => {
    setIsRefreshingDocuments(true);
    await loadDocuments();
    setIsRefreshingDocuments(false);
  }, [loadDocuments]);

  const handleDeleteChat = useCallback(async (chatId: number) => {
    if (!confirm("¿Eliminar este chat completo?")) return;
    try {
      await deleteChat(chatId);
      setMessages([]);
      setActiveChatId(null);
      await loadDocuments();
    } catch (e) {
      console.error("Failed to delete chat:", e);
    }
  }, [loadDocuments]);

  const handleClearMessages = useCallback(async (chatId: number) => {
    if (!confirm("¿Limpiar todos los mensajes de este chat?")) return;
    try {
      await clearChatMessages(chatId);
      setMessages([]);
    } catch (e) {
      console.error("Failed to clear messages:", e);
    }
  }, []);

  const handleDeleteDocs = useCallback(async (chatId: number) => {
    if (!confirm("¿Eliminar los documentos de este chat?")) return;
    try {
      await deleteChatDocuments(chatId);
      await loadDocuments();
    } catch (e) {
      console.error("Failed to delete documents:", e);
    }
  }, [loadDocuments]);

  const checkAuth = useCallback(async () => {
    const token = getAuthToken();
    if (!token) { router.push("/auth"); return; }
    try {
      const user = await getCurrentUser();
      setCurrentUser(user);
      await loadDocuments();
      
      // Cargar chat desde URL si existe
      const urlParams = new URLSearchParams(window.location.search);
      const chatIdFromUrl = urlParams.get("chat");
      if (chatIdFromUrl) {
        const chatId = parseInt(chatIdFromUrl, 10);
        if (!isNaN(chatId)) {
          setActiveChatId(chatId);
          await loadChatMessages(chatId);
        }
      }
    } catch (e) { apiLogout(); router.push("/auth"); }
  }, [router, loadDocuments, loadChatMessages]);

  useEffect(() => { checkAuth(); }, [checkAuth]);

  const handleDocumentClick = useCallback(async (doc: IngestedDocument) => {
    setActiveDocument(doc);
    if (doc.chat_id) {
      setActiveChatId(doc.chat_id);
      await loadChatMessages(doc.chat_id);
      const url = new URL(window.location.href);
      url.searchParams.set("chat", doc.chat_id.toString());
      window.history.replaceState({}, "", url.toString());
    }
  }, [loadChatMessages]);

  const handleLogout = useCallback(() => { apiLogout(); router.push("/auth"); }, [router]);

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    const userMessage: Message = { id: Date.now().toString(), role: "user", content: input.trim() };
    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);
    try {
      const response = await askQuestion(userMessage.content, activeChatId ?? undefined);
      setActiveChatId(response.chat_id);
      
      // Actualizar URL con chat_id
      const url = new URL(window.location.href);
      url.searchParams.set("chat", response.chat_id.toString());
      window.history.replaceState({}, "", url.toString());
      
      const assistantMsg: Message = { id: (Date.now() + 1).toString(), role: "assistant", content: response.answer, sources: response.sources };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (error) {
      setMessages(prev => [...prev, { id: (Date.now() + 1).toString(), role: "assistant", content: "Lo siento, ocurrió un error al procesar tu pregunta." }]);
    } finally { setIsLoading(false); }
  }, [input, isLoading, activeChatId]);

  const messagesMemo = useMemo(() => messages.map(msg => <MessageBubble key={msg.id} message={msg} />), [messages]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 via-white to-amber-50 text-slate-700 font-sans">
      
      <div className="fixed inset-0 mesh-gradient opacity-30 pointer-events-none" />
      <div className="relative flex h-screen">
        <Sidebar documents={documents} onNewIngest={() => setShowUpload(true)} onDocumentClick={handleDocumentClick} activeDocument={activeDocument} currentUser={currentUser} onLogout={handleLogout} isRefreshing={isRefreshingDocuments} onRefresh={handleRefreshDocuments} onDeleteChat={handleDeleteChat} onClearMessages={handleClearMessages} onDeleteDocs={handleDeleteDocs} />
        <main className="flex-1 flex flex-col relative">
          <div className="p-5 border-b border-orange-100/50 bg-white/40 bg-white/40">
            <h1 className="text-lg font-bold text-slate-700 truncate">{activeDocument ? activeDocument.title : "Pregunta a tu documentación"}</h1>
            {activeDocument && <p className="text-xs text-slate-400 mt-0.5">Selecciona un documento del sidebar</p>}
          </div>
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {messages.length === 0 && <WelcomeScreen />}
            {messagesMemo}
            {isLoading && <LoadingIndicator />}
            <div ref={messagesEndRef} />
          </div>
          <ChatInput input={input} onChange={setInput} onSubmit={handleSubmit} isLoading={isLoading} />
        </main>
      </div>
      <UploadModal isOpen={showUpload} onClose={() => { setShowUpload(false); setRefreshKey(k => k + 1); }} onUploadSuccess={handleRefreshDocuments} />
    </div>
  );
}