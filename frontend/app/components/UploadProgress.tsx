import { cn } from "@/lib/utils";
import { Upload, Loader2, CheckCircle2, XCircle } from "lucide-react";

interface UploadProgressProps {
  progress: number;
  status: string;
  fileName: string;
}

export default function UploadProgress({ progress, status, fileName }: UploadProgressProps) {
  const isError = status.toLowerCase().includes("error");
  const isCompleted = status.toLowerCase().includes("completado");
  const isProcessing = status.toLowerCase().includes("procesando");

  const statusIcon = isError ? (
    <XCircle className="w-4 h-4 text-red-500" />
  ) : isCompleted ? (
    <CheckCircle2 className="w-4 h-4 text-green-500" />
  ) : (
    <Loader2 className={cn("w-4 h-4 text-petro-blue", isProcessing && "animate-spin")} />
  );

  const barColor = isError
    ? "bg-red-500"
    : isCompleted
    ? "bg-green-500"
    : "bg-petro-blue";

  return (
    <div className="w-full bg-white border border-gray-200 rounded-lg p-3 shadow-sm">
      <div className="flex items-center gap-2 mb-2">
        <Upload className="w-4 h-4 text-gray-500" />
        <span className="text-sm font-medium text-gray-800 truncate">{fileName}</span>
        <div className="ml-auto flex items-center gap-1.5">
          {statusIcon}
          <span
            className={cn(
              "text-xs font-medium",
              isError ? "text-red-600" : isCompleted ? "text-green-600" : "text-petro-blue"
            )}
          >
            {status}
          </span>
        </div>
      </div>
      <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={cn("h-full transition-all duration-300 rounded-full", barColor)}
          style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
        />
      </div>
      <div className="text-right mt-1">
        <span className="text-[10px] text-gray-400 font-medium">{progress.toFixed(0)}%</span>
      </div>
    </div>
  );
}
