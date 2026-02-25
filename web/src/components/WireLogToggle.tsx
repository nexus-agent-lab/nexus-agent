"use client";

import { useState, useEffect } from "react";
import { Terminal, Bug, CheckCircle2, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface WireLogToggleProps {
  apiKey: string;
}

/**
 * A toggle component for controlling the LLM Wire Logging setting.
 * Calls POST /admin/config to update the configuration.
 */
export default function WireLogToggle({ apiKey }: WireLogToggleProps) {
  const [isEnabled, setIsEnabled] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState<"idle" | "success" | "error">("idle");

  const toggleWireLog = async () => {
    setIsLoading(true);
    setStatus("idle");
    const newValue = !isEnabled;
    
    try {
      const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${backendUrl}/admin/config`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": apiKey,
        },
        body: JSON.stringify({
          key: "DEBUG_WIRE_LOG",
          value: newValue ? "true" : "false",
        }),
      });

      if (response.ok) {
        setIsEnabled(newValue);
        setStatus("success");
        setTimeout(() => setStatus("idle"), 3000);
      } else {
        setStatus("error");
      }
    } catch (error) {
      console.error("Failed to update config:", error);
      setStatus("error");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-6 dark:border-neutral-800 dark:bg-neutral-900">
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Bug className="h-5 w-5 text-indigo-500" />
            <h3 className="text-lg font-semibold">LLM Wire Logging</h3>
          </div>
          <p className="text-sm text-neutral-500 dark:text-neutral-400">
            When enabled, all LLM requests and responses are logged to the container logs.
          </p>
        </div>
        <div className="flex items-center gap-4">
          {status === "success" && (
            <span className="flex items-center gap-1 text-xs text-emerald-600">
              <CheckCircle2 className="h-4 w-4" />
              Updated
            </span>
          )}
          {status === "error" && (
            <span className="flex items-center gap-1 text-xs text-rose-600">
              <AlertCircle className="h-4 w-4" />
              Failed
            </span>
          )}
          <button
            onClick={toggleWireLog}
            disabled={isLoading}
            className={cn(
              "relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:ring-offset-2",
              isEnabled ? "bg-indigo-600" : "bg-neutral-200 dark:bg-neutral-700",
              isLoading && "opacity-50 cursor-not-allowed"
            )}
          >
            <span
              className={cn(
                "pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out",
                isEnabled ? "translate-x-5" : "translate-x-0"
              )}
            />
          </button>
        </div>
      </div>
      
      <div className="mt-4 rounded-lg bg-neutral-50 p-3 dark:bg-neutral-800/50">
        <p className="flex items-center gap-2 text-xs font-mono text-neutral-600 dark:text-neutral-400">
          <Terminal className="h-3 w-3" />
          docker-compose logs -f --timestamps nexus-app
        </p>
      </div>
    </div>
  );
}
