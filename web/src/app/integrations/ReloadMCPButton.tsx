"use client";

import { useState } from "react";
import { RefreshCw, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { reloadMCP } from "@/app/actions/plugins";
import { toast } from "@/lib/toast";

export default function ReloadMCPButton() {
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<"idle" | "success" | "error">("idle");
  const [message, setMessage] = useState("");

  const handleReload = async () => {
    setLoading(true);
    setStatus("idle");
    try {
      const result = await reloadMCP();
      if (result.error) {
        setStatus("error");
        setMessage(result.error);
        toast.error(result.error);
      } else {
        setStatus("success");
        setMessage("MCP servers reloaded successfully");
        toast.success("MCP servers reloaded successfully");
        // Reset status after 3 seconds
        setTimeout(() => setStatus("idle"), 3000);
      }
    } catch (error) {
      setStatus("error");
      setMessage("Failed to connect to backend");
      toast.error("Failed to connect to backend");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-2">
      <button
        onClick={handleReload}
        disabled={loading}
        className="flex w-full items-center justify-center gap-2 rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:opacity-50 dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-200"
      >
        {loading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <RefreshCw className="h-4 w-4" />
        )}
        Reload MCP Servers
      </button>

      {status === "success" && (
        <div className="flex items-center gap-2 text-xs text-emerald-600 dark:text-emerald-400">
          <CheckCircle2 className="h-3 w-3" />
          {message}
        </div>
      )}

      {status === "error" && (
        <div className="flex items-center gap-2 text-xs text-rose-600 dark:text-rose-400">
          <AlertCircle className="h-3 w-3" />
          {message}
        </div>
      )}
    </div>
  );
}
