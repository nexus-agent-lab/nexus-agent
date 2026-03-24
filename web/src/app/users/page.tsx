import { redirect } from "next/navigation";
import { Users, Shield } from "lucide-react";
import DataTable from "@/components/DataTable";
import { cn } from "@/lib/utils";
import Link from "next/link";
import { Settings2 } from "lucide-react";
import CreateUserForm from "./CreateUserForm";
import { buildBearerHeaders, getServerAuthContext } from "@/lib/server-auth";
import { getDictionary, getServerLocale } from "@/lib/locale";
interface User {
  id: number;
  username: string;
  api_key: string;
  role: string;
  language: string;
  timezone?: string;
  notes?: string;
  policy: Record<string, unknown>;
}

interface UserRow extends User {
  telegram_bound: boolean;
  telegram_username?: string | null;
  wechat_bound: boolean;
  wechat_polling_active: boolean;
}

interface UserChannelStatus {
  user_id: number;
  telegram_bound: boolean;
  telegram_username?: string | null;
  wechat_bound: boolean;
  wechat_polling_active: boolean;
}

async function getUsers(token: string): Promise<User[]> {
  const baseUrl = process.env.API_URL || "http://127.0.0.1:8000/api";
  try {
    const res = await fetch(`${baseUrl}/users/`, {
      headers: buildBearerHeaders(token),
      cache: "no-store",
    });
    if (!res.ok) return [];
    return await res.json();
  } catch (e) {
    console.error("Failed to fetch users:", e);
    return [];
  }
}

async function getUserChannelStatuses(token: string): Promise<Map<number, UserChannelStatus>> {
  const baseUrl = process.env.API_URL || "http://127.0.0.1:8000/api";
  try {
    const res = await fetch(`${baseUrl}/users/channel-statuses`, {
      headers: buildBearerHeaders(token),
      cache: "no-store",
    });
    if (!res.ok) {
      return new Map();
    }
    const rows = (await res.json()) as UserChannelStatus[];
    return new Map(rows.map((row) => [row.user_id, row]));
  } catch (e) {
    console.error("Failed to fetch user channel statuses:", e);
    return new Map();
  }
}

export default async function UsersPage() {
  const authContext = await getServerAuthContext();
  if (!authContext) {
    redirect("/login");
  }
  const { token, payload } = authContext;
  const locale = await getServerLocale();
  const dict = getDictionary(locale);

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

  const users = await getUsers(token);
  const channelStatuses = await getUserChannelStatuses(token);
  const usersWithBindings: UserRow[] = users.map((user) => {
    const status = channelStatuses.get(user.id);
    return {
      ...user,
      telegram_bound: status?.telegram_bound ?? false,
      telegram_username: status?.telegram_username ?? null,
      wechat_bound: status?.wechat_bound ?? false,
      wechat_polling_active: status?.wechat_polling_active ?? false,
    };
  });

  const columns = [
    { 
      header: dict.users.id, 
      accessorKey: "id" as keyof UserRow,
      cell: (item: UserRow) => <span className="text-neutral-500">#{item.id}</span>
    },
    { 
      header: dict.users.username, 
      accessorKey: "username" as keyof UserRow,
      cell: (item: UserRow) => (
        <span className="font-medium text-neutral-900 dark:text-neutral-100">
          {item.username}
        </span>
      )
    },
    { 
      header: dict.users.role, 
      accessorKey: "role" as keyof UserRow,
      cell: (item: UserRow) => (
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
      header: dict.users.apiKey, 
      accessorKey: "api_key" as keyof UserRow,
      cell: (item: UserRow) => (
        <code className="rounded bg-neutral-100 px-1.5 py-0.5 font-mono text-xs dark:bg-neutral-800">
          {item.api_key.substring(0, 8)}...
        </code>
      )
    },
    { 
      header: dict.users.language, 
      accessorKey: "language" as keyof UserRow,
      cell: (item: UserRow) => (
        <span className="uppercase text-neutral-500">{item.language}</span>
      )
    },
    {
      header: dict.users.telegram,
      accessorKey: "telegram_bound" as keyof UserRow,
      cell: (item: UserRow) => (
        <div className="space-y-1">
          <span className={cn(
            "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
            item.telegram_bound
              ? "bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-400"
              : "bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400"
          )}>
            {item.telegram_bound ? dict.users.bound : dict.users.notBound}
          </span>
          {item.telegram_username ? (
            <div className="text-xs text-neutral-500">{item.telegram_username}</div>
          ) : null}
        </div>
      )
    },
    {
      header: dict.users.wechat,
      accessorKey: "wechat_bound" as keyof UserRow,
      cell: (item: UserRow) => (
        <div className="space-y-1">
          <span className={cn(
            "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
            item.wechat_bound
              ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
              : "bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400"
          )}>
            {item.wechat_bound ? dict.users.bound : dict.users.notBound}
          </span>
          {item.wechat_bound ? (
            <div className="text-xs text-neutral-500">
              {item.wechat_polling_active ? dict.users.pollingActive : dict.users.pollingIdle}
            </div>
          ) : null}
        </div>
      )
    },
    { 
      header: dict.users.actions, 
      accessorKey: "id" as keyof UserRow,
      cell: (item: UserRow) => (
        <Link 
          href={`/users/${item.id}`}
          className="inline-flex items-center gap-1.5 text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 dark:hover:text-indigo-300"
        >
          <Settings2 className="h-4 w-4" />
          {dict.users.manage}
        </Link>
      )
    },
  ];


  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">{dict.users.title}</h1>
        <p className="text-neutral-500 dark:text-neutral-400">
          {dict.users.subtitle}
        </p>
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold flex items-center gap-2">
              <Users className="h-5 w-5" />
              {dict.users.activeUsers}
            </h2>
            <p className="text-sm text-neutral-500 dark:text-neutral-400">
              {dict.users.tableHint}
            </p>
          </div>
          <DataTable columns={columns} data={usersWithBindings} />
        </div>

        <div className="space-y-4">
          <CreateUserForm />
          <div className="rounded-xl border border-neutral-200 bg-white p-6 shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
            <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
              {dict.users.channelBinding}
            </h3>
            <p className="mt-2 text-sm text-neutral-500 dark:text-neutral-400">
              {dict.users.channelBindingHint}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
