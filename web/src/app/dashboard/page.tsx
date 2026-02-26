import { Suspense } from "react";
import { 
  Activity, 
  Database, 
  Server, 
  Cpu,
  History
} from "lucide-react";
import MetricCard from "@/components/MetricCard";
import DataTable from "@/components/DataTable";
import LoadingSkeleton from "@/components/LoadingSkeleton";
import QuickActions from "./QuickActions";
import { cn } from "@/lib/utils";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { verifyAuthToken } from "@/lib/auth";

interface SystemHealth {
  status: string;
  timestamp: string;
}

interface DatabaseStatus {
  status: string;
  error?: string;
}

interface RedisStatus {
  status: string;
  inbox_length: number;
  outbox_length: number;
  dlq_length: number;
  error?: string;
}

interface AuditLog {
  id: number;
  action: string;
  status: string;
  created_at: string;
  user_id?: number;
}

async function getSystemHealth(apiKey: string): Promise<SystemHealth | null> {
  try {
    const baseUrl = process.env.API_URL || 'http://127.0.0.1:8000';
    const res = await fetch(`${baseUrl}/system/health`, { 
      headers: { "X-API-Key": apiKey },
      cache: 'no-store' 
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (e) {
    return null;
  }
}

async function getDatabaseStatus(apiKey: string): Promise<DatabaseStatus | null> {
  try {
    const baseUrl = process.env.API_URL || 'http://127.0.0.1:8000';
    const res = await fetch(`${baseUrl}/system/database`, { 
      headers: { "X-API-Key": apiKey },
      cache: 'no-store' 
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (e) {
    return null;
  }
}

async function getRedisStatus(apiKey: string): Promise<RedisStatus | null> {
  try {
    const baseUrl = process.env.API_URL || 'http://127.0.0.1:8000';
    const res = await fetch(`${baseUrl}/system/redis`, { 
      headers: { "X-API-Key": apiKey },
      cache: 'no-store' 
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (e) {
    return null;
  }
}

async function getAuditLogs(apiKey: string): Promise<AuditLog[]> {
  try {
    const baseUrl = process.env.API_URL || 'http://127.0.0.1:8000';
    const res = await fetch(`${baseUrl}/audit?limit=5`, { 
      headers: { "X-API-Key": apiKey },
      cache: 'no-store' 
    });
    if (!res.ok) return [];
    return await res.json();
  } catch (e) {
    return [];
  }
}

export default async function DashboardPage() {
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

  const apiKey = payload.api_key as string;

  const [health, dbStatus, redisStatus, auditLogs] = await Promise.all([
    getSystemHealth(apiKey),
    getDatabaseStatus(apiKey),
    getRedisStatus(apiKey),
    getAuditLogs(apiKey),
  ]);

  const auditColumns = [
    { 
      header: "Action", 
      accessorKey: "action" as keyof AuditLog,
      cell: (item: AuditLog) => (
        <span className="font-medium text-neutral-900 dark:text-neutral-100">
          {item.action}
        </span>
      )
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
            : "bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-400"
        )}>
          {item.status}
        </span>
      )
    },
    { 
      header: "Time", 
      accessorKey: "created_at" as keyof AuditLog,
      cell: (item: AuditLog) => new Date(item.created_at).toLocaleString()
    },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-neutral-500 dark:text-neutral-400">
          Monitor your Nexus Agent OS health and activity.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="Agent Core"
          value={health?.status === "ok" ? "Online" : "Offline"}
          icon={<Activity className="h-5 w-5" />}
          className={health?.status === "ok" ? "border-emerald-200 dark:border-emerald-800/50" : "border-rose-200 dark:border-rose-800/50"}
        />
        <MetricCard
          label="Database"
          value={dbStatus?.status === "connected" ? "Connected" : "Disconnected"}
          icon={<Database className="h-5 w-5" />}
        />
        <MetricCard
          label="Redis"
          value={redisStatus?.status === "connected" ? `${redisStatus.inbox_length} msgs` : "Disconnected"}
          icon={<Server className="h-5 w-5" />}
        />
        <MetricCard
          label="Model Service"
          value="Online" // Placeholder as there's no specific endpoint yet
          icon={<Cpu className="h-5 w-5" />}
        />
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold flex items-center gap-2">
              <History className="h-5 w-5" />
              Recent Activity
            </h2>
          </div>
          <DataTable columns={auditColumns} data={auditLogs} />
        </div>

        <div className="space-y-4">
          <QuickActions />
        </div>
      </div>
    </div>
  );
}
