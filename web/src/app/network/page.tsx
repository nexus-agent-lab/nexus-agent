import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { Network, Shield, AlertCircle, Laptop, Server, Activity } from "lucide-react";

import { verifyAuthToken } from "@/lib/auth";
import DataTable from "@/components/DataTable";
import { cn } from "@/lib/utils";

interface NetworkNode {
  hostname: string;
  ip: string;
  os: string | null;
  type: string;
  online: boolean | null;
}

interface NetworkStatusResponse {
  status: string;
  nodes: NetworkNode[];
  error: string | null;
}

async function getNetworkStatus(apiKey: string): Promise<NetworkStatusResponse> {
  const baseUrl = process.env.API_URL || "http://127.0.0.1:8000";
  try {
    const res = await fetch(`${baseUrl}/system/network`, {
      headers: {
        "X-API-Key": apiKey,
      },
      cache: "no-store",
    });
    if (!res.ok) {
      return { status: "error", nodes: [], error: `HTTP Error: ${res.status}` };
    }
    return await res.json();
  } catch (e) {
    console.error("Failed to fetch network status:", e);
    return { status: "error", nodes: [], error: String(e) };
  }
}

export default async function NetworkPage() {
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

  const { status, nodes, error } = await getNetworkStatus(payload.api_key as string);

  const columns = [
    {
      header: "Hostname",
      accessorKey: "hostname" as keyof NetworkNode,
      cell: (item: NetworkNode) => (
        <div className="flex items-center gap-2">
          {item.type.includes("Local") ? (
            <Server className="h-4 w-4 text-indigo-500" />
          ) : (
            <Laptop className="h-4 w-4 text-neutral-500" />
          )}
          <span className="font-medium text-neutral-900 dark:text-neutral-100">
            {item.hostname}
          </span>
        </div>
      ),
    },
    {
      header: "IP Address",
      accessorKey: "ip" as keyof NetworkNode,
      cell: (item: NetworkNode) => (
        <code className="rounded bg-neutral-100 px-1.5 py-0.5 font-mono text-sm dark:bg-neutral-800">
          {item.ip || "—"}
        </code>
      ),
    },
    {
      header: "OS",
      accessorKey: "os" as keyof NetworkNode,
      cell: (item: NetworkNode) => (
        <span className="text-neutral-600 dark:text-neutral-400">
          {item.os || "—"}
        </span>
      ),
    },
    {
      header: "Type",
      accessorKey: "type" as keyof NetworkNode,
      cell: (item: NetworkNode) => (
        <span className="text-sm font-medium text-neutral-500">
          {item.type}
        </span>
      ),
    },
    {
      header: "Status",
      accessorKey: "online" as keyof NetworkNode,
      cell: (item: NetworkNode) => {
        if (item.online === null) {
          return <span className="text-neutral-400">Unknown</span>;
        }
        return (
          <span
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium",
              item.online
                ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
                : "bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-400"
            )}
          >
            <span
              className={cn(
                "h-1.5 w-1.5 rounded-full",
                item.online ? "bg-emerald-500" : "bg-neutral-400"
              )}
            />
            {item.online ? "Online" : "Offline"}
          </span>
        );
      },
    },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
          <Network className="h-8 w-8 text-indigo-500" />
          Network Status
        </h1>
        <p className="text-neutral-500 dark:text-neutral-400 mt-2">
          View Tailscale nodes and connection details.
        </p>
      </div>

      {error ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 dark:border-rose-900/50 dark:bg-rose-900/10">
          <div className="flex items-start gap-3">
            <AlertCircle className="mt-0.5 h-5 w-5 text-rose-500" />
            <div>
              <h3 className="text-sm font-medium text-rose-800 dark:text-rose-200">
                Failed to fetch real-time network status
              </h3>
              <p className="mt-1 text-sm text-rose-600 dark:text-rose-300">
                {error}
              </p>
              <div className="mt-3 text-sm text-rose-700 dark:text-rose-400 flex flex-col gap-1">
                <span>Cannot access Docker interface (Sidecar isolation).</span>
                <a 
                  href="https://login.tailscale.com/admin/machines" 
                  target="_blank" 
                  rel="noreferrer"
                  className="font-medium underline hover:text-rose-800 dark:hover:text-rose-200 transition-colors"
                >
                  👉 Open Tailscale Admin Console
                </a>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 dark:border-emerald-900/50 dark:bg-emerald-900/10 mb-6">
          <div className="flex items-center gap-2 text-emerald-800 dark:text-emerald-200 font-medium">
            <Activity className="h-5 w-5" />
            Network Status: Online ({nodes.length} nodes)
          </div>
        </div>
      )}

      <div className="space-y-4">
        <DataTable columns={columns} data={nodes.length > 0 ? nodes : [{
            hostname: "nexus-agent-server (本机)",
            ip: "自动获取 (MagicDNS)",
            os: "Unknown",
            type: "Local (本节点)",
            online: true
          }]} 
        />
      </div>

      <div className="pt-8">
        <div className="rounded-xl border border-neutral-200 bg-white p-6 shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
          <h2 className="text-lg font-semibold mb-4">Connection Info</h2>
          <div className="p-3 bg-neutral-100 dark:bg-neutral-950 rounded border border-neutral-200 dark:border-neutral-800 font-mono text-sm text-neutral-800 dark:text-neutral-300">
            http://nexus-agent-server:8000
          </div>
          <p className="mt-2 text-sm text-neutral-500 dark:text-neutral-400">
            Enter this URL in your Nexus App (Requires Tailscale connection)
          </p>
        </div>
      </div>
    </div>
  );
}
