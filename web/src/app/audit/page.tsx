import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import Link from "next/link";
import { History, Shield, Activity, Search, Info, ChevronLeft, ChevronRight } from "lucide-react";

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

          <section className="space-y-4 opacity-50">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold flex items-center gap-2">
                <Activity className="h-5 w-5 text-neutral-400" />
                Trace Viewer
              </h2>
              <span className="rounded bg-neutral-100 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-neutral-500 dark:bg-neutral-800">
                Coming Soon
              </span>
            </div>
            <div className="rounded-xl border border-dashed border-neutral-300 p-8 text-center dark:border-neutral-700">
              <Info className="mx-auto h-8 w-8 text-neutral-300 dark:text-neutral-600" />
              <p className="mt-2 text-sm text-neutral-500">
                LangGraph execution paths and node tracing will be visible here.
              </p>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
