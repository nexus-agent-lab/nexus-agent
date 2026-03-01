"use client";

import React, { useState } from "react";
import { Activity, Clock, Cpu, Info, Search, Terminal, ChevronRight, Hash, User, MessageSquare } from "lucide-react";
import { cn } from "@/lib/utils";
import TraceDetailModal, { GroupedTrace } from "@/components/TraceDetailModal";

interface TraceViewerProps {
  initialTraces: GroupedTrace[];
}

const TraceViewer: React.FC<TraceViewerProps> = ({ initialTraces }) => {
  const [selectedTrace, setSelectedTrace] = useState<GroupedTrace | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const filteredTraces = initialTraces.filter((trace) => 
    trace.trace_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
    trace.session_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
    trace.steps.some(step => step.prompt_summary?.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <section className="space-y-6">
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        <h2 className="text-xl font-bold flex items-center gap-2 text-neutral-900 dark:text-neutral-100">
          <Activity className="h-5 w-5 text-indigo-500" />
          Execution Traces
        </h2>
        
        <div className="relative w-full sm:w-64">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400" />
          <input
            type="text"
            placeholder="Search traces..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-neutral-100 dark:bg-neutral-800 border-none rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none placeholder:text-neutral-500 transition-all"
          />
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {filteredTraces.length === 0 ? (
          <div className="col-span-full rounded-2xl border border-dashed border-neutral-200 dark:border-neutral-800 p-12 text-center bg-neutral-50/50 dark:bg-neutral-900/30">
            <div className="mx-auto h-12 w-12 rounded-full bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center mb-4">
              <Info className="h-6 w-6 text-neutral-300 dark:text-neutral-600" />
            </div>
            <p className="text-sm font-medium text-neutral-500">
              No traces found matching your query.
            </p>
          </div>
        ) : (
          filteredTraces.map((trace) => (
            <div 
              key={trace.trace_id} 
              onClick={() => setSelectedTrace(trace)}
              className="group cursor-pointer relative rounded-2xl border border-neutral-200 bg-white p-5 transition-all hover:border-indigo-200 hover:shadow-lg dark:border-neutral-800 dark:bg-neutral-900/50 hover:scale-[1.01] active:scale-[0.99]"
            >
              <div className="mb-4 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 bg-neutral-100 dark:bg-neutral-800 rounded-lg group-hover:bg-indigo-50 dark:group-hover:bg-indigo-900/20 transition-colors">
                    <Hash className="h-3.5 w-3.5 text-neutral-500 group-hover:text-indigo-500" />
                  </div>
                  <span className="text-[10px] font-mono font-bold text-neutral-400 group-hover:text-indigo-400 transition-colors">
                    {trace.trace_id.slice(0, 8)}
                  </span>
                </div>
                
                <div className={cn(
                  "flex items-center gap-1.5 rounded-full px-3 py-1 text-[11px] font-bold shadow-sm",
                  trace.total_latency_ms < 2000 
                    ? "bg-emerald-50 text-emerald-600 dark:bg-emerald-900/20 dark:text-emerald-400" 
                    : trace.total_latency_ms < 5000 
                      ? "bg-amber-50 text-amber-600 dark:bg-amber-900/20 dark:text-amber-400" 
                      : "bg-rose-50 text-rose-600 dark:bg-rose-900/20 dark:text-rose-400"
                )}>
                  <Clock className="h-3 w-3" />
                  {(trace.total_latency_ms / 1000).toFixed(2)}s
                </div>
              </div>
              
              <div className="space-y-3">
                <div className="flex items-center gap-4 text-xs">
                  <div className="flex items-center gap-1.5 text-neutral-500">
                    <Activity className="h-3.5 w-3.5" />
                    <span className="font-bold text-neutral-700 dark:text-neutral-300">{trace.call_count} calls</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-neutral-500">
                    <User className="h-3.5 w-3.5" />
                    <span className="font-medium text-neutral-600 dark:text-neutral-400 truncate max-w-[100px]">
                      {trace.user_id ? `#${trace.user_id}` : 'System'}
                    </span>
                  </div>
                </div>

                <div className="relative group/prompt">
                  <div className="absolute -left-2 top-0 bottom-0 w-0.5 bg-indigo-500/0 group-hover:bg-indigo-500/50 transition-all rounded-full" />
                  <p className="line-clamp-2 text-[13px] leading-relaxed text-neutral-600 dark:text-neutral-400 group-hover:text-neutral-900 dark:group-hover:text-neutral-200 transition-colors">
                    {trace.steps[0]?.prompt_summary || "No request content available"}
                  </p>
                </div>
              </div>
              
              <div className="mt-5 flex items-center justify-between border-t border-neutral-100 pt-4 dark:border-neutral-800">
                <div className="flex items-center gap-1.5 text-[10px] font-medium text-neutral-400">
                  <Clock className="h-3 w-3" />
                  {new Date(trace.created_at).toLocaleTimeString(undefined, {
                    hour: "2-digit",
                    minute: "2-digit",
                    hour12: false,
                  })}
                </div>
                
                <div className="flex items-center gap-1 text-[10px] font-bold text-indigo-500 group-hover:translate-x-1 transition-transform">
                  Details <ChevronRight className="h-3 w-3" />
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      <TraceDetailModal 
        trace={selectedTrace} 
        onClose={() => setSelectedTrace(null)} 
      />
    </section>
  );
};

export default TraceViewer;
