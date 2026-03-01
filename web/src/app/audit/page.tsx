import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import Link from "next/link";
import { History, Shield, Activity, Search, Info, ChevronLeft, ChevronRight, Cpu, Clock, Terminal } from "lucide-react";

import { verifyAuthToken } from "@/lib/auth";
import DataTable from "@/components/DataTable";
import WireLogToggle from "@/components/WireLogToggle";
import { cn } from "@/lib/utils";

interface AuditLog {
  id: number;
  trace_id: string;
  user_id: number | null;
  action: string;
  tool_name: string | null;
  status: string;
  created_at: string;
}
interface LLMTraceRecord {
  id: number;
  model: string;
  latency_ms: number;
  prompt_summary: string;
  tools_bound: string[] | null;
  created_at: string;
}

/**
 * Fetches audit logs from the backend.
 * @param apiKey Admin API key
 */
async function getAuditLogs(apiKey: string, skip: number = 0, limit: number = 50): Promise<AuditLog[]> {
  const baseUrl = process.env.API_URL || "http://127.0.0.1:8000";
  try {
    const res = await fetch(`${baseUrl}/audit?skip=${skip}&limit=${limit}`, {
      headers: {
        "X-API-Key": apiKey,
      },
      cache: "no-store",
    });
    if (!res.ok) return [];
    return await res.json();
  } catch (e) {
    console.error("Failed to fetch audit logs:", e);
    return [];
  }
}
/**
 * Fetches LLM traces from the backend.
 * @param apiKey Admin API key
 */
async function getTraces(apiKey: string, limit: number = 20): Promise<LLMTraceRecord[]> {
  const baseUrl = process.env.API_URL || "http://127.0.0.1:8000";
  try {
    const res = await fetch(`${baseUrl}/admin/traces?limit=${limit}`, {
      headers: {
        "X-API-Key": apiKey,
      },
      cache: "no-store",
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.traces || [];
  } catch (e) {
    console.error("Failed to fetch traces:", e);
    return [];
  }
}


/**
 * Audit & Observability Page.
 * Displays audit logs and provides debugging tools for administrators.
 */
export default async function AuditPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string }>;
}) {
  const params = await searchParams;
  const page = parseInt(params.page || "1");
  const limit = 50;
  const skip = (page - 1) * limit;

  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;

  if (!token) {
    redirect("/login");
  }

  let payload;
  try {
    payload = await verifyAuthToken(token);
  } catch (e) {
    redirect("/login");
  }

  if (payload.role !== "admin") {
    return (
      <div className="flex h-[60vh] flex-col items-center justify-center space-y-4">
        <Shield className="h-16 w-16 text-rose-500" />
        <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">
          Access Denied
        </h1>
        <p className="text-neutral-500 dark:text-neutral-400">
          You need administrator privileges to access this page.
        </p>
      </div>
    );
  }

  const logs = await getAuditLogs(payload.api_key as string, skip, limit);
  const traces = await getTraces(payload.api_key as string);

  const columns = [
    {
      header: "Timestamp",
      accessorKey: "created_at" as keyof AuditLog,
      cell: (item: AuditLog) => (
        <span className="text-neutral-500 font-mono text-xs">
          {new Date(item.created_at).toLocaleTimeString(undefined, {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
            hour12: false,
          })}
        </span>
      ),
    },
    {
      header: "Action",
      accessorKey: "action" as keyof AuditLog,
      cell: (item: AuditLog) => (
        <span className="font-medium text-neutral-900 dark:text-neutral-100">
          {item.action}
        </span>
      ),
    },
    {
      header: "Tool",
      accessorKey: "tool_name" as keyof AuditLog,
      cell: (item: AuditLog) => (
        item.tool_name ? (
          <code className="rounded bg-neutral-100 px-1.5 py-0.5 font-mono text-xs dark:bg-neutral-800">
            {item.tool_name}
          </code>
        ) : (
          <span className="text-neutral-400">—</span>
        )
      ),
    },
    {
      header: "Status",
      accessorKey: "status" as keyof AuditLog,
      cell: (item: AuditLog) => (
        <span className={cn(
          "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
          item.status === "SUCCESS"
            ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
            : item.status === "FAILURE"
            ? "bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400"
            : "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
        )}>
          {item.status}
        </span>
      ),
    },
    {
      header: "User ID",
      accessorKey: "user_id" as keyof AuditLog,
      cell: (item: AuditLog) => (
        <span className="text-neutral-500">
          {item.user_id ? `#${item.user_id}` : "System"}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Observability & Audit</h1>
        <p className="text-neutral-500 dark:text-neutral-400">
          Monitor agent actions, tool executions, and system health in real-time.
        </p>
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Main Audit Table */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold flex items-center gap-2">
              <History className="h-5 w-5 text-indigo-500" />
              Audit Logs
            </h2>
            <div className="flex items-center gap-2 rounded-lg bg-neutral-100 px-3 py-1.5 dark:bg-neutral-800">
              <Search className="h-4 w-4 text-neutral-500" />
              <input
                type="text"
                placeholder="Filter logs..."
                className="bg-transparent text-sm outline-none placeholder:text-neutral-500"
              />
            </div>
          </div>
          <DataTable columns={columns} data={logs} />
          
          <div className="flex items-center justify-between">
            <p className="text-sm text-neutral-500">
              Showing {logs.length} logs
            </p>
            <div className="flex items-center gap-2">
              <Link
                href={`/audit?page=${Math.max(1, page - 1)}`}
                className={cn(
                  "flex items-center gap-1 rounded-lg border border-neutral-200 px-3 py-1 text-sm font-medium transition-colors hover:bg-neutral-100 dark:border-neutral-800 dark:hover:bg-neutral-800",
                  page <= 1 && "pointer-events-none opacity-50"
                )}
              >
                <ChevronLeft className="h-4 w-4" />
                Previous
              </Link>
              <span className="text-sm font-medium">Page {page}</span>
              <Link
                href={`/audit?page=${page + 1}`}
                className={cn(
                  "flex items-center gap-1 rounded-lg border border-neutral-200 px-3 py-1 text-sm font-medium transition-colors hover:bg-neutral-100 dark:border-neutral-800 dark:hover:bg-neutral-800",
                  logs.length < limit && "pointer-events-none opacity-50"
                )}
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </Link>
            </div>
          </div>
        </div>

        {/* Sidebar Diagnostics */}
        <div className="space-y-6">
          <section className="space-y-4">
            <h2 className="text-xl font-semibold flex items-center gap-2">
              <Activity className="h-5 w-5 text-indigo-500" />
              LLM Debug
            </h2>
            <WireLogToggle apiKey={payload.api_key as string} />
          </section>

          <section className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold flex items-center gap-2">
                <Activity className="h-5 w-5 text-indigo-500" />
                Trace Viewer
              </h2>
              <span className="text-xs font-medium text-neutral-500">
                Live
              </span>
            </div>
            
            <div className="space-y-3">
              {traces.length === 0 ? (
                <div className="rounded-xl border border-dashed border-neutral-300 p-8 text-center dark:border-neutral-700">
                  <Info className="mx-auto h-8 w-8 text-neutral-300 dark:text-neutral-600" />
                  <p className="mt-2 text-sm text-neutral-500">
                    No traces available yet.
                  </p>
                </div>
              ) : (
                traces.map((trace) => (
                  <div key={trace.id} className="group relative rounded-xl border border-neutral-200 bg-white p-4 transition-all hover:border-indigo-200 hover:shadow-sm dark:border-neutral-800 dark:bg-neutral-900/50">
                    <div className="mb-2 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Cpu className="h-3.5 w-3.5 text-neutral-400" />
                        <span className="text-xs font-semibold text-neutral-700 dark:text-neutral-300">
                          {trace.model}
                        </span>
                      </div>
                      <div className={cn(
                        "flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold",
                        trace.latency_ms < 2000 
                          ? "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/30 dark:text-emerald-400" 
                          : trace.latency_ms < 5000 
                            ? "bg-amber-50 text-amber-600 dark:bg-amber-950/30 dark:text-amber-400" 
                            : "bg-rose-50 text-rose-600 dark:bg-rose-950/30 dark:text-rose-400"
                      )}>
                        <Clock className="h-3 w-3" />
                        {(trace.latency_ms / 1000).toFixed(1)}s
                      </div>
                    </div>
                    
                    <p className="mb-3 line-clamp-2 text-xs text-neutral-600 dark:text-neutral-400">
                      {trace.prompt_summary || "No prompt summary available"}
                    </p>
                    
                    <div className="flex flex-wrap gap-1.5">
                      {trace.tools_bound?.slice(0, 5).map((tool) => (
                        <div key={tool} className="flex items-center gap-1 rounded bg-neutral-100 px-1.5 py-0.5 text-[10px] font-medium text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400">
                          <Terminal className="h-2.5 w-2.5" />
                          {tool}
                        </div>
                      ))}
                      {(trace.tools_bound?.length || 0) > 5 && (
                        <span className="text-[10px] text-neutral-400">
                          +{(trace.tools_bound?.length || 0) - 5} more
                        </span>
                      )}
                    </div>
                    
                    <div className="mt-3 flex items-center justify-between border-t border-neutral-100 pt-2 dark:border-neutral-800">
                      <span className="text-[10px] text-neutral-400">
                        {new Date(trace.created_at).toLocaleTimeString(undefined, {
                          hour: "2-digit",
                          minute: "2-digit",
                          second: "2-digit",
                          hour12: false,
                        })}
                      </span>
                      <span className="text-[10px] font-mono text-neutral-400">
                        #{trace.id}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
