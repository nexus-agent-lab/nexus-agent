"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createPlugin } from "@/app/actions/plugins";
import { Puzzle, Loader2, AlertCircle, CheckCircle2 } from "lucide-react";

interface PluginFormProps {
  onSuccess?: () => void;
}

export default function PluginForm({ onSuccess }: PluginFormProps) {
  const router = useRouter();
  const [name, setName] = useState("");
  const [type, setType] = useState("mcp");
  const [sourceUrl, setSourceUrl] = useState("");
  const [configStr, setConfigStr] = useState("{}");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      // Validate JSON config
      let config = {};
      try {
        config = JSON.parse(configStr);
      } catch (err) {
        throw new Error("Invalid JSON configuration");
      }

      const result = await createPlugin({
        name,
        type,
        source_url: sourceUrl,
        config,
      });

      if (result.error) {
        throw new Error(result.error);
      }

      setSuccess(true);
      setName("");
      setSourceUrl("");
      setConfigStr("{}");
      onSuccess?.();
      router.refresh();
      
      // Reset success message after 3 seconds
      setTimeout(() => setSuccess(false), 3000);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-6 shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
      <div className="mb-6 flex items-center gap-2">
        <Puzzle className="h-5 w-5 text-indigo-600" />
        <h2 className="text-xl font-semibold">Add New Plugin</h2>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="mb-1 block text-sm font-medium text-neutral-700 dark:text-neutral-300">
            Plugin Name
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full rounded-lg border border-neutral-300 bg-white px-4 py-2 text-sm focus:border-indigo-500 focus:outline-none dark:border-neutral-700 dark:bg-neutral-800"
            placeholder="e.g. File System"
            required
          />
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="mb-1 block text-sm font-medium text-neutral-700 dark:text-neutral-300">
              Type
            </label>
            <select
              value={type}
              onChange={(e) => setType(e.target.value)}
              className="w-full rounded-lg border border-neutral-300 bg-white px-4 py-2 text-sm focus:border-indigo-500 focus:outline-none dark:border-neutral-700 dark:bg-neutral-800"
            >
              <option value="mcp">MCP Server</option>
              <option value="internal">Internal Plugin</option>
              <option value="tool">Single Tool</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-neutral-700 dark:text-neutral-300">
              Status
            </label>
            <select
              disabled
              className="w-full rounded-lg border border-neutral-300 bg-neutral-50 px-4 py-2 text-sm text-neutral-500 dark:border-neutral-700 dark:bg-neutral-800/50"
            >
              <option value="active">Active</option>
            </select>
          </div>
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-neutral-700 dark:text-neutral-300">
            Source URL
          </label>
          <input
            type="text"
            value={sourceUrl}
            onChange={(e) => setSourceUrl(e.target.value)}
            className="w-full rounded-lg border border-neutral-300 bg-white px-4 py-2 text-sm focus:border-indigo-500 focus:outline-none dark:border-neutral-700 dark:bg-neutral-800"
            placeholder="e.g. mcp:https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem"
            required
          />
          <p className="mt-1 text-xs text-neutral-500">
            Format: [protocol]:[url] (e.g., mcp:https://...)
          </p>
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-neutral-700 dark:text-neutral-300">
            Configuration (JSON)
          </label>
          <textarea
            value={configStr}
            onChange={(e) => setConfigStr(e.target.value)}
            className="h-24 w-full rounded-lg border border-neutral-300 bg-white px-4 py-2 font-mono text-sm focus:border-indigo-500 focus:outline-none dark:border-neutral-700 dark:bg-neutral-800"
            placeholder='{ "key": "value" }'
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Puzzle className="h-4 w-4" />
          )}
          Register Plugin
        </button>
      </form>

      {error && (
        <div className="mt-4 flex items-center gap-2 rounded-lg bg-rose-50 p-3 text-sm text-rose-600 dark:bg-rose-900/20 dark:text-rose-400">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      )}

      {success && (
        <div className="mt-4 flex items-center gap-2 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-600 dark:bg-emerald-900/20 dark:text-emerald-400">
          <CheckCircle2 className="h-4 w-4" />
          Plugin registered successfully!
        </div>
      )}
    </div>
  );
}
