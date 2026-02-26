import { cookies } from "next/headers";
import { redirect, notFound } from "next/navigation";
import Link from "next/link";
import { ChevronLeft, User as UserIcon, Shield, Fingerprint } from "lucide-react";
import { verifyAuthToken } from "@/lib/auth";
import EditUserForm from "./EditUserForm";

interface User {
  id: number;
  username: string;
  role: string;
  language: string;
  timezone?: string;
  notes?: string;
  policy: Record<string, any>;
  api_key: string;
}

async function getUser(userId: string, apiKey: string): Promise<User | null> {
  const baseUrl = process.env.API_URL || "http://127.0.0.1:8000";
  try {
    const res = await fetch(`${baseUrl}/users/${userId}`, {
      headers: {
        "X-API-Key": apiKey,
      },
      cache: "no-store",
    });
    if (!res.ok) {
      if (res.status === 404) return null;
      throw new Error(`Failed to fetch user: ${res.status}`);
    }
    return await res.json();
  } catch (e) {
    console.error("Failed to fetch user:", e);
    return null;
  }
}

/**
 * UserDetailPage displays specific user details and provides an interface
 * for administrators to manage user properties and security policies.
 */
export default async function UserDetailPage({

  params,
}: {
  params: { user_id: string };
}) {
  const { user_id } = await params;
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

  const user = await getUser(user_id, payload.api_key as string);

  if (!user) {
    notFound();
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center gap-4">
        <Link
          href="/users"
          className="flex h-10 w-10 items-center justify-center rounded-full border border-neutral-200 bg-white transition-colors hover:bg-neutral-50 dark:border-neutral-800 dark:bg-neutral-900 dark:hover:bg-neutral-800"
        >
          <ChevronLeft className="h-5 w-5" />
        </Link>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-3xl font-bold tracking-tight">User Details</h1>
            <span className="rounded-full bg-neutral-100 px-2.5 py-0.5 text-xs font-mono text-neutral-500 dark:bg-neutral-800">
              #{user.id}
            </span>
          </div>
          <p className="text-neutral-500 dark:text-neutral-400">
            View and manage permissions for {user.username}.
          </p>
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-1 space-y-6">
          <div className="rounded-xl border border-neutral-200 bg-white p-6 shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
            <div className="mb-6 flex flex-col items-center text-center">
              <div className="mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-indigo-50 text-indigo-600 dark:bg-indigo-900/20 dark:text-indigo-400">
                <UserIcon className="h-10 w-10" />
              </div>
              <h2 className="text-xl font-bold">{user.username}</h2>
              <span className="mt-1 inline-flex items-center rounded-full bg-indigo-100 px-2.5 py-0.5 text-xs font-medium text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400">
                {user.role}
              </span>
            </div>

            <div className="space-y-4">
              <div className="flex items-center justify-between text-sm">
                <span className="text-neutral-500">API Key</span>
                <code className="rounded bg-neutral-100 px-1.5 py-0.5 font-mono text-xs dark:bg-neutral-800">
                  {user.api_key.substring(0, 12)}...
                </code>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-neutral-500">Language</span>
                <span className="font-medium uppercase">{user.language}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-neutral-500">Timezone</span>
                <span className="font-medium">{user.timezone || "Not set"}</span>
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-neutral-200 bg-white p-6 shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
            <h3 className="mb-4 flex items-center gap-2 font-semibold">
              <Fingerprint className="h-4 w-4 text-neutral-400" />
              Identities
            </h3>
            <p className="text-xs text-neutral-500">
              Identity binding management is coming soon in the next update.
            </p>
          </div>
        </div>

        <div className="lg:col-span-2">
          <div className="rounded-xl border border-neutral-200 bg-white p-8 shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
            <EditUserForm user={user} />
          </div>
        </div>
      </div>
    </div>
  );
}
