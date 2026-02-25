"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createUser } from "@/app/actions/users";
import { UserPlus, Key, Loader2, AlertCircle, CheckCircle2 } from "lucide-react";

interface CreateUserFormProps {
  onSuccess?: () => void;
}

export default function CreateUserForm({ onSuccess }: CreateUserFormProps) {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [role, setRole] = useState("user");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generatedKey, setGeneratedKey] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setGeneratedKey(null);

    try {
      const result = await createUser({ username, role });

      if (result.error) {
        throw new Error(result.error);
      }

      const newUser = result.data;
      setGeneratedKey(newUser.api_key);
      setUsername("");
      setRole("user");
      onSuccess?.();
      router.refresh();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-6 shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
      <div className="mb-6 flex items-center gap-2">
        <UserPlus className="h-5 w-5 text-indigo-600" />
        <h2 className="text-xl font-semibold">Create New User</h2>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="mb-1 block text-sm font-medium text-neutral-700 dark:text-neutral-300">
            Username
          </label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="w-full rounded-lg border border-neutral-300 bg-white px-4 py-2 text-sm focus:border-indigo-500 focus:outline-none dark:border-neutral-700 dark:bg-neutral-800"
            placeholder="e.g. alice"
            required
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-neutral-700 dark:text-neutral-300">
            Role
          </label>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="w-full rounded-lg border border-neutral-300 bg-white px-4 py-2 text-sm focus:border-indigo-500 focus:outline-none dark:border-neutral-700 dark:bg-neutral-800"
          >
            <option value="user">User</option>
            <option value="admin">Admin</option>
            <option value="guest">Guest</option>
          </select>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <UserPlus className="h-4 w-4" />
          )}
          Create User
        </button>
      </form>

      {error && (
        <div className="mt-4 flex items-center gap-2 rounded-lg bg-rose-50 p-3 text-sm text-rose-600 dark:bg-rose-900/20 dark:text-rose-400">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      )}

      {generatedKey && (
        <div className="mt-4 rounded-lg bg-emerald-50 p-4 dark:bg-emerald-900/20">
          <div className="mb-2 flex items-center gap-2 text-sm font-medium text-emerald-700 dark:text-emerald-400">
            <CheckCircle2 className="h-4 w-4" />
            User created successfully!
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-xs text-neutral-500 dark:text-neutral-400">
              Save this API Key. It won&apos;t be shown again.
            </span>
            <div className="flex items-center gap-2 rounded bg-white p-2 font-mono text-sm dark:bg-black">
              <Key className="h-3 w-3 text-neutral-400" />
              <span className="break-all">{generatedKey}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
