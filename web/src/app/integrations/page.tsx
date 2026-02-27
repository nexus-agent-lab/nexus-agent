import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { Puzzle, Shield, Info } from "lucide-react";
import { verifyAuthToken } from "@/lib/auth";
import DataTable from "@/components/DataTable";
import PluginForm from "./PluginForm";
import ReloadMCPButton from "./ReloadMCPButton";
import { cn } from "@/lib/utils";
import DeletePluginButton from "./DeletePluginButton";
import EditPluginButton from "./EditPluginButton";
import ViewSkillButton from "./ViewSkillButton";

interface Plugin {
  id: number;
  name: string;
  type: string;
  source_url: string;
  status: string;
  required_role: string;
  config: Record<string, any>;
  manifest_id: string | null;
}

async function getPlugins(apiKey: string): Promise<Plugin[]> {
  const baseUrl = process.env.API_URL || "http://127.0.0.1:8000";
  try {
    const res = await fetch(`${baseUrl}/plugins/`, {
      headers: {
        "X-API-Key": apiKey,
      },
      cache: "no-store",
    });
    if (!res.ok) return [];
    return await res.json();
  } catch (e) {
    console.error("Failed to fetch plugins:", e);
    return [];
  }
}

export default async function IntegrationsPage() {
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

  const apiKey = payload.api_key as string;
  const plugins = await getPlugins(apiKey);

  const columns = [
    { 
      header: "Plugin Name", 
      accessorKey: "name" as keyof Plugin,
      cell: (item: Plugin) => (
        <div className="flex flex-col">
          <span className="font-medium text-neutral-900 dark:text-neutral-100">
            {item.name}
          </span>
          <span className="text-xs text-neutral-500">ID: {item.id}</span>
        </div>
      )
    },
    { 
      header: "Type", 
      accessorKey: "type" as keyof Plugin,
      cell: (item: Plugin) => (
        <span className="inline-flex items-center rounded-full bg-neutral-100 px-2 py-0.5 text-xs font-medium text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400">
          {item.type}
        </span>
      )
    },
    { 
      header: "Source URL", 
      accessorKey: "source_url" as keyof Plugin,
      cell: (item: Plugin) => (
        <code className="rounded bg-neutral-100 px-1.5 py-0.5 font-mono text-xs dark:bg-neutral-800 max-w-[200px] truncate block" title={item.source_url}>
          {item.source_url}
        </code>
      )
    },
    { 
      header: "Status", 
      accessorKey: "status" as keyof Plugin,
      cell: (item: Plugin) => (
        <span className={cn(
          "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
          item.status === "active" 
            ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
            : "bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-400"
        )}>
          {item.status}
        </span>
      )
    },
    {
      header: "Actions",
      accessorKey: "id" as keyof Plugin,
      cell: (item: Plugin) => (
        <div className="flex items-center gap-2">
          <ViewSkillButton pluginId={item.id} apiKey={apiKey} />
          <EditPluginButton plugin={item} apiKey={apiKey} />
          <DeletePluginButton pluginId={item.id} pluginName={item.name} />
        </div>
      )
    }
  ];

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-neutral-900 dark:text-neutral-100">Integrations</h1>
          <p className="text-neutral-500 dark:text-neutral-400">
            Extend Nexus Agent OS with MCP servers and internal plugins.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="hidden rounded-lg bg-amber-50 p-2 text-xs text-amber-700 dark:bg-amber-900/20 dark:text-amber-400 md:flex items-center gap-2">
            <Info className="h-3.5 w-3.5" />
            Changes require an MCP reload to take effect.
          </div>
        </div>
      </div>

      <div className="space-y-12">
        <div className="space-y-6">
          <ReloadMCPButton />
          <PluginForm apiKey={apiKey} />
        </div>

        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold flex items-center gap-2">
              <Puzzle className="h-5 w-5" />
              Installed Plugins
            </h2>
          </div>
          <DataTable columns={columns} data={plugins} />
        </div>
      </div>
    </div>
  );
}
