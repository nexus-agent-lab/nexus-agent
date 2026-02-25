import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import Link from "next/link";
import { Brain, Database, Cpu, History, Info, Activity, Shield } from "lucide-react";
import { verifyAuthToken } from "@/lib/auth";
import DataTable from "@/components/DataTable";
import MetricCard from "@/components/MetricCard";
import { cn } from "@/lib/utils";
import ChangelogActions from "./ChangelogActions";

interface Memory {
  id: number;
  user_id: number;
  content: string;
  memory_type: string;
  skill_id?: number;
  created_at: string;
}

interface MemoryStats {
  total_memories: number;
  memories_by_type: Record<string, number>;
}

interface MemorySkill {
  id: number;
  name: string;
  description: string;
  skill_type: string;
  prompt_template: string;
  version: number;
  is_base: boolean;
  status: string;
  positive_count: number;
  negative_count: number;
  created_at: string;
}

interface MemorySkillStats {
  total_skills: number;
  active_skills: number;
  canary_skills: number;
  deprecated_skills: number;
}

interface Changelog {
  id: number;
  skill_id: number;
  skill_name: string;
  old_prompt: string;
  new_prompt: string;
  reason: string;
  status: string;
  created_at: string;
  reviewed_at?: string;
}

const API_URL = process.env.API_URL || "http://127.0.0.1:8000";

/**
 * Fetch data from backend with API key.
 */
async function fetchData(endpoint: string, apiKey: string) {
  try {
    const res = await fetch(`${API_URL}${endpoint}`, {
      headers: { "X-API-Key": apiKey },
      cache: "no-store",
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (e) {
    console.error(`Failed to fetch ${endpoint}:`, e);
    return null;
  }
}

export default async function CortexPage(props: {
  searchParams: Promise<{ tab?: string }>;
}) {
  const searchParams = await props.searchParams;
  const activeTab = searchParams.tab || "memories";
  
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
        <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">Access Denied</h1>
        <p className="text-neutral-500 dark:text-neutral-400">You need administrator privileges to access this page.</p>
      </div>
    );
  }

  const apiKey = payload.api_key as string;

  // Tabs configuration
  const tabs = [
    { id: "memories", label: "Memory Storage", icon: Database },
    { id: "skills", label: "Skills Management", icon: Cpu },
    { id: "evolution", label: "Evolution History", icon: History },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="flex items-center gap-3 text-3xl font-bold tracking-tight">
          <Brain className="h-8 w-8 text-indigo-500" />
          Cortex
        </h1>
        <p className="text-neutral-500 dark:text-neutral-400">
          The brain center of Nexus Agent. Manage memories, skills, and autonomous evolution.
        </p>
      </div>

      {/* Tabs Navigation */}
      <div className="flex border-b border-neutral-200 dark:border-neutral-800">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <Link
              key={tab.id}
              href={`/cortex?tab=${tab.id}`}
              className={cn(
                "flex items-center gap-2 border-b-2 px-6 py-4 text-sm font-medium transition-colors",
                isActive
                  ? "border-indigo-500 text-indigo-600 dark:text-indigo-400"
                  : "border-transparent text-neutral-500 hover:border-neutral-300 hover:text-neutral-700 dark:hover:text-neutral-300"
              )}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </Link>
          );
        })}
      </div>

      {/* Tab Content */}
      <div className="mt-8">
        {activeTab === "memories" && <MemoriesTab apiKey={apiKey} />}
        {activeTab === "skills" && <SkillsTab apiKey={apiKey} />}
        {activeTab === "evolution" && <EvolutionTab apiKey={apiKey} />}
      </div>
    </div>
  );
}

/**
 * Memory Storage Tab
 */
async function MemoriesTab({ apiKey }: { apiKey: string }) {
  const [memories, stats] = await Promise.all([
    fetchData("/memories", apiKey) as Promise<Memory[] | null>,
    fetchData("/memories/stats", apiKey) as Promise<MemoryStats | null>,
  ]);

  const memoryColumns = [
    { header: "ID", accessorKey: "id" as keyof Memory, cell: (m: Memory) => <span className="text-neutral-500">#{m.id}</span> },
    { 
      header: "Type", 
      accessorKey: "memory_type" as keyof Memory,
      cell: (m: Memory) => (
        <span className={cn(
          "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
          m.memory_type === "profile" ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400" :
          m.memory_type === "reflexion" ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400" :
          "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400"
        )}>
          {m.memory_type}
        </span>
      )
    },
    { 
      header: "Content", 
      accessorKey: "content" as keyof Memory,
      cell: (m: Memory) => (
        <div className="max-w-md overflow-hidden text-ellipsis whitespace-nowrap text-neutral-900 dark:text-neutral-100">
          {m.content}
        </div>
      )
    },
    { 
      header: "Created At", 
      accessorKey: "created_at" as keyof Memory,
      cell: (m: Memory) => (
        <span className="text-xs text-neutral-500">
          {new Date(m.created_at).toLocaleString()}
        </span>
      )
    },
  ];

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="Total Memories" value={stats?.total_memories || 0} icon={<Database className="h-4 w-4" />} />
        <MetricCard label="Profiles" value={stats?.memories_by_type?.profile || 0} />
        <MetricCard label="Reflexions" value={stats?.memories_by_type?.reflexion || 0} />
        <MetricCard label="Knowledge" value={stats?.memories_by_type?.knowledge || 0} />
      </div>

      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Recent Memories</h3>
        <DataTable columns={memoryColumns} data={memories || []} />
      </div>
    </div>
  );
}

/**
 * Skills Management Tab
 */
async function SkillsTab({ apiKey }: { apiKey: string }) {
  const [skills, stats] = await Promise.all([
    fetchData("/memskills", apiKey) as Promise<MemorySkill[] | null>,
    fetchData("/memskills/stats", apiKey) as Promise<MemorySkillStats | null>,
  ]);

  const skillColumns = [
    { 
      header: "Name", 
      accessorKey: "name" as keyof MemorySkill,
      cell: (s: MemorySkill) => (
        <div className="flex flex-col">
          <span className="font-semibold text-neutral-900 dark:text-neutral-100">{s.name}</span>
          <span className="text-xs text-neutral-500">v{s.version}</span>
        </div>
      )
    },
    { 
      header: "Type", 
      accessorKey: "skill_type" as keyof MemorySkill,
      cell: (s: MemorySkill) => (
        <span className="text-xs font-medium uppercase text-neutral-500">{s.skill_type}</span>
      )
    },
    { 
      header: "Status", 
      accessorKey: "status" as keyof MemorySkill,
      cell: (s: MemorySkill) => (
        <span className={cn(
          "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
          s.status === "active" ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400" :
          s.status === "canary" ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400" :
          "bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400"
        )}>
          {s.status}
        </span>
      )
    },
    { 
      header: "Feedback", 
      accessorKey: "positive_count" as keyof MemorySkill,
      cell: (s: MemorySkill) => (
        <div className="flex items-center gap-3">
          <span className="text-xs text-emerald-600 dark:text-emerald-400">+{s.positive_count}</span>
          <span className="text-xs text-rose-600 dark:text-rose-400">-{s.negative_count}</span>
        </div>
      )
    },
  ];

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="Total Skills" value={stats?.total_skills || 0} icon={<Cpu className="h-4 w-4" />} />
        <MetricCard label="Active" value={stats?.active_skills || 0} />
        <MetricCard label="Canaries" value={stats?.canary_skills || 0} />
        <MetricCard label="Deprecated" value={stats?.deprecated_skills || 0} />
      </div>

      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Memory Skills</h3>
        <DataTable columns={skillColumns} data={skills || []} />
      </div>
    </div>
  );
}

/**
 * Evolution History Tab
 */
async function EvolutionTab({ apiKey }: { apiKey: string }) {
  const changelogs = (await fetchData("/memskills/changelogs", apiKey)) as Changelog[] | null;

  const changelogColumns = [
    { header: "Skill", accessorKey: "skill_name" as keyof Changelog },
    { 
      header: "Reason", 
      accessorKey: "reason" as keyof Changelog,
      cell: (c: Changelog) => (
        <div className="flex max-w-xs items-center gap-1.5 overflow-hidden text-ellipsis whitespace-nowrap text-xs text-neutral-600 dark:text-neutral-400">
          <Info className="h-3 w-3 shrink-0" />
          {c.reason}
        </div>
      )
    },
    { 
      header: "Changes", 
      accessorKey: "new_prompt" as keyof Changelog,
      cell: (c: Changelog) => (
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-neutral-400">
            <span className="rounded bg-rose-50 px-1 dark:bg-rose-900/20 text-rose-600 dark:text-rose-400">Old</span>
            <span className="max-w-[150px] truncate">{c.old_prompt}</span>
          </div>
          <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-neutral-400">
            <span className="rounded bg-emerald-50 px-1 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400">New</span>
            <span className="max-w-[150px] truncate font-medium text-neutral-700 dark:text-neutral-300">{c.new_prompt}</span>
          </div>
        </div>
      )
    },
    { 
      header: "Date", 
      accessorKey: "created_at" as keyof Changelog,
      cell: (c: Changelog) => (
        <span className="text-xs text-neutral-500">
          {new Date(c.created_at).toLocaleString()}
        </span>
      )
    },
    { 
      header: "Actions", 
      accessorKey: "status" as keyof Changelog,
      cell: (c: Changelog) => (
        <ChangelogActions id={c.id} status={c.status} />
      )
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Activity className="h-5 w-5 text-indigo-500" />
        <h3 className="text-lg font-semibold">Evolution History</h3>
      </div>
      <p className="text-sm text-neutral-500 dark:text-neutral-400">
        Autonomous changes proposed by the MemSkill Designer. Review and approve to promote canaries to active status.
      </p>
      <DataTable columns={changelogColumns} data={changelogs || []} />
    </div>
  );
}
