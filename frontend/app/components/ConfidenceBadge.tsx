import { cn } from "@/lib/utils";
import { ShieldCheck, AlertCircle, AlertOctagon } from "lucide-react";
import type { ElementType } from "react";

interface ConfidenceBadgeProps {
  score: number;
}

export default function ConfidenceBadge({ score }: ConfidenceBadgeProps) {
  let label: string;
  let colorClass: string;
  let Icon: ElementType;

  if (score > 0.8) {
    label = "Alta confianza";
    colorClass = "bg-green-100 text-green-800 border-green-200";
    Icon = ShieldCheck;
  } else if (score >= 0.7) {
    label = "Confianza media - Verificar";
    colorClass = "bg-yellow-100 text-yellow-800 border-yellow-200";
    Icon = AlertCircle;
  } else {
    label = "Baja confianza - Revisión humana requerida";
    colorClass = "bg-red-100 text-red-800 border-red-200";
    Icon = AlertOctagon;
  }

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border",
        colorClass
      )}
    >
      <Icon className="w-3.5 h-3.5" />
      {label}
      <span className="opacity-70 font-normal">({(score * 100).toFixed(0)}%)</span>
    </span>
  );
}
