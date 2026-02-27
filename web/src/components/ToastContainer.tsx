"use client";

import { useState, useEffect } from "react";
import { X, CheckCircle2, AlertCircle, Info } from "lucide-react";
import { cn } from "@/lib/utils";

type ToastType = "success" | "error" | "info";

interface Toast {
  id: string;
  message: string;
  type: ToastType;
}

/**
 * Global event-based toast system.
 */
export const toastEvents = {
  emit: (message: string, type: ToastType) => {
    const event = new CustomEvent("app-toast", { 
      detail: { message, type, id: Math.random().toString(36).substr(2, 9) } 
    });
    window.dispatchEvent(event);
  }
};

export default function ToastContainer() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  useEffect(() => {
    const handleToast = (e: Event) => {
      const { message, type, id } = (e as CustomEvent).detail;
      setToasts((prev) => [...prev, { id, message, type }]);

      // Auto-remove after 5 seconds
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, 5000);
    };

    window.addEventListener("app-toast", handleToast);
    return () => window.removeEventListener("app-toast", handleToast);
  }, []);

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  if (toasts.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-[9999] flex flex-col gap-3 w-full max-w-sm">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={cn(
            "flex items-start gap-3 p-4 rounded-xl border shadow-lg animate-in fade-in slide-in-from-right-8 duration-300",
            toast.type === "success" && "bg-emerald-50 border-emerald-200 text-emerald-800 dark:bg-emerald-950/30 dark:border-emerald-900/50 dark:text-emerald-400",
            toast.type === "error" && "bg-rose-50 border-rose-200 text-rose-800 dark:bg-rose-950/30 dark:border-rose-900/50 dark:text-rose-400",
            toast.type === "info" && "bg-indigo-50 border-indigo-200 text-indigo-800 dark:bg-indigo-950/30 dark:border-indigo-900/50 dark:text-indigo-400"
          )}
        >
          <div className="shrink-0 mt-0.5">
            {toast.type === "success" && <CheckCircle2 className="h-5 w-5" />}
            {toast.type === "error" && <AlertCircle className="h-5 w-5" />}
            {toast.type === "info" && <Info className="h-5 w-5" />}
          </div>
          <div className="flex-1 text-sm font-medium leading-relaxed">
            {toast.message}
          </div>
          <button
            onClick={() => removeToast(toast.id)}
            className="shrink-0 hover:opacity-70 transition-opacity"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      ))}
    </div>
  );
}
