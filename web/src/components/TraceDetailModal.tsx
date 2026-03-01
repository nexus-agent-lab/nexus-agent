"use client";

import React, { useState } from "react";
import { X, Clock, Cpu, Terminal, ChevronRight, Activity, Calendar, Hash, MessageSquare, Info } from "lucide-react";
import { cn } from "@/lib/utils";

export interface TraceStep {
  id: number;
  trace_id: string;
  session_id: string;
  user_id: number | null;
  model: string;
  phase: string;
  prompt_summary: string | null;
  response_summary: string | null;
  latency_ms: number | null;
  tools_bound: string[] | null;
  tool_calls: any[] | null;
  created_at: string;
}

export interface GroupedTrace {
  trace_id: string;
  session_id: string;
  user_id: number | null;
  total_latency_ms: number;
  call_count: number;
  created_at: string;
  steps: TraceStep[];
}

interface TraceDetailModalProps {
  trace: GroupedTrace | null;
  onClose: () => void;
}

const TraceDetailModal: React.FC<TraceDetailModalProps> = ({ trace, onClose }) => {
  const [showFullPrompt, setShowFullPrompt] = useState<Record<number, boolean>>({});

  if (!trace) return null;

  const togglePrompt = (id: number) => {
    setShowFullPrompt((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-neutral-900/40 backdrop-blur-sm transition-opacity duration-300">
      <div className="bg-white dark:bg-neutral-900 w-full max-w-4xl max-h-[90vh] rounded-2xl shadow-2xl border border-neutral-200 dark:border-neutral-800 overflow-hidden flex flex-col transform transition-all duration-300 scale-100">
        {/* Header */}
        <div className="px-6 py-4 border-b border-neutral-100 dark:border-neutral-800 flex items-center justify-between bg-neutral-50/50 dark:bg-neutral-800/30">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-100 dark:bg-indigo-900/30 rounded-lg">
              <Activity className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-100">Trace Deep-Dive</h2>
              <div className="flex items-center gap-4 text-xs text-neutral-500 mt-1">
                <span className="flex items-center gap-1"><Hash className="h-3 w-3" /> {trace.trace_id.slice(0, 8)}...</span>
                <span className="flex items-center gap-1"><Calendar className="h-3 w-3" /> {new Date(trace.created_at).toLocaleString()}</span>
              </div>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-2 rounded-full hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
          >
            <X className="h-5 w-5 text-neutral-400" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-8 custom-scrollbar">
          {/* Summary Stats */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl bg-neutral-50 dark:bg-neutral-800/50 border border-neutral-100 dark:border-neutral-800">
              <span className="text-[10px] uppercase tracking-wider text-neutral-400 font-bold block mb-1">Total Latency</span>
              <div className="flex items-baseline gap-1">
                <span className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">{(trace.total_latency_ms / 1000).toFixed(2)}</span>
                <span className="text-xs text-neutral-500">seconds</span>
              </div>
            </div>
            <div className="p-4 rounded-xl bg-neutral-50 dark:bg-neutral-800/50 border border-neutral-100 dark:border-neutral-800">
              <span className="text-[10px] uppercase tracking-wider text-neutral-400 font-bold block mb-1">Call Count</span>
              <div className="flex items-baseline gap-1">
                <span className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">{trace.call_count}</span>
                <span className="text-xs text-neutral-500">steps</span>
              </div>
            </div>
            <div className="p-4 rounded-xl bg-neutral-50 dark:bg-neutral-800/50 border border-neutral-100 dark:border-neutral-800">
              <span className="text-[10px] uppercase tracking-wider text-neutral-400 font-bold block mb-1">Session ID</span>
              <span className="text-sm font-mono text-neutral-600 dark:text-neutral-400 truncate block mt-1">{trace.session_id.slice(0, 12)}...</span>
            </div>
            <div className="p-4 rounded-xl bg-neutral-50 dark:bg-neutral-800/50 border border-neutral-100 dark:border-neutral-800">
              <span className="text-[10px] uppercase tracking-wider text-neutral-400 font-bold block mb-1">User</span>
              <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100 block mt-1">{trace.user_id ? `User #${trace.user_id}` : 'System'}</span>
            </div>
          </div>

          {/* Timeline of steps */}
          <div className="space-y-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-neutral-400 flex items-center gap-2">
              <Clock className="h-4 w-4" />
              Execution Timeline
            </h3>
            
            <div className="space-y-4 relative before:absolute before:left-3.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-neutral-100 dark:before:bg-neutral-800">
              {trace.steps.map((step, idx) => (
                <div key={step.id} className="relative pl-10 group">
                  {/* Timeline dot */}
                  <div className="absolute left-0 top-1.5 w-7 h-7 rounded-full bg-white dark:bg-neutral-900 border-2 border-indigo-500 z-10 flex items-center justify-center text-[10px] font-bold text-indigo-600 shadow-sm">
                    {idx + 1}
                  </div>
                  
                  <div className="bg-white dark:bg-neutral-800/30 rounded-xl border border-neutral-200 dark:border-neutral-800 overflow-hidden transition-all hover:border-indigo-200 dark:hover:border-indigo-900/50">
                    <div className="px-4 py-3 bg-neutral-50/50 dark:bg-neutral-800/50 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className="text-xs font-bold text-neutral-900 dark:text-neutral-100 uppercase tracking-tight">{step.phase}</span>
                        <div className="flex items-center gap-1.5 px-2 py-0.5 bg-neutral-100 dark:bg-neutral-700 rounded text-[10px] font-medium text-neutral-600 dark:text-neutral-300">
                          <Cpu className="h-2.5 w-2.5" />
                          {step.model}
                        </div>
                      </div>
                      <div className={cn(
                        "text-[10px] font-mono font-bold px-2 py-0.5 rounded-full",
                        (step.latency_ms || 0) < 1000 ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-400" : "bg-amber-100 text-amber-700 dark:bg-amber-950/30 dark:text-amber-400"
                      )}>
                        {step.latency_ms ? `${step.latency_ms}ms` : 'N/A'}
                      </div>
                    </div>
                    
                    <div className="p-4 space-y-4">
                      {/* Prompt Summary */}
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-bold text-neutral-400 uppercase flex items-center gap-1">
                            <MessageSquare className="h-3 w-3" /> Prompt Summary
                          </span>
                        </div>
                        <div className="relative">
                          <p className={cn(
                            "text-xs leading-relaxed text-neutral-600 dark:text-neutral-400 bg-neutral-50 dark:bg-neutral-900/50 p-3 rounded-lg border border-neutral-100 dark:border-neutral-800 whitespace-pre-wrap",
                            !showFullPrompt[step.id] && "line-clamp-3"
                          )}>
                            {step.prompt_summary || "No prompt content available."}
                          </p>
                          {(step.prompt_summary?.length || 0) > 150 && (
                            <button 
                              onClick={() => togglePrompt(step.id)}
                              className="mt-2 text-[10px] font-bold text-indigo-600 hover:text-indigo-500 transition-colors flex items-center gap-0.5"
                            >
                              {showFullPrompt[step.id] ? "Show Less" : "Show More"}
                              <ChevronRight className={cn("h-3 w-3 transition-transform", showFullPrompt[step.id] && "rotate-90")} />
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Response Summary (Optional) */}
                      {step.response_summary && (
                        <div className="space-y-2">
                          <span className="text-[10px] font-bold text-neutral-400 uppercase flex items-center gap-1">
                            <Info className="h-3 w-3" /> Response
                          </span>
                          <p className="text-xs leading-relaxed text-neutral-600 dark:text-neutral-400 italic">
                            {step.response_summary}
                          </p>
                        </div>
                      )}

                      {/* Tools bound */}
                      {step.tools_bound && step.tools_bound.length > 0 && (
                        <div className="space-y-2">
                          <span className="text-[10px] font-bold text-neutral-400 uppercase flex items-center gap-1">
                            <Terminal className="h-3 w-3" /> Tools Context
                          </span>
                          <div className="flex flex-wrap gap-1.5">
                            {step.tools_bound.map(tool => (
                              <span key={tool} className="px-2 py-0.5 bg-neutral-100 dark:bg-neutral-800 rounded text-[10px] font-mono text-neutral-500 border border-neutral-200 dark:border-neutral-700">
                                {tool}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-neutral-100 dark:border-neutral-800 flex justify-end bg-neutral-50/50 dark:bg-neutral-800/30">
          <button 
            onClick={onClose}
            className="px-4 py-2 bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 rounded-lg text-sm font-bold hover:opacity-90 transition-opacity"
          >
            Close Trace
          </button>
        </div>
      </div>
      
      <style jsx>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #e5e7eb;
          border-radius: 10px;
        }
        .dark .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #374151;
        }
      `}</style>
    </div>
  );
};

export default TraceDetailModal;
