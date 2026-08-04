"use client";

import { AlertTriangle } from "lucide-react";
import { useLanguage } from "@/lib/i18n";

interface SafetyBannerProps {
  warning?: string;
}

export default function SafetyBanner({ warning }: SafetyBannerProps) {
  const { t } = useLanguage();
  if (!warning) return null;

  return (
    <div className="w-full bg-petro-orange text-white px-4 py-3 rounded-lg shadow-md flex items-start gap-3 animate-in fade-in slide-in-from-top-2 duration-300">
      <AlertTriangle className="w-6 h-6 flex-shrink-0 mt-0.5" />
      <div className="flex-1">
        <p className="font-bold text-sm uppercase tracking-wide">
          {t("safety.warningTitle")}
        </p>
        <p className="text-sm mt-0.5 font-medium leading-relaxed">{warning}</p>
      </div>
    </div>
  );
}
