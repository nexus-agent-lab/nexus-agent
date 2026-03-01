"use client";

import { useState } from "react";
import { Trash2, ChevronDown, ChevronUp, Loader2, Info } from "lucide-react";
import { deleteMemory } from "@/app/actions/memories";
import { toast } from "@/lib/toast";
import { cn } from "@/lib/utils";

interface MemoryActionsProps {
  id: number;
  content: string;
  type: string;
}

export default function MemoryActions({ id, content, type }: MemoryActionsProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleDelete = async () => {
    if (!confirm("Are you sure you want to delete this memory? This action cannot be undone.")) {
      return;
    }

    setLoading(true);
    try {
      const result = await deleteMemory(id);
      if (result?.error) {
        toast.error(result.error);
      } else {
        toast.success("Memory deleted successfully");
      }
    } catch (error) {
      toast.error("Failed to delete memory");
    } finally {
      setLoading(false);
    }
  };

  const isRoutingLesson = content.includes("ROUTING LESSON:");

  return (
    <div className="flex flex-col gap-2 py-1">
      <div className="flex items-center justify-between gap-4">
        <div 
          className={cn(
            "max-w-md cursor-pointer transition-all hover:opacity-80",
            !isExpanded && "overflow-hidden text-ellipsis whitespace-nowrap",
            isExpanded && "whitespace-pre-wrap leading-relaxed bg-neutral-50 dark:bg-neutral-900 p-3 rounded-lg border border-neutral-100 dark:border-neutral-800 text-xs font-mono",
            isRoutingLesson && !isExpanded && "text-indigo-600 dark:text-indigo-400 font-semibold"
          )}
          onClick={() => setIsExpanded(!isExpanded)}
        >
          {isRoutingLesson && !isExpanded && (
            <span className="mr-2 inline-flex items-center gap-1 rounded bg-indigo-50 px-1.5 py-0.5 text-[10px] uppercase dark:bg-indigo-900/30">
              <Info className="h-3 w-3" />
              Lesson
            </span>
          )}
          {content}
        </div>

        <div className="flex shrink-0 items-center gap-1">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1.5 text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-md transition-colors"
            title={isExpanded ? "Collapse" : "Expand"}
          >
            {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>
          
          <button
            onClick={handleDelete}
            disabled={loading}
            className="p-1.5 text-neutral-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-900/20 rounded-md transition-colors disabled:opacity-50"
            title="Delete Memory"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
          </button>
        </div>
      </div>
    </div>
  );
}
