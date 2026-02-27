"use client";

import { useState } from "react";
import { BookOpen, X, Loader2, FileText, Info } from "lucide-react";
import { toast } from "@/lib/toast";

interface ViewSkillButtonProps {
  pluginId: number;
  apiKey: string;
}

export default function ViewSkillButton({ pluginId, apiKey }: ViewSkillButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [content, setContent] = useState<string | null>(null);

  const fetchSkill = async () => {
    setLoading(true);
    try {
      const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${backendUrl}/plugins/${pluginId}/skill`, {
        headers: {
          "X-API-Key": apiKey,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setContent(data.content);
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
    fetchSkill();
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
          <div className="w-full max-w-2xl bg-white dark:bg-neutral-900 h-full shadow-2xl border-l border-neutral-200 dark:border-neutral-800 flex flex-col animate-in slide-in-from-right duration-300">
            <div className="flex items-center justify-between p-6 border-b border-neutral-200 dark:border-neutral-800 bg-neutral-50/50 dark:bg-neutral-800/50">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600">
                  <BookOpen className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h2 className="text-xl font-bold">Skill Description</h2>
                  <p className="text-xs text-neutral-500">Agent Instruction Manual</p>
                </div>
              </div>
              <button 
                onClick={() => setIsOpen(false)}
                className="p-2 hover:bg-neutral-200 dark:hover:bg-neutral-700 rounded-full transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-8">
              {loading ? (
                <div className="flex flex-col items-center justify-center h-full gap-4 text-neutral-400">
                  <Loader2 className="h-10 w-10 animate-spin" />
                  <p className="text-sm font-medium">Reading skill file...</p>
                </div>
              ) : content ? (
                <div className="space-y-6">
                  <div className="flex items-center gap-2 text-indigo-500 mb-4">
                    <FileText className="h-4 w-4" />
                    <span className="text-xs font-bold uppercase tracking-widest">Markdown Content</span>
                  </div>
                  <pre className="text-sm font-mono whitespace-pre-wrap bg-neutral-50 dark:bg-neutral-950 p-6 rounded-2xl border border-neutral-200 dark:border-neutral-800 text-neutral-800 dark:text-neutral-300 leading-relaxed">
                    {content}
                  </pre>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-neutral-500">
                  <Info className="h-12 w-12 mb-4 opacity-20" />
                  <p>No skill content found.</p>
                </div>
              )}
            </div>

            <div className="p-6 border-t border-neutral-200 dark:border-neutral-800 bg-neutral-50/50 dark:bg-neutral-800/50 text-center">
              <p className="text-xs text-neutral-400">
                These rules are automatically injected into the Agent's system prompt when this plugin is relevant.
              </p>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
