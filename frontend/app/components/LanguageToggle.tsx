"use client";

import { useLanguage } from "@/lib/i18n";
import { Languages } from "lucide-react";

export default function LanguageToggle() {
  const { language, setLanguage } = useLanguage();

  return (
    <button
      onClick={() => setLanguage(language === "es" ? "en" : "es")}
      className="relative flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-gray-200 text-gray-700 text-sm font-medium hover:bg-gray-50 transition-colors"
      title={language === "es" ? "Switch to English" : "Cambiar a Español"}
    >
      <Languages className="w-4 h-4" />
      <span className="hidden sm:inline">{language === "es" ? "EN" : "ES"}</span>
      <span className="sm:hidden">{language === "es" ? "EN" : "ES"}</span>
    </button>
  );
}