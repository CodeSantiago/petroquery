"use client";

import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { cn } from "@/lib/utils";
import {
  askQuestion,
  uploadPDF,
  getUploadStatus,
  listChats,
  getChatMessages,
  deleteChat,
  renameChat,
  getCurrentUser,
  getAuthToken,
  logout as apiLogout,
  type User,
} from "@/lib/api";
import { FilterParams, Message, OGTechnicalAnswer } from "@/lib/types";
import ChatMessage from "@/app/components/ChatMessage";
import AdvancedFilters from "@/app/components/AdvancedFilters";
import UploadProgress from "@/app/components/UploadProgress";
import {
  Send,
  Plus,
  Loader2,
  LogOut,
  MessageSquare,
  Trash2,
  Pencil,
  X,
  Check,
  Droplets,
  Upload,
  ChevronLeft,
  Menu,
  User as UserIcon,
  BookOpen,
  FolderOpen,
  ArrowLeft,
} from "lucide-react";
import DocumentInsights from "@/app/components/DocumentInsights";
import DocumentOutline from "@/app/components/DocumentOutline";

interface UploadTask {
  id: number | string;
  fileName: string;
  progress: number;
  status: string;
  chatId?: number;
  insights?: {
    summary?: string;
    sections?: string[];
    questions?: string[];
  } | null;
}

interface Project {
  id: number;
  name: string;
  description?: string;
  cuenca?: string;
}

export default function ChatPage() {
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [chats, setChats] = useState<{ id: number; title: string; created_at: string }[]>([]);
  const [activeChatId, setActiveChatId] = useState<number | null>(null);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const [projectId, setProjectId] = useState<number | null>(null);
  const [filters, setFilters] = useState<FilterParams>({});
  const [showFilters, setShowFilters] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [uploadTasks, setUploadTasks] = useState<UploadTask[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [renamingChatId, setRenamingChatId] = useState<number | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [documentInsights, setDocumentInsights] = useState<{
    summary?: string;
    sections?: string[];
    questions?: string[];
  } | null>(null);
  const [outlineOpen, setOutlineOpen] = useState(false);
  const [outlineData, setOutlineData] = useState<{
    title: string;
    summary?: string;
    global_topics?: string[];
    global_questions?: string[];
    sections: {
      name: string;
      topics?: string[];
      important_points?: string[];
      questions?: string[];
    }[];
  }>({ title: "", sections: [] });

  const loadChats = useCallback(async () => {
    try {
      const data = await listChats();
      setChats(data);
    } catch (e) {
      console.error("Failed to load chats:", e);
    }
  }, []);

  const loadChat = useCallback(async (chatId: number) => {
    try {
      const data = await getChatMessages(chatId);
      // Map structured_response from API to answer_data for rendering
      const mappedMessages = data.map((msg: Message) => ({
        ...msg,
        answer_data: msg.structured_response || msg.answer_data,
      }));
      setMessages(mappedMessages);
      setActiveChatId(chatId);
      // Load document outline for this chat
      await loadChatOutline(chatId);
    } catch (e) {
      console.error("Failed to load chat:", e);
    }
  }, []);

  const loadChatOutline = useCallback(async (chatId: number) => {
    try {
      const token = getAuthToken();
      const res = await fetch(`http://localhost:8000/api/v1/chats/${chatId}/outline`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setOutlineData(data);
        if (data.sections.length > 0 || data.summary || (data.global_topics?.length ?? 0) > 0) {
          setOutlineOpen(true);
        }
      }
    } catch (e) {
      console.error("Failed to load outline:", e);
    }
  }, []);

  const loadProject = useCallback(async (pid: number) => {
    try {
      const token = getAuthToken();
      const res = await fetch(`http://localhost:8000/api/v1/projects/${pid}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setCurrentProject(data);
      }
    } catch (e) {
      console.error("Failed to load project:", e);
    }
  }, []);

  const checkAuth = useCallback(async () => {
    const token = getAuthToken();
    if (!token) {
      router.push("/auth");
      return;
    }

    // Check project selection
    const storedProjectId = localStorage.getItem("petroquery_project_id");
    if (!storedProjectId) {
      router.push("/projects");
      return;
    }
    const pid = parseInt(storedProjectId, 10);
    if (isNaN(pid)) {
      router.push("/projects");
      return;
    }
    setProjectId(pid);

    try {
      const user = await getCurrentUser();
      setCurrentUser(user);
      await loadProject(pid);
      await loadChats();
      const urlParams = new URLSearchParams(window.location.search);
      const chatIdFromUrl = urlParams.get("chat");
      if (chatIdFromUrl) {
        const chatId = parseInt(chatIdFromUrl, 10);
        if (!isNaN(chatId)) {
          await loadChat(chatId);
        }
      }
    } catch (e) {
      apiLogout();
      router.push("/auth");
    }
  }, [router, loadChats, loadChat, loadProject]);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!input.trim() || isLoading) return;

      const userMessage: Message = {
        id: Date.now().toString(),
        role: "user",
        content: input.trim(),
      };
      setMessages((prev) => [...prev, userMessage]);
      setInput("");
      setIsLoading(true);

      try {
        const answer: OGTechnicalAnswer = await askQuestion(
          userMessage.content,
          activeChatId ?? undefined,
          filters,
          projectId ?? undefined
        );

        const assistantMsg: Message = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: answer.respuesta_tecnica,
          answer_data: answer,
        };

        setMessages((prev) => [...prev, assistantMsg]);

        if (answer.chat_id) {
          setActiveChatId(answer.chat_id);
          const url = new URL(window.location.href);
          url.searchParams.set("chat", answer.chat_id.toString());
          window.history.replaceState({}, "", url.toString());
          await loadChats();
        }
      } catch (error) {
        setMessages((prev) => [
          ...prev,
          {
            id: (Date.now() + 1).toString(),
            role: "assistant",
            content:
              "Lo siento, ocurrió un error al procesar tu consulta. Por favor, intenta nuevamente.",
          },
        ]);
      } finally {
        setIsLoading(false);
      }
    },
    [input, isLoading, activeChatId, filters, loadChats]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit(e as unknown as React.FormEvent);
      }
    },
    [handleSubmit]
  );

  const handleNewChat = useCallback(async () => {
    setMessages([]);
    setActiveChatId(null);
    setDocumentInsights(null);
    setOutlineOpen(false);
    setOutlineData({ title: "", sections: [] });
    router.push("/chat");
    await loadChats();
    setTimeout(() => {
      textareaRef.current?.focus();
    }, 100);
  }, [router, loadChats]);

  const handleDeleteChat = useCallback(
    async (chatId: number) => {
      if (!confirm("¿Eliminar este chat?")) return;
      try {
        await deleteChat(chatId);
        if (activeChatId === chatId) {
          setMessages([]);
          setActiveChatId(null);
          setDocumentInsights(null);
          setOutlineOpen(false);
          setOutlineData({ title: "", sections: [] });
        }
        await loadChats();
      } catch (e) {
        console.error("Failed to delete chat:", e);
      }
    },
    [activeChatId, loadChats]
  );

  const startRename = useCallback((chat: { id: number; title: string }) => {
    setRenamingChatId(chat.id);
    setRenameValue(chat.title);
  }, []);

  const confirmRename = useCallback(
    async (chatId: number) => {
      if (!renameValue.trim()) return;
      try {
        await renameChat(chatId, renameValue.trim());
        setRenamingChatId(null);
        await loadChats();
      } catch (e) {
        console.error("Failed to rename chat:", e);
      }
    },
    [renameValue, loadChats]
  );

  const handleFileUpload = useCallback(
    async (file: File) => {
      if (!projectId) {
        console.error("No project selected");
        return;
      }
      try {
        const result = await uploadPDF(
          file,
          projectId,
          {
            cuenca: filters.cuenca,
            tipo_equipo: filters.tipo_equipo,
            normativa_aplicable: filters.normativa_aplicable,
            tipo_documento: filters.tipo_documento,
          }
        );

        const newTask: UploadTask = {
          id: result.document_id,
          fileName: file.name,
          progress: result.status === "completed" ? 100 : 0,
          status:
            result.status === "completed"
              ? "Completado"
              : "Procesando...",
          chatId: result.chat_id,
        };

        setUploadTasks((prev) => [...prev, newTask]);

        if (result.status !== "completado") {
          const interval = setInterval(async () => {
            try {
              const status = await getUploadStatus(result.document_id);
              setUploadTasks((prev) =>
                prev.map((t) =>
                  t.id === result.document_id
                    ? {
                        ...t,
                        progress: status.progress,
                        status:
                          status.status === "completed"
                            ? "Completado"
                            : status.status === "failed"
                            ? "Error"
                            : "Procesando...",
                        insights: status.insights || t.insights,
                      }
                    : t
                )
              );
              if (
                status.status === "completed" ||
                status.status === "failed"
              ) {
                clearInterval(interval);
                // Store insights persistently when upload completes
                if (status.status === "completed" && status.insights) {
                  setDocumentInsights(status.insights);
                }
                // Auto-load outline and activate chat when upload completes
                if (result.chat_id) {
                  loadChatOutline(result.chat_id);
                  setActiveChatId(result.chat_id);
                  const url = new URL(window.location.href);
                  url.searchParams.set("chat", result.chat_id.toString());
                  window.history.replaceState({}, "", url.toString());
                  loadChats();
                }
              }
            } catch (e) {
              clearInterval(interval);
            }
          }, 2000);
        }
      } catch (e) {
        console.error("Upload failed:", e);
        setUploadTasks((prev) => [
          ...prev,
          {
            id: Date.now(),
            fileName: file.name,
            progress: 0,
            status: "Error",
          },
        ]);
      }
    },
    [filters, projectId, loadChatOutline, loadChats]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file && file.type === "application/pdf") {
        handleFileUpload(file);
      }
    },
    [handleFileUpload]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleFileInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFileUpload(file);
      if (fileInputRef.current) fileInputRef.current.value = "";
    },
    [handleFileUpload]
  );

  const removeUploadTask = useCallback((id: number | string) => {
    setUploadTasks((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const messagesMemo = useMemo(
    () =>
      messages.map((msg) => <ChatMessage key={String(msg.id)} message={msg} />),
    [messages]
  );

  const sidebarContent = (
    <>
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-petro-blue flex items-center justify-center">
            <Droplets className="w-5 h-5 text-white" />
          </div>
          <span className="font-bold text-base text-petro-blue">
            PetroQuery
          </span>
        </div>
        {currentProject && (
          <div className="mt-3 px-2 py-2 rounded-lg bg-petro-light border border-petro-blue/10">
            <div className="flex items-center gap-2">
              <FolderOpen className="w-3.5 h-3.5 text-petro-blue" />
              <span className="text-xs font-medium text-petro-blue truncate">
                {currentProject.name}
              </span>
            </div>
            {currentProject.cuenca && (
              <span className="text-[10px] text-gray-500 ml-5.5">{currentProject.cuenca}</span>
            )}
          </div>
        )}
        <button
          onClick={() => router.push("/projects")}
          className="mt-2 w-full flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-xs text-gray-500 hover:text-petro-blue hover:bg-petro-light transition-colors"
        >
          <ArrowLeft className="w-3 h-3" />
          Cambiar proyecto
        </button>
      </div>

      <div className="p-3">
        <button
          onClick={handleNewChat}
          className={cn(
            "w-full flex items-center gap-2 px-4 py-3 rounded-xl font-medium transition-all duration-200 shadow-sm",
            activeChatId === null
              ? "bg-petro-orange text-white ring-2 ring-petro-orange/30"
              : "bg-petro-blue text-white hover:bg-petro-dark"
          )}
        >
          <Plus className="w-4 h-4" />
          {activeChatId === null ? "Nueva consulta (activa)" : "Nueva consulta"}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-3 pb-3 space-y-1">
        <div className="px-2 py-2 text-[10px] font-bold text-gray-400 uppercase tracking-wider">
          Historial
        </div>
        {chats.length === 0 ? (
          <div className="px-2 py-6 text-center">
            <MessageSquare className="w-8 h-8 text-gray-300 mx-auto mb-2" />
            <p className="text-xs text-gray-400">Sin consultas aún</p>
          </div>
        ) : (
          chats.map((chat) => (
            <div
              key={chat.id}
              className={cn(
                "group relative rounded-lg transition-colors",
                activeChatId === chat.id
                  ? "bg-petro-light border border-petro-blue/10"
                  : "hover:bg-gray-50 border border-transparent"
              )}
            >
              {renamingChatId === chat.id ? (
                <div className="flex items-center gap-1 px-2 py-2">
                  <input
                    autoFocus
                    value={renameValue}
                    onChange={(e) => setRenameValue(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") confirmRename(chat.id);
                      if (e.key === "Escape") setRenamingChatId(null);
                    }}
                    className="flex-1 min-w-0 px-2 py-1 text-sm bg-white border border-gray-200 rounded focus:outline-none focus:border-petro-blue"
                  />
                  <button
                    onClick={() => confirmRename(chat.id)}
                    className="p-1 rounded hover:bg-green-100 text-green-600"
                  >
                    <Check className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => setRenamingChatId(null)}
                    className="p-1 rounded hover:bg-red-100 text-red-600"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => loadChat(chat.id)}
                  className="w-full text-left px-3 py-2.5 pr-8"
                >
                  <span
                    className={cn(
                      "block text-sm truncate",
                      activeChatId === chat.id
                        ? "text-petro-blue font-semibold"
                        : "text-gray-700"
                    )}
                  >
                    {chat.title || `Chat #${chat.id}`}
                  </span>
                </button>
              )}
              {renamingChatId !== chat.id && (
                <div className="absolute right-1 top-1/2 -translate-y-1/2 hidden group-hover:flex items-center gap-0.5">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      startRename(chat);
                    }}
                    className="p-1 rounded hover:bg-gray-200 text-gray-500"
                    title="Renombrar"
                  >
                    <Pencil className="w-3 h-3" />
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteChat(chat.id);
                    }}
                    className="p-1 rounded hover:bg-red-100 text-red-500"
                    title="Eliminar"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      <div className="p-3 border-t border-gray-200 space-y-1">
        {currentUser && (
          <div className="flex items-center gap-2 px-2 py-2 rounded-lg bg-gray-50 mb-2">
            <div className="w-8 h-8 rounded-full bg-petro-blue flex items-center justify-center">
              <UserIcon className="w-4 h-4 text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-800 truncate">
                {currentUser.username}
              </p>
              <p className="text-[10px] text-gray-500 truncate">
                {currentUser.email}
              </p>
            </div>
          </div>
        )}
        <button
          onClick={() => {
            apiLogout();
            router.push("/auth");
          }}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-gray-600 hover:text-red-600 hover:bg-red-50 transition-colors text-sm"
        >
          <LogOut className="w-4 h-4" />
          Cerrar sesión
        </button>
      </div>
    </>
  );

  return (
    <div className="h-screen bg-petro-gray text-gray-900 font-sans flex overflow-hidden">
      {/* Desktop Sidebar */}
      <aside
        className={cn(
          "hidden md:flex flex-col bg-white border-r border-gray-200 transition-all duration-300",
          sidebarOpen ? "w-72" : "w-0 overflow-hidden"
        )}
      >
        {sidebarContent}
      </aside>

      {/* Mobile Sidebar Overlay */}
      {mobileSidebarOpen && (
        <div className="fixed inset-0 z-50 flex md:hidden">
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => setMobileSidebarOpen(false)}
          />
          <div className="relative w-72 bg-white h-full flex flex-col shadow-xl">
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              <span className="font-bold text-petro-blue">PetroQuery</span>
              <button
                onClick={() => setMobileSidebarOpen(false)}
                className="p-2 rounded-lg hover:bg-gray-100"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
            </div>
            {sidebarContent}
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Header */}
        <header className="flex items-center gap-3 px-4 py-3 bg-white border-b border-gray-200 shadow-sm flex-shrink-0">
          <button
            onClick={() => setMobileSidebarOpen(true)}
            className="md:hidden p-2 rounded-lg hover:bg-gray-100"
          >
            <Menu className="w-5 h-5 text-gray-600" />
          </button>
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="hidden md:flex p-2 rounded-lg hover:bg-gray-100"
          >
            <Menu className="w-5 h-5 text-gray-600" />
          </button>
          <div className="flex-1 min-w-0">
            <h1 className="text-sm font-semibold text-gray-800 truncate">
              {activeChatId
                ? chats.find((c) => c.id === activeChatId)?.title ||
                  `Consulta #${activeChatId}`
                : "Nueva consulta técnica"}
            </h1>
            <p className="text-[10px] text-gray-400 truncate">
              {currentProject
                ? `${currentProject.name} · ${currentProject.cuenca || "Sin cuenca"}`
                : activeChatId
                ? "Consulta con trazabilidad completa"
                : "Inicia una nueva consulta especializada"}
            </p>
          </div>
          <button
            onClick={() => setOutlineOpen(!outlineOpen)}
            className={cn(
              "hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors",
              outlineOpen
                ? "bg-petro-blue text-white"
                : "text-petro-blue hover:bg-petro-light"
            )}
            title="Ver contenido del documento"
          >
            <BookOpen className="w-3.5 h-3.5" />
            Contenido
          </button>
          <Link
            href="/manual"
            className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-petro-blue hover:bg-petro-light transition-colors"
          >
            <BookOpen className="w-3.5 h-3.5" />
            Manual
          </Link>
        </header>

        {/* Messages */}
        <div
          className={cn(
            "flex-1 overflow-y-auto px-4 py-6 space-y-6",
            isDragging && "bg-petro-blue/5"
          )}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
        >
          {messages.length === 0 && !isLoading && (
            <div className="flex flex-col items-center justify-center h-full text-center px-6">
              <div className="w-20 h-20 rounded-2xl bg-petro-blue flex items-center justify-center mb-5 shadow-lg shadow-petro-blue/20">
                <Droplets className="w-10 h-10 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                PetroQuery
              </h2>
              <p className="text-gray-500 max-w-md mb-6">
                Asistente técnico especializado para operaciones Oil & Gas en
                Vaca Muerta. Consulta normativas, manuales y reportes con
                trazabilidad total.
              </p>
              <div className="flex items-center gap-3 px-5 py-4 bg-white border border-gray-200 rounded-xl text-sm text-gray-600 max-w-sm">
                <div className="w-10 h-10 rounded-lg bg-petro-light flex items-center justify-center flex-shrink-0">
                  <Upload className="w-5 h-5 text-petro-blue" />
                </div>
                <div className="text-left">
                  <p className="font-medium text-gray-800">No hay documentos cargados</p>
                  <p className="text-gray-500 mt-0.5">Subí un PDF técnico para empezar a consultar</p>
                </div>
              </div>
            </div>
          )}

          {messagesMemo}

          {isLoading && (
            <div className="flex gap-4 max-w-5xl">
              <div className="w-9 h-9 rounded-lg bg-petro-orange flex items-center justify-center flex-shrink-0">
                <Droplets className="w-5 h-5 text-white" />
              </div>
              <div className="flex items-center gap-2 px-5 py-4 rounded-2xl bg-white border border-gray-200 shadow-sm">
                <div className="flex gap-1">
                  <span
                    className="w-2 h-2 rounded-full bg-gray-400 animate-bounce"
                    style={{ animationDelay: "0ms" }}
                  />
                  <span
                    className="w-2 h-2 rounded-full bg-gray-400 animate-bounce"
                    style={{ animationDelay: "150ms" }}
                  />
                  <span
                    className="w-2 h-2 rounded-full bg-gray-400 animate-bounce"
                    style={{ animationDelay: "300ms" }}
                  />
                </div>
                <span className="text-sm text-gray-500">
                  Analizando documentación técnica...
                </span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Upload tasks & Insights */}
        {uploadTasks.length > 0 && (
          <div className="px-4 py-3 bg-white border-t border-gray-200 space-y-3">
            {uploadTasks.map((task) => (
              <div key={task.id}>
                <div className="flex items-center gap-2 mb-2">
                  <div className="flex-1">
                    <UploadProgress
                      progress={task.progress}
                      status={task.status}
                      fileName={task.fileName}
                    />
                  </div>
                  {task.status === "Completado" && task.chatId && (
                    <button
                      onClick={() => {
                        if (task.chatId) {
                          loadChat(task.chatId);
                          removeUploadTask(task.id);
                        }
                      }}
                      className="px-3 py-1.5 rounded-lg bg-petro-blue text-white text-xs font-medium hover:bg-petro-dark transition-colors"
                    >
                      Ver documento
                    </button>
                  )}
                  {(task.status === "Completado" || task.status === "Error") && (
                    <button
                      onClick={() => removeUploadTask(task.id)}
                      className="p-2 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Persistent Document Insights */}
        {documentInsights && (
          <div className="px-4 py-3 bg-white border-t border-gray-200">
            <DocumentInsights
              insights={documentInsights}
              onAskQuestion={(q) => {
                setInput(q);
                textareaRef.current?.focus();
              }}
            />
          </div>
        )}

        {/* Input Area */}
        <div className="px-4 py-4 bg-white border-t border-gray-200">
          <div className="max-w-4xl mx-auto space-y-3">
            <AdvancedFilters filters={filters} onChange={setFilters} />

            <form
              onSubmit={handleSubmit}
              className="flex items-end gap-3"
            >
              <div className="flex-1 relative">
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Escribe tu consulta técnica..."
                  rows={1}
                  className="w-full px-4 py-3.5 bg-petro-gray border border-gray-200 rounded-xl text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-petro-blue/20 focus:border-petro-blue resize-none text-sm"
                  style={{ minHeight: 48, maxHeight: 160 }}
                />
              </div>

              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="p-3.5 rounded-xl bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors"
                title="Subir PDF"
              >
                <Upload className="w-5 h-5" />
              </button>

              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                onChange={handleFileInputChange}
                className="hidden"
              />

              <button
                type="submit"
                disabled={!input.trim() || isLoading}
                className="p-3.5 rounded-xl bg-petro-blue text-white hover:bg-petro-dark disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-sm"
              >
                {isLoading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </button>
            </form>

            {isDragging && (
              <div className="absolute inset-x-0 bottom-0 p-4 bg-petro-blue/10 border-t-2 border-dashed border-petro-blue text-center">
                <p className="text-sm font-medium text-petro-blue">
                  Suelta el PDF aquí para subirlo
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Right Panel: Document Outline */}
      <DocumentOutline
        title={outlineData.title}
        summary={outlineData.summary}
        global_topics={outlineData.global_topics}
        global_questions={outlineData.global_questions}
        sections={outlineData.sections}
        onAskQuestion={(q) => {
          setInput(q);
          textareaRef.current?.focus();
        }}
        isOpen={outlineOpen}
        onClose={() => setOutlineOpen(false)}
      />
    </div>
  );
}
