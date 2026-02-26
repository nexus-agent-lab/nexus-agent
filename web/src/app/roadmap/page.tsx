import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { Map, Lightbulb, CheckCircle2, XCircle, Trash2, Clock, Filter } from "lucide-react";
import { verifyAuthToken } from "@/lib/auth";
import DataTable from "@/components/DataTable";
import { cn } from "@/lib/utils";
import RoadmapActions from "./RoadmapActions";

interface Suggestion {
  id: number;
  content: string;
  category: string;
  priority: string;
  status: string;
  votes: number;
  user_id: number;
  created_at: string;
}

const API_URL = process.env.API_URL || "http://127.0.0.1:8000";

async function getSuggestions(apiKey: string, status?: string) {
  const url = status ? `${API_URL}/roadmap/?status=${status}` : `${API_URL}/roadmap/`;
  try {
    const res = await fetch(url, {
      headers: { "X-API-Key": apiKey },
      cache: "no-store",
    });
    if (!res.ok) return [];
    return await res.json();
  } catch (e) {
    return [];
  }
}

export default async function RoadmapPage(props: {
  searchParams: Promise<{ status?: string }>;
}) {
  const searchParams = await props.searchParams;
  const statusFilter = searchParams.status || "";
  
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;

  if (!token) redirect("/login");

  let payload;
  try {
    payload = await verifyAuthToken(token);
  } catch (e) {
    redirect("/login");
  }

  const apiKey = payload.api_key as string;
  const suggestions = await getSuggestions(apiKey, statusFilter);

  const columns = [
    {
      header: "Category",
      accessorKey: "category" as keyof Suggestion,
      cell: (item: Suggestion) => (
        <span className="text-xs font-bold uppercase text-neutral-400">
          {item.category}
        </span>
      ),
    },
    {
      header: "Content",
      accessorKey: "content" as keyof Suggestion,
      cell: (item: Suggestion) => (
        <div className="max-w-md font-medium text-neutral-900 dark:text-neutral-100">
          {item.content}
        </div>
      ),
    },
    {
      header: "Status",
      accessorKey: "status" as keyof Suggestion,
      cell: (item: Suggestion) => (
        <span className={cn(
          "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium",
          item.status === "approved" ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400" :
          item.status === "implemented" ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400" :
          item.status === "rejected" ? "bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400" :
          "bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-400"
        )}>
          {item.status === "pending" && <Clock className="h-3 w-3" />}
          {item.status === "approved" && <Lightbulb className="h-3 w-3" />}
          {item.status === "implemented" && <CheckCircle2 className="h-3 w-3" />}
          {item.status === "rejected" && <XCircle className="h-3 w-3" />}
          {item.status}
        </span>
      ),
    },
    {
      header: "Votes",
      accessorKey: "votes" as keyof Suggestion,
      cell: (item: Suggestion) => (
        <span className="text-neutral-500">{item.votes}</span>
      ),
    },
    {
      header: "Actions",
      id: "actions",
      cell: (item: Suggestion) => (
        <RoadmapActions id={item.id} status={item.status} isAdmin={payload.role === "admin"} />
      ),
    },
  ];

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <Map className="h-8 w-8 text-indigo-500" />
            Product Roadmap
          </h1>
          <p className="text-neutral-500 dark:text-neutral-400 mt-2">
            Community suggestions and planned features for Nexus Agent.
          </p>
        </div>
      </div>

      <div className="flex items-center gap-4 border-b border-neutral-200 dark:border-neutral-800 pb-4">
        <Filter className="h-4 w-4 text-neutral-400" />
        <div className="flex gap-2">
          {[
            { label: "All", value: "" },
            { label: "Pending", value: "pending" },
            { label: "Approved", value: "approved" },
            { label: "Implemented", value: "implemented" },
            { label: "Rejected", value: "rejected" },
          ].map((f) => (
            <a
              key={f.value}
              href={`/roadmap?status=${f.value}`}
              className={cn(
                "rounded-full px-3 py-1 text-xs font-medium transition-colors",
                statusFilter === f.value
                  ? "bg-indigo-600 text-white"
                  : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200 dark:bg-neutral-800 dark:text-neutral-400 dark:hover:bg-neutral-700"
              )}
            >
              {f.label}
            </a>
          ))}
        </div>
      </div>

      <DataTable columns={columns} data={suggestions} />
    </div>
  );
}
