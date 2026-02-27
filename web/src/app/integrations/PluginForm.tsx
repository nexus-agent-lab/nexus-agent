"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { createPlugin } from "@/app/actions/plugins";
import { Puzzle, Loader2, AlertCircle, CheckCircle2, Store, Wrench, Shield, Plus, Info, ExternalLink, ArrowRight, Code } from "lucide-react";
import { toast } from "@/lib/toast";

interface PluginFormProps {
  apiKey: string;
  onSuccess?: () => void;
}

export default function PluginForm({ apiKey, onSuccess }: PluginFormProps) {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<"store" | "custom">("store");
  const [name, setName] = useState("");
  const [type, setType] = useState("mcp");
  const [sourceUrl, setSourceUrl] = useState("");
  const [configStr, setConfigStr] = useState("{}");
  const [requiredRole, setRequiredRole] = useState("user");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [catalog, setCatalog] = useState<any[]>([]);
  const [loadingCatalog, setLoadingCatalog] = useState(false);
  const [catalogLoaded, setCatalogLoaded] = useState(false);

  useEffect(() => {
    if (activeTab === "store" && !catalogLoaded) {
      fetchCatalog();
    }
  }, [activeTab, catalogLoaded]);

  const fetchCatalog = async () => {
    setLoadingCatalog(true);
    try {
      const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${backendUrl}/plugins/catalog`, {
        headers: {
          "X-API-Key": apiKey,
        }
      });
      if (response.ok) {
        const data = await response.json();
        setCatalog(data);
      } else if (response.status === 401) {
        toast.error("Unauthorized: Session might have expired. Please log in again.");
      } else {
        toast.error(`Failed to load catalog: ${response.statusText}`);
      }
    } catch (error) {
      console.error("Failed to fetch plugin catalog:", error);
      toast.error("Failed to connect to plugin registry.");
    } finally {
      setLoadingCatalog(false);
      setCatalogLoaded(true);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
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
        required_role: requiredRole,
      });

      if (result.error) {
        toast.error(result.error);
        throw new Error(result.error);
      }

      setSuccess(true);
      toast.success("Plugin registered successfully!");
      setName("");
      setSourceUrl("");
      setConfigStr("{}");
      onSuccess?.();
      router.refresh();
      setTimeout(() => setSuccess(false), 3000);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleInstallFromStore = async (item: any) => {
    setLoading(true);
    setError(null);
    setSuccess(false);
    try {
      const result = await createPlugin({
        name: item.name,
        type: item.type,
        source_url: item.source_url,
        manifest_id: item.id,
        required_role: item.required_role || "user",
        config: item.config || {},
      });
      if (result.error) {
        toast.error(result.error);
        throw new Error(result.error);
      }
      setSuccess(true);
      toast.success(`${item.name} installed successfully!`);
      onSuccess?.();
      router.refresh();
      setTimeout(() => setSuccess(false), 3000);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-2xl border border-neutral-200 bg-white p-6 shadow-sm transition-all dark:border-neutral-800 dark:bg-neutral-900/50 dark:backdrop-blur-xl">
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 shadow-lg shadow-indigo-500/20">
            <Puzzle className="h-6 w-6 text-white" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-neutral-900 dark:text-white">Plugin Engine</h2>
            <p className="text-sm text-neutral-500">Expand your agent's capabilities</p>
          </div>
        </div>
        
        <div className="inline-flex items-center rounded-xl bg-neutral-100 p-1.5 dark:bg-neutral-800">
          <button
            onClick={() => setActiveTab("store")}
            type="button"
            className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition-all duration-200 ${
              activeTab === "store" 
                ? "bg-white text-indigo-600 shadow-sm dark:bg-neutral-700 dark:text-indigo-400" 
                : "text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200"
            }`}
          >
            <Store className="h-4 w-4" />
            Store
          </button>
          <button
            onClick={() => setActiveTab("custom")}
            type="button"
            className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition-all duration-200 ${
              activeTab === "custom" 
                ? "bg-white text-indigo-600 shadow-sm dark:bg-neutral-700 dark:text-indigo-400" 
                : "text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200"
            }`}
          >
            <Wrench className="h-4 w-4" />
            Custom
          </button>
        </div>
      </div>

      {activeTab === "store" ? (
        <div className="space-y-6">
          {loadingCatalog ? (
            <div className="flex flex-col items-center justify-center py-12">
              <Loader2 className="h-10 w-10 animate-spin text-indigo-600/50" />
              <p className="mt-4 text-sm font-medium text-neutral-500">Synchronizing catalog...</p>
            </div>
          ) : catalog.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-neutral-200 py-12 text-center dark:border-neutral-800">
              <Info className="mb-3 h-10 w-10 text-neutral-300" />
              <p className="text-neutral-500 text-sm">The plugin store is currently empty.</p>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
              {catalog.map((item) => (
                <div 
                  key={item.id} 
                  className="group flex flex-col justify-between rounded-2xl border border-neutral-200 bg-neutral-50/50 p-5 transition-all duration-300 hover:border-indigo-500/50 hover:bg-white hover:shadow-xl hover:shadow-indigo-500/5 dark:border-neutral-800 dark:bg-neutral-800/50 dark:hover:bg-neutral-800"
                >
                  <div className="flex items-start gap-4">
                    <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-white text-2xl shadow-sm dark:bg-neutral-700">
                      {item.icon || "🧩"}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="truncate font-bold text-neutral-900 dark:text-white">{item.name}</h3>
                        <span className="rounded-full bg-neutral-200/50 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-neutral-600 dark:bg-neutral-700 dark:text-neutral-400">
                          {item.type}
                        </span>
                      </div>
                      <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-neutral-500 dark:text-neutral-400">{item.description}</p>
                    </div>
                  </div>
                  
                  <div className="mt-6 flex items-center justify-between border-t border-neutral-200/50 pt-4 dark:border-neutral-700/50">
                    <div className="flex items-center gap-1.5 text-xs font-medium text-neutral-400">
                      <Shield className="h-3.5 w-3.5" />
                      {item.required_role || "User"}
                    </div>
                    <button
                      onClick={() => handleInstallFromStore(item)}
                      disabled={loading}
                      type="button"
                      className="flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-bold text-white shadow-md shadow-indigo-600/20 transition-all hover:bg-indigo-700 hover:shadow-indigo-600/40 active:scale-95 disabled:opacity-50"
                    >
                      {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : (
                        <>
                          <Plus className="h-3.5 w-3.5" />
                          Install
                        </>
                      )}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            <div className="md:col-span-2">
              <label className="mb-2 flex items-center gap-2 text-sm font-bold text-neutral-700 dark:text-neutral-300">
                <Puzzle className="h-4 w-4 text-indigo-500" />
                Plugin Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm font-medium transition-all focus:border-indigo-500 focus:bg-white focus:outline-none dark:border-neutral-700 dark:bg-neutral-800 dark:focus:border-indigo-500"
                placeholder="e.g. Weather Service"
                required
              />
            </div>

            <div>
              <label className="mb-2 flex items-center gap-2 text-sm font-bold text-neutral-700 dark:text-neutral-300">
                <Wrench className="h-4 w-4 text-indigo-500" />
                Protocol / Type
              </label>
              <select
                value={type}
                onChange={(e) => setType(e.target.value)}
                className="w-full rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm font-medium transition-all focus:border-indigo-500 focus:bg-white focus:outline-none dark:border-neutral-700 dark:bg-neutral-800"
              >
                <option value="mcp">MCP Server</option>
                <option value="internal">Internal Plugin</option>
                <option value="tool">Single Tool</option>
              </select>
            </div>

            <div>
              <label className="mb-2 flex items-center gap-2 text-sm font-bold text-neutral-700 dark:text-neutral-300">
                <Shield className="h-4 w-4 text-indigo-500" />
                Access Control
              </label>
              <select
                value={requiredRole}
                onChange={(e) => setRequiredRole(e.target.value)}
                className="w-full rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm font-medium transition-all focus:border-indigo-500 focus:bg-white focus:outline-none dark:border-neutral-700 dark:bg-neutral-800"
              >
                <option value="user">User Role</option>
                <option value="admin">Administrator</option>
                <option value="guest">Guest / Public</option>
              </select>
            </div>
          </div>

          <div>
            <label className="mb-2 flex items-center gap-2 text-sm font-bold text-neutral-700 dark:text-neutral-300">
              <ExternalLink className="h-4 w-4 text-indigo-500" />
              Source Endpoint / URL
            </label>
            <input
              type="text"
              value={sourceUrl}
              onChange={(e) => setSourceUrl(e.target.value)}
              className="w-full rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm font-medium transition-all focus:border-indigo-500 focus:bg-white focus:outline-none dark:border-neutral-700 dark:bg-neutral-800"
              placeholder="mcp:https://..."
              required
            />
            <p className="mt-2 flex items-center gap-1.5 text-[11px] font-medium text-neutral-400">
              <Info className="h-3 w-3" />
              Requires protocol prefix: mcp:, internal:, or tool:
            </p>
          </div>

          <div>
            <label className="mb-2 flex items-center gap-2 text-sm font-bold text-neutral-700 dark:text-neutral-300">
              <Code className="h-4 w-4 text-indigo-500" />
              Configuration Parameter (JSON)
            </label>
            <textarea
              value={configStr}
              onChange={(e) => setConfigStr(e.target.value)}
              className="h-32 w-full rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3 font-mono text-sm font-medium transition-all focus:border-indigo-500 focus:bg-white focus:outline-none dark:border-neutral-700 dark:bg-neutral-800"
              placeholder='{ "api_key": "..." }'
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="group flex w-full items-center justify-center gap-3 rounded-xl bg-indigo-600 py-4 text-sm font-bold text-white shadow-lg shadow-indigo-600/20 transition-all hover:bg-indigo-700 hover:shadow-indigo-600/40 active:scale-[0.98] disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <>
                <Plus className="h-5 w-5" />
                <span>Register Custom Plugin</span>
                <ArrowRight className="ml-1 h-4 w-4 transition-transform group-hover:translate-x-1" />
              </>
            )}
          </button>
        </form>
      )}

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
