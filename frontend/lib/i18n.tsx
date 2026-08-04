"use client";

import { createContext, useContext, useState, useEffect, ReactNode, useCallback } from "react";

export type Language = "es" | "en";

const translations = {
  es: {
    // Auth / Login
    "auth.title": "Iniciar Sesión",
    "auth.subtitle": "Acceso corporativo - PetroQuery",
    "auth.usernameLabel": "Usuario",
    "auth.usernamePlaceholder": "tuusuario",
    "auth.passwordLabel": "Contraseña",
    "auth.passwordPlaceholder": "••••••••",
    "auth.submit": "Iniciar Sesión",
    "auth.loading": "Iniciando...",
    "auth.error": "Ocurrió un error",
    "auth.sso": "Ingresar con SSO Corporativo",
    "auth.back": "Volver",

    // Chat page
    "chat.newQuery": "Nueva consulta técnica",
    "chat.noQueries": "Sin consultas aún",
    "chat.deleteConfirm": "¿Eliminar este chat?",
    "chat.renameTitle": "Renombrar",
    "chat.deleteTitle": "Eliminar",
    "chat.viewDocument": "Ver contenido del documento",
    "chat.uploadPrompt": "Sube un PDF técnico para empezar a consultar",
    "chat.inputPlaceholder": "Escribe tu consulta técnica...",
    "chat.uploadTitle": "Subir PDF",
    "chat.errorProcessing": "Lo siento, ocurrió un error al procesar tu consulta. Por favor, intenta nuevamente.",

    // ChatMessage
    "chatMessage.sourcesConsulted": "Fuentes consultadas",
    "chatMessage.requiresHumanReview": "Esta respuesta requiere revisión humana antes de su aplicación operativa.",
    "chatMessage.queryType": "Tipo de consulta",

    // SafetyBanner
    "safety.warningTitle": "Advertencia de Seguridad",

    // ConfidenceBadge
    "confidence.high": "Alta confianza",
    "confidence.medium": "Confianza media - Verificar",
    "confidence.low": "Baja confianza - Revisión humana requerida",

    // SourceCard
    "source.page": "Pág.",
    "source.section": "Sección",
    "source.table": "Tabla",
    "source.figure": "Figura",
    "source.hideContent": "Ocultar contenido",
    "source.showContent": "Ver contenido citado",
    "source.viewInDocument": "Ver en documento",
    "source.documentDetail": "Detalle de fuente",
    "source.document": "Documento",
    "source.score": "Score de confianza",
    "source.basin": "Cuenca",
    "source.regulation": "Normativa",
    "source.citedContent": "Contenido citado",
    "source.footer": "Fuente consultada por PetroQuery con trazabilidad absoluta",

    // AdvancedFilters
    "filters.title": "Filtros avanzados",
    "filters.clear": "Limpiar filtros",
    "filters.basin": "Cuenca",
    "filters.docType": "Tipo de Documento",
    "filters.equipmentType": "Tipo de Equipo",
    "filters.regulation": "Normativa Aplicable",
    "filters.all": "Todas",
    "filters.allOptions": "Todos",

    // Basins
    "basin.vacaMuerta": "Vaca Muerta",
    "basin.neuquina": "Neuquina",
    "basin.golfoSanJorge": "Golfo San Jorge",
    "basin.cuyana": "Cuyana",

    // Document Types
    "docType.manual": "manual",
    "docType.regulation": "normativa",
    "docType.report": "reporte",
    "docType.specification": "especificacion",

    // Equipment Types
    "equip.bop": "BOP",
    "equip.casing": "Casing",
    "equip.tubing": "Tubing",
    "equip.christmasTree": "Christmas Tree",
    "equip.pumpjack": "Pumpjack",

    // Regulations
    "reg.iapg": "IAPG-IRAM 301",
    "reg.api14b": "API RP 14B",
    "reg.api14c": "API RP 14C",
    "reg.api75": "API RP 75",
    "reg.asme": "ANSI/ASME B31.3",

    // UploadProgress
    "upload.status.uploading": "Subiendo",
    "upload.status.processing": "Procesando",
    "upload.status.completed": "Completado",
    "upload.status.error": "Error",

    // DocumentInsights
    "insights.title": "Resumen del documento",
    "insights.summary": "Resumen técnico",
    "insights.sections": "Secciones detectadas",
    "insights.questions": "Preguntas sugeridas",

    // DocumentOutline
    "outline.title": "Estructura del documento",
    "outline.summary": "Resumen",
    "outline.topics": "Temas",
    "outline.keyPoints": "Puntos clave",
    "outline.suggestedQuestions": "Preguntas sugeridas",
    "outline.chapters": "Capítulos",
    "outline.generalQuestions": "Preguntas generales",
    "outline.empty": "No se detectó estructura en el documento.",
    "outline.expand": "Expandir",
    "outline.collapse": "Colapsar",

    // NumberHighlighter
    // (no user-facing strings)

    // Common UI
    "common.yes": "Sí",
    "common.no": "No",
    "common.cancel": "Cancelar",
    "common.save": "Guardar",
    "common.delete": "Eliminar",
    "common.edit": "Editar",
    "common.loading": "Cargando...",
    "common.error": "Error",
    "common.success": "Éxito",
    "common.empty": "N/A",

    // Navigation / Layout
    "nav.projects": "Proyectos",
    "nav.admin": "Administración",
    "nav.manual": "Manual",
    "nav.chat": "Chat",
    "nav.logout": "Cerrar sesión",
    "nav.language": "Idioma",

    // Admin page
    "admin.title": "Panel de Administración",
    "admin.users": "Usuarios",
    "admin.invite": "Invitar usuario",
    "admin.audits": "Auditoría de Consultas",
    "admin.projects": "Proyectos",
    "admin.inviteUser": "Invitar Usuario",
    "admin.email": "Email",
    "admin.username": "Usuario",
    "admin.role": "Rol",
    "admin.project": "Proyecto",
    "admin.selectProject": "Seleccionar proyecto",
    "admin.sendInvitation": "Enviar Invitación",
    "admin.invitationSent": "Invitación enviada exitosamente",
    "admin.inviteError": "Error al enviar invitación",
    "admin.totalUsers": "Total Usuarios",
    "admin.totalDocuments": "Documentos",
    "admin.totalChunks": "Chunks",
    "admin.estimatedTokens": "Tokens Est.",
    "admin.activity": "Actividad (Últimos 7 días)",
    "admin.usersTable": "Usuarios",
    "admin.refresh": "Actualizar",
    "admin.userColumn": "Usuario",
    "admin.emailColumn": "Email",
    "admin.registeredColumn": "Registrado",
    "admin.docsColumn": "Docs",
    "admin.statusColumn": "Estado",
    "admin.actionsColumn": "Acciones",
    "admin.active": "Activo",
    "admin.suspended": "Suspendido",
    "admin.suspend": "Suspender",
    "admin.activate": "Activar",
    "admin.roleOperator": "Operador",
    "admin.roleEngineer": "Ingeniero",
    "admin.roleAdmin": "Admin",
    "admin.errorLogs": "Logs de Error",
    "admin.systemOperational": "System operational",
    "admin.dbConnected": "Database connection active",

    // Projects page
    "projects.title": "Mis Proyectos",
    "projects.new": "Nuevo Proyecto",
    "projects.empty": "No tienes proyectos aún",
    "projects.emptyDescription": "Crea tu primer proyecto para empezar a cargar documentos técnicos.",
    "projects.create": "Crear proyecto",
    "projects.createModalTitle": "Nuevo Proyecto",
    "projects.name": "Nombre",
    "projects.nameLabel": "Nombre del Proyecto",
    "projects.namePlaceholder": "Ej: Yacimiento Loma Campana",
    "projects.description": "Descripción",
    "projects.descriptionPlaceholder": "Descripción del proyecto...",
    "projects.company": "Empresa",
    "projects.basin": "Cuenca",
    "projects.basinPlaceholder": "Cuenca",
    "projects.location": "Ubicación",
    "projects.locationPlaceholder": "Ubicación",
    "projects.selectProject": "Selecciona un proyecto para continuar",
    "projects.createProject": "Crear proyecto",
    "projects.createNew": "Nuevo Proyecto",
    "projects.cancel": "Cancelar",
    "projects.save": "Guardar",
    "projects.noCompany": "Sin empresa",

    // Manual page
    "manual.title": "Manual de Usuario",
    "manual.sections": "Secciones",
  },
  en: {
    // Auth / Login
    "auth.title": "Sign In",
    "auth.subtitle": "Corporate Access - PetroQuery",
    "auth.usernameLabel": "Username",
    "auth.usernamePlaceholder": "yourusername",
    "auth.passwordLabel": "Password",
    "auth.passwordPlaceholder": "••••••••",
    "auth.submit": "Sign In",
    "auth.loading": "Signing in...",
    "auth.error": "An error occurred",
    "auth.sso": "Sign in with Corporate SSO",
    "auth.back": "Back",

    // Chat page
    "chat.newQuery": "New technical query",
    "chat.noQueries": "No queries yet",
    "chat.deleteConfirm": "Delete this chat?",
    "chat.renameTitle": "Rename",
    "chat.deleteTitle": "Delete",
    "chat.viewDocument": "View document content",
    "chat.uploadPrompt": "Upload a technical PDF to start querying",
    "chat.inputPlaceholder": "Enter your technical query...",
    "chat.uploadTitle": "Upload PDF",
    "chat.errorProcessing": "Sorry, an error occurred while processing your query. Please try again.",

    // ChatMessage
    "chatMessage.sourcesConsulted": "Sources consulted",
    "chatMessage.requiresHumanReview": "This response requires human review before operational application.",
    "chatMessage.queryType": "Query type",

    // SafetyBanner
    "safety.warningTitle": "Safety Warning",

    // ConfidenceBadge
    "confidence.high": "High confidence",
    "confidence.medium": "Medium confidence - Verify",
    "confidence.low": "Low confidence - Human review required",

    // SourceCard
    "source.page": "Pg.",
    "source.section": "Section",
    "source.table": "Table",
    "source.figure": "Figure",
    "source.hideContent": "Hide content",
    "source.showContent": "View cited content",
    "source.viewInDocument": "View in document",
    "source.documentDetail": "Source Detail",
    "source.document": "Document",
    "source.score": "Confidence Score",
    "source.basin": "Basin",
    "source.regulation": "Regulation",
    "source.citedContent": "Cited Content",
    "source.footer": "Source retrieved by PetroQuery with full traceability",

    // AdvancedFilters
    "filters.title": "Advanced Filters",
    "filters.clear": "Clear Filters",
    "filters.basin": "Basin",
    "filters.docType": "Document Type",
    "filters.equipmentType": "Equipment Type",
    "filters.regulation": "Applicable Regulation",
    "filters.all": "All",
    "filters.allOptions": "All",

    // Basins
    "basin.vacaMuerta": "Vaca Muerta",
    "basin.neuquina": "Neuquina",
    "basin.golfoSanJorge": "Golfo San Jorge",
    "basin.cuyana": "Cuyana",

    // Document Types
    "docType.manual": "manual",
    "docType.regulation": "regulation",
    "docType.report": "report",
    "docType.specification": "specification",

    // Equipment Types
    "equip.bop": "BOP",
    "equip.casing": "Casing",
    "equip.tubing": "Tubing",
    "equip.christmasTree": "Christmas Tree",
    "equip.pumpjack": "Pumpjack",

    // Regulations
    "reg.iapg": "IAPG-IRAM 301",
    "reg.api14b": "API RP 14B",
    "reg.api14c": "API RP 14C",
    "reg.api75": "API RP 75",
    "reg.asme": "ANSI/ASME B31.3",

    // UploadProgress
    "upload.status.uploading": "Uploading",
    "upload.status.processing": "Processing",
    "upload.status.completed": "Completed",
    "upload.status.error": "Error",

    // DocumentInsights
    "insights.title": "Document Summary",
    "insights.summary": "Technical Summary",
    "insights.sections": "Detected Sections",
    "insights.questions": "Suggested Questions",

    // DocumentOutline
    "outline.title": "Document Structure",
    "outline.summary": "Summary",
    "outline.topics": "Topics",
    "outline.keyPoints": "Key Points",
    "outline.suggestedQuestions": "Suggested Questions",
    "outline.chapters": "Chapters",
    "outline.generalQuestions": "General Questions",
    "outline.empty": "No structure detected in document.",
    "outline.expand": "Expand",
    "outline.collapse": "Collapse",

    // Common UI
    "common.yes": "Yes",
    "common.no": "No",
    "common.cancel": "Cancel",
    "common.save": "Save",
    "common.delete": "Delete",
    "common.edit": "Edit",
    "common.loading": "Loading...",
    "common.error": "Error",
    "common.success": "Success",
    "common.empty": "N/A",

    // Navigation
    "nav.projects": "Projects",
    "nav.admin": "Admin",
    "nav.manual": "Manual",
    "nav.chat": "Chat",
    "nav.logout": "Logout",
    "nav.language": "Language",

    // Admin
    "admin.title": "Admin Dashboard",
    "admin.users": "Users",
    "admin.invite": "Invite User",
    "admin.audits": "Query Audits",
    "admin.projects": "Projects",
    "admin.inviteUser": "Invite User",
    "admin.email": "Email",
    "admin.username": "Username",
    "admin.role": "Role",
    "admin.project": "Project",
    "admin.selectProject": "Select project",
    "admin.sendInvitation": "Send Invitation",
    "admin.invitationSent": "Invitation sent successfully",
    "admin.inviteError": "Error sending invitation",
    "admin.totalUsers": "Total Users",
    "admin.totalDocuments": "Documents",
    "admin.totalChunks": "Chunks",
    "admin.estimatedTokens": "Est. Tokens",
    "admin.activity": "Activity (Last 7 days)",
    "admin.usersTable": "Users",
    "admin.refresh": "Refresh",
    "admin.userColumn": "User",
    "admin.emailColumn": "Email",
    "admin.registeredColumn": "Registered",
    "admin.docsColumn": "Docs",
    "admin.statusColumn": "Status",
    "admin.actionsColumn": "Actions",
    "admin.active": "Active",
    "admin.suspended": "Suspended",
    "admin.suspend": "Suspend",
    "admin.activate": "Activate",
    "admin.roleOperator": "Operator",
    "admin.roleEngineer": "Engineer",
    "admin.roleAdmin": "Admin",
    "admin.errorLogs": "Error Logs",
    "admin.systemOperational": "System operational",
    "admin.dbConnected": "Database connection active",

    // Projects
    "projects.title": "My Projects",
    "projects.new": "New Project",
    "projects.empty": "No projects yet",
    "projects.emptyDescription": "Create your first project to start uploading technical documents.",
    "projects.create": "Create Project",
    "projects.createModalTitle": "New Project",
    "projects.name": "Name",
    "projects.nameLabel": "Project Name",
    "projects.namePlaceholder": "e.g.: Loma Campana Field",
    "projects.description": "Description",
    "projects.descriptionPlaceholder": "Project description...",
    "projects.company": "Company",
    "projects.basin": "Basin",
    "projects.basinPlaceholder": "Basin",
    "projects.location": "Location",
    "projects.locationPlaceholder": "Location",
    "projects.selectProject": "Select a project to continue",
    "projects.createProject": "Create Project",
    "projects.createNew": "New Project",
    "projects.cancel": "Cancel",
    "projects.save": "Save",
    "projects.noCompany": "No company",

    // Manual
    "manual.title": "User Manual",
    "manual.sections": "Sections",
  },
} as const;

export type TranslationKey = keyof typeof translations.es;

interface LanguageContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: TranslationKey) => string;
}

const LanguageContext = createContext<LanguageContextType | null>(null);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>("es");

  useEffect(() => {
    const stored = localStorage.getItem("petroquery-language");
    if (stored === "en" || stored === "es") {
      setLanguageState(stored);
    }
  }, []);

  useEffect(() => {
    document.documentElement.lang = language;
  }, [language]);

  const setLanguage = useCallback((lang: Language) => {
    setLanguageState(lang);
    localStorage.setItem("petroquery-language", lang);
  }, []);

  const t = useCallback((key: TranslationKey): string => {
    return translations[language][key] ?? translations.es[key] ?? key;
  }, [language]);

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error("useLanguage must be used within LanguageProvider");
  return ctx;
}