"use client";

import { useState, useEffect } from "react";
import { Settings2, Loader2, X, Save, Shield, ExternalLink, Code, Puzzle, Info } from "lucide-react";
import { updatePlugin } from "@/app/actions/plugins";
import { toast } from "@/lib/toast";

interface EditPluginButtonProps {
  apiKey: string;
  plugin: {
    id: number;
    name: string;
    type: string;
    source_url: string;
    required_role: string;
    config: Record<string, any>;
    manifest_id: string | null;
  };
}

export default function EditPluginButton({ plugin, apiKey }: EditPluginButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [schema, setSchema] = useState<any>(null);
  const [installFormValues, setInstallFormValues] = useState<Record<string, string>>({});
  const [fetchingSchema, setFetchingSchema] = useState(false);
  const [formData, setFormData] = useState({
    name: plugin.name,
    type: plugin.type,
    source_url: plugin.source_url,
    required_role: plugin.required_role || "user",
    configStr: JSON.stringify(plugin.config, null, 2),
  });

  useEffect(() => {
    if (isOpen) {
      fetchSchema();
    }
  }, [isOpen]);

  const fetchSchema = async () => {
    setFetchingSchema(true);
    try {
      const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${backendUrl}/plugins/${plugin.id}/schema`, {
        headers: {
          "X-API-Key": apiKey,
        }
      });
      if (response.ok) {
        const data = await response.json();
        setSchema(data);
        
        if (data.env_schema) {
          const initialValues: Record<string, string> = {};
          Object.keys(data.env_schema).forEach(key => {
            const schemaItem = data.env_schema[key];
            if (schemaItem.type === "password") {
              initialValues[key] = "";
            } else {
              initialValues[key] = plugin.config[key] || "";
            }
          });
          setInstallFormValues(initialValues);
        }
      }
    } catch (error) {
      console.error("Failed to fetch schema:", error);
    } finally {
      setFetchingSchema(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      let config = {};
      const secretValues: Record<string, string> = {};

      if (schema?.env_schema) {
        Object.entries(schema.env_schema).forEach(([key, schemaItem]: [string, any]) => {
          const value = installFormValues[key];
          if (schemaItem.type === "password") {
            if (value) {
              secretValues[key] = value;
            }
          } else {
            (config as any)[key] = value;
          }
        });
      } else {
        try {
          config = JSON.parse(formData.configStr);
        } catch (err) {
          throw new Error("Invalid JSON in configuration field");
        }
      }

      const result = await updatePlugin(plugin.id, {
        name: formData.name,
        type: formData.type,
        source_url: formData.source_url,
        required_role: formData.required_role,
        config: config,
        secrets: Object.keys(secretValues).length > 0 ? secretValues : undefined,
      });

      if (result.error) {
        toast.error(result.error);
      } else {
        toast.success("Plugin updated successfully");
        setIsOpen(false);
      }
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  };
  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className="text-neutral-500 hover:text-indigo-600 dark:text-neutral-400 dark:hover:text-indigo-400 transition-colors p-1 rounded-md hover:bg-neutral-100 dark:hover:bg-neutral-800"
        title="Edit Configuration"
      >
        <Settings2 className="h-4 w-4" />
      </button>

      {isOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-2xl bg-white dark:bg-neutral-900 rounded-2xl shadow-2xl border border-neutral-200 dark:border-neutral-800 overflow-hidden animate-in fade-in zoom-in duration-200">
            <div className="flex items-center justify-between p-6 border-b border-neutral-200 dark:border-neutral-800 bg-neutral-50/50 dark:bg-neutral-800/50">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600">
                  <Settings2 className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h2 className="text-xl font-bold">Edit Plugin</h2>
                  <p className="text-xs text-neutral-500">ID: {plugin.id}</p>
                </div>
              </div>
              <button 
                onClick={() => setIsOpen(false)}
                className="p-2 hover:bg-neutral-200 dark:hover:bg-neutral-700 rounded-full transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleSave} className="p-6 space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="md:col-span-2">
                  <label className="mb-2 block text-sm font-bold text-neutral-700 dark:text-neutral-300">Name</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-2 text-sm focus:border-indigo-500 focus:bg-white focus:outline-none dark:border-neutral-700 dark:bg-neutral-800"
                    required
                  />
                </div>

                <div>
                  <label className="mb-2 block text-sm font-bold text-neutral-700 dark:text-neutral-300">Type</label>
                  <select
                    value={formData.type}
                    onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                    className="w-full rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-2 text-sm focus:border-indigo-500 focus:bg-white focus:outline-none dark:border-neutral-700 dark:bg-neutral-800"
                  >
                    <option value="mcp">MCP Server</option>
                    <option value="internal">Internal Plugin</option>
                    <option value="tool">Single Tool</option>
                  </select>
                </div>

                <div>
                  <label className="mb-2 block text-sm font-bold text-neutral-700 dark:text-neutral-300">Access Control</label>
                  <select
                    value={formData.required_role}
                    onChange={(e) => setFormData({ ...formData, required_role: e.target.value })}
                    className="w-full rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-2 text-sm focus:border-indigo-500 focus:bg-white focus:outline-none dark:border-neutral-700 dark:bg-neutral-800"
                  >
                    <option value="user">User Role</option>
                    <option value="admin">Administrator</option>
                    <option value="guest">Guest / Public</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="mb-2 block text-sm font-bold text-neutral-700 dark:text-neutral-300">Source URL</label>
                <input
                  type="text"
                  value={formData.source_url}
                  onChange={(e) => setFormData({ ...formData, source_url: e.target.value })}
                  className="w-full rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-2 text-sm focus:border-indigo-500 focus:bg-white focus:outline-none dark:border-neutral-700 dark:bg-neutral-800"
                  required
                />
              </div>

              {fetchingSchema ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
                </div>
              ) : schema?.env_schema ? (
                <div className="space-y-4 border-t border-neutral-100 dark:border-neutral-800 pt-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Shield className="h-4 w-4 text-indigo-500" />
                    <h3 className="text-sm font-bold uppercase tracking-wider text-neutral-500">Configuration</h3>
                  </div>
                  {Object.entries(schema.env_schema).map(([key, schemaItem]: [string, any]) => (
                    <div key={key}>
                      <label className="mb-1.5 block text-sm font-bold text-neutral-700 dark:text-neutral-300">
                        {schemaItem.label || key} {schemaItem.required && <span className="text-rose-500">*</span>}
                      </label>
                      <input
                        type={schemaItem.type === "password" ? "password" : schemaItem.type === "url" ? "url" : "text"}
                        value={installFormValues[key] || ""}
                        onChange={(e) => setInstallFormValues({ ...installFormValues, [key]: e.target.value })}
                        className="w-full rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-2 text-sm focus:border-indigo-500 focus:bg-white focus:outline-none dark:border-neutral-700 dark:bg-neutral-800"
                        placeholder={schemaItem.type === "password" ? "•••••••• (unchanged unless filled)" : `Enter ${schemaItem.label || key}...`}
                        required={schemaItem.required && schemaItem.type !== "password"}
                      />
                      {schemaItem.description && (
                        <p className="mt-1 text-[11px] text-neutral-500">{schemaItem.description}</p>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div>
                  <label className="mb-2 block text-sm font-bold text-neutral-700 dark:text-neutral-300">Configuration (JSON)</label>
                  <textarea
                    value={formData.configStr}
                    onChange={(e) => setFormData({ ...formData, configStr: e.target.value })}
                    rows={8}
                    className="w-full rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-2 font-mono text-sm focus:border-indigo-500 focus:bg-white focus:outline-none dark:border-neutral-700 dark:bg-neutral-950"
                  />
                </div>
              )}

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setIsOpen(false)}
                  className="flex-1 px-4 py-3 text-sm font-bold rounded-xl border border-neutral-200 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-bold rounded-xl bg-indigo-600 text-white hover:bg-indigo-700 transition-colors disabled:opacity-50"
                >
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
