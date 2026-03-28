"use client";

import { useMemo, useState } from "react";
import { BookOpen, X, Loader2, FileText, Info, Save, Sparkles, ListChecks } from "lucide-react";
import { getClientApiBase } from "@/lib/client-api";
import { toast } from "@/lib/toast";

interface SkillMetadata {
  description?: string;
  domain?: string;
  routing_examples?: string[];
}

interface ViewSkillButtonProps {
  pluginId: number;
  token: string;
}

function normalizeExamples(raw: string): string[] {
  return raw
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

export default function ViewSkillButton({ pluginId, token }: ViewSkillButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [applying, setApplying] = useState(false);
  const [content, setContent] = useState<string>("");
  const [skillName, setSkillName] = useState<string>("");
  const [metadata, setMetadata] = useState<SkillMetadata>({});
  const [generatedExamples, setGeneratedExamples] = useState<string[]>([]);
  const [examplesDraft, setExamplesDraft] = useState("");

  const currentExamples = useMemo(() => metadata.routing_examples || [], [metadata.routing_examples]);

  const fetchSkill = async () => {
    setLoading(true);
    try {
      const backendUrl = getClientApiBase();
      const response = await fetch(`${backendUrl}/plugins/${pluginId}/skill`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setContent(data.content || "");
        setSkillName(data.skill_name || "");
        setMetadata(data.metadata || {});
        setExamplesDraft(((data.metadata?.routing_examples || []) as string[]).join("\n"));
        setGeneratedExamples([]);
      } else {
        const data = await response.json();
        toast.error(data.detail || "Failed to load skill content");
        setIsOpen(false);
      }
    } catch (error) {
      console.error("Failed to fetch skill:", error);
      toast.error("Failed to connect to backend");
      setIsOpen(false);
    } finally {
      setLoading(false);
    }
  };

  const handleOpen = () => {
    setIsOpen(true);
    void fetchSkill();
  };

  const saveSkill = async () => {
    if (!skillName) return;
    setSaving(true);
    try {
      const backendUrl = getClientApiBase();
      const response = await fetch(`${backendUrl}/skills/${skillName}`, {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ content }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Failed to save skill");
      }

      toast.success("Skill saved successfully");
      await fetchSkill();
    } catch (error) {
      console.error("Failed to save skill:", error);
      toast.error(error instanceof Error ? error.message : "Failed to save skill");
    } finally {
      setSaving(false);
    }
  };

  const generateExamples = async () => {
    if (!skillName) return;
    setGenerating(true);
    try {
      const backendUrl = getClientApiBase();
      const response = await fetch(`${backendUrl}/skills/generate-routing-examples`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          skill_name: skillName,
          description: metadata.description || "",
          domain: metadata.domain || "unknown",
          tools: [],
          constraints: ["Generate examples for semantic routing only."],
          count: 12,
        }),
      });

      const data = await response.json();
      if (!response.ok || !data.success) {
        throw new Error(data.message || data.detail || "Failed to generate routing examples");
      }

      setGeneratedExamples(data.examples || []);
      toast.success("Routing examples generated");
    } catch (error) {
      console.error("Failed to generate routing examples:", error);
      toast.error(error instanceof Error ? error.message : "Failed to generate routing examples");
    } finally {
      setGenerating(false);
    }
  };

  const applyExamples = async () => {
    if (!skillName) return;
    const examples = normalizeExamples(examplesDraft);
    setApplying(true);
    try {
      const backendUrl = getClientApiBase();
      const response = await fetch(`${backendUrl}/skills/${skillName}/routing-examples`, {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ examples }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Failed to update routing examples");
      }

      setMetadata((current) => ({
        ...current,
        routing_examples: examples,
      }));
      setGeneratedExamples([]);
      toast.success("Routing examples updated");
      await fetchSkill();
    } catch (error) {
      console.error("Failed to apply routing examples:", error);
      toast.error(error instanceof Error ? error.message : "Failed to apply routing examples");
    } finally {
      setApplying(false);
    }
  };

  const useGeneratedExamples = () => {
    setExamplesDraft(generatedExamples.join("\n"));
  };

  return (
    <>
      <button
        onClick={handleOpen}
        className="text-neutral-500 hover:text-indigo-600 dark:text-neutral-400 dark:hover:text-indigo-400 transition-colors p-1 rounded-md hover:bg-neutral-100 dark:hover:bg-neutral-800"
        title="View Associated Skill"
      >
        <BookOpen className="h-4 w-4" />
      </button>

      {isOpen && (
        <div className="fixed inset-0 z-[100] flex justify-end bg-black/60 backdrop-blur-sm animate-in fade-in duration-300">
          <div className="w-full max-w-3xl bg-white dark:bg-neutral-900 h-full shadow-2xl border-l border-neutral-200 dark:border-neutral-800 flex flex-col animate-in slide-in-from-right duration-300">
            <div className="flex items-center justify-between p-6 border-b border-neutral-200 dark:border-neutral-800 bg-neutral-50/50 dark:bg-neutral-800/50">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600">
                  <BookOpen className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h2 className="text-xl font-bold">Skill Description</h2>
                  <p className="text-xs text-neutral-500">
                    {skillName ? `Skill: ${skillName}` : "Agent Instruction Manual"}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="p-2 hover:bg-neutral-200 dark:hover:bg-neutral-700 rounded-full transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {loading ? (
                <div className="flex flex-col items-center justify-center h-full gap-4 text-neutral-400">
                  <Loader2 className="h-10 w-10 animate-spin" />
                  <p className="text-sm font-medium">Reading skill file...</p>
                </div>
              ) : skillName ? (
                <>
                  <div className="rounded-2xl border border-neutral-200 bg-neutral-50 p-4 dark:border-neutral-800 dark:bg-neutral-950">
                    <div className="flex items-center gap-2 text-indigo-500 mb-3">
                      <Info className="h-4 w-4" />
                      <span className="text-xs font-bold uppercase tracking-widest">Routing Notes</span>
                    </div>
                    <p className="text-sm text-neutral-600 dark:text-neutral-300">
                      `routing_examples` only affect semantic routing and do not get injected into the LLM prompt.
                    </p>
                  </div>

                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-indigo-500">
                        <ListChecks className="h-4 w-4" />
                        <span className="text-xs font-bold uppercase tracking-widest">Routing Examples</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={generateExamples}
                          disabled={generating}
                          className="inline-flex items-center gap-2 rounded-xl bg-amber-500 px-3 py-2 text-xs font-semibold text-white hover:bg-amber-400 disabled:opacity-60"
                        >
                          {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                          Generate Samples
                        </button>
                        <button
                          type="button"
                          onClick={applyExamples}
                          disabled={applying}
                          className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-500 disabled:opacity-60"
                        >
                          {applying ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                          Apply Samples
                        </button>
                      </div>
                    </div>

                    <textarea
                      value={examplesDraft}
                      onChange={(e) => setExamplesDraft(e.target.value)}
                      rows={8}
                      className="w-full rounded-2xl border border-neutral-200 bg-white px-4 py-3 font-mono text-sm outline-none transition focus:border-indigo-500 dark:border-neutral-800 dark:bg-neutral-950"
                      placeholder="One routing example per line"
                    />

                    {currentExamples.length > 0 ? (
                      <p className="text-xs text-neutral-500">
                        Current saved examples: {currentExamples.length}
                      </p>
                    ) : null}

                    {generatedExamples.length > 0 ? (
                      <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-900/50 dark:bg-amber-950/30">
                        <div className="mb-3 flex items-center justify-between gap-3">
                          <span className="text-sm font-semibold text-amber-800 dark:text-amber-300">
                            Generated candidates
                          </span>
                          <button
                            type="button"
                            onClick={useGeneratedExamples}
                            className="rounded-lg bg-amber-500 px-3 py-1.5 text-xs font-semibold text-white hover:bg-amber-400"
                          >
                            Use Generated
                          </button>
                        </div>
                        <div className="space-y-2 text-sm text-amber-900 dark:text-amber-100">
                          {generatedExamples.map((example) => (
                            <div key={example} className="rounded-xl bg-white/70 px-3 py-2 dark:bg-neutral-900/50">
                              {example}
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : null}
                  </div>

                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-indigo-500">
                        <FileText className="h-4 w-4" />
                        <span className="text-xs font-bold uppercase tracking-widest">Markdown Content</span>
                      </div>
                      <button
                        type="button"
                        onClick={saveSkill}
                        disabled={saving}
                        className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-3 py-2 text-xs font-semibold text-white hover:bg-indigo-500 disabled:opacity-60"
                      >
                        {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                        Save Skill
                      </button>
                    </div>
                    <textarea
                      value={content}
                      onChange={(e) => setContent(e.target.value)}
                      rows={22}
                      className="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 font-mono text-sm outline-none transition focus:border-indigo-500 focus:bg-white dark:border-neutral-800 dark:bg-neutral-950"
                    />
                  </div>
                </>
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-neutral-500">
                  <Info className="h-12 w-12 mb-4 opacity-20" />
                  <p>No skill content found.</p>
                </div>
              )}
            </div>

            <div className="p-6 border-t border-neutral-200 dark:border-neutral-800 bg-neutral-50/50 dark:bg-neutral-800/50 text-center">
              <p className="text-xs text-neutral-400">
                Skill rules are injected into the agent only when routing selects this capability.
              </p>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
