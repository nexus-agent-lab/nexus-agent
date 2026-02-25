import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { Users, Shield } from "lucide-react";
import { verifyAuthToken } from "@/lib/auth";
import DataTable from "@/components/DataTable";
import CreateUserForm from "./CreateUserForm";
import { cn } from "@/lib/utils";

interface User {
  id: number;
  username: string;
  api_key: string;
  role: string;
  language: string;
  timezone?: string;
  notes?: string;
  policy: Record<string, any>;
}

async function getUsers(apiKey: string): Promise<User[]> {
  const baseUrl = process.env.API_URL || "http://127.0.0.1:8000";
  try {
    const res = await fetch(`${baseUrl}/users/`, {
      headers: {
        "X-API-Key": apiKey,
      },
      cache: "no-store",
    });
    if (!res.ok) return [];
    return await res.json();
  } catch (e) {
    console.error("Failed to fetch users:", e);
    return [];
  }
}

export default async function UsersPage() {
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

  const users = await getUsers(payload.api_key as string);

  const columns = [
    { 
      header: "ID", 
      accessorKey: "id" as keyof User,
      cell: (item: User) => <span className="text-neutral-500">#{item.id}</span>
    },
    { 
      header: "Username", 
      accessorKey: "username" as keyof User,
      cell: (item: User) => (
        <span className="font-medium text-neutral-900 dark:text-neutral-100">
          {item.username}
        </span>
      )
    },
    { 
      header: "Role", 
      accessorKey: "role" as keyof User,
      cell: (item: User) => (
        <span className={cn(
          "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
          item.role === "admin" 
            ? "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400"
            : item.role === "guest"
            ? "bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400"
            : "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
        )}>
          {item.role}
        </span>
      )
    },
    { 
      header: "API Key", 
      accessorKey: "api_key" as keyof User,
      cell: (item: User) => (
        <code className="rounded bg-neutral-100 px-1.5 py-0.5 font-mono text-xs dark:bg-neutral-800">
          {item.api_key.substring(0, 8)}...
        </code>
      )
    },
    { 
      header: "Language", 
      accessorKey: "language" as keyof User,
      cell: (item: User) => (
        <span className="uppercase text-neutral-500">{item.language}</span>
      )
    },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Users & IAM</h1>
        <p className="text-neutral-500 dark:text-neutral-400">
          Manage user accounts, roles, and access keys.
        </p>
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold flex items-center gap-2">
              <Users className="h-5 w-5" />
              Active Users
            </h2>
          </div>
          <DataTable columns={columns} data={users} />
        </div>

      </div>
    </div>
  );
}
