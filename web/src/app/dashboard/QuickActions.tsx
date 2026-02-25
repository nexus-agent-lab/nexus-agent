"use client";

import { RefreshCw, Trash2, Zap } from "lucide-react";
import { useState } from "react";

export default function QuickActions() {
  const [loading, setLoading] = useState<string | null>(null);

  const handleAction = async (action: string) => {
    setLoading(action);
    // Simulate action
    await new Promise((resolve) => setTimeout(resolve, 1000));
    setLoading(null);
    alert(`${action} completed!`);
  };

  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-6 shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
      <h3 className="mb-4 text-lg font-semibold">Quick Actions</h3>
      <div className="flex flex-wrap gap-4">
        <button
          onClick={() => handleAction("Clear Cache")}
          disabled={loading !== null}
          className="flex items-center gap-2 rounded-lg bg-neutral-100 px-4 py-2 text-sm font-medium transition-colors hover:bg-neutral-200 dark:bg-neutral-800 dark:hover:bg-neutral-700 disabled:opacity-50"
        >
          <Trash2 className="h-4 w-4" />
          {loading === "Clear Cache" ? "Clearing..." : "Clear Cache"}
        </button>
        <button
          onClick={() => handleAction("Run Diagnostics")}
          disabled={loading !== null}
          className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
        >
          <Zap className="h-4 w-4" />
          {loading === "Run Diagnostics" ? "Running..." : "Run Diagnostics"}
        </button>
      </div>
    </div>
  );
}
