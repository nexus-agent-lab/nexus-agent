"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { updateUser } from "@/app/actions/users";
import { Save, Loader2, AlertCircle, CheckCircle2, ShieldAlert } from "lucide-react";
import { toast } from "@/lib/toast";


interface User {
  id: number;
  username: string;
  role: string;
  language: string;
  timezone?: string;
  notes?: string;
  policy: Record<string, any>;
}

interface EditUserFormProps {
  user: User;
}

/**
 * EditUserForm component provides a form for administrators to update user details
 * and modify the security policy JSON object.
 */
export default function EditUserForm({ user }: EditUserFormProps) {

  const router = useRouter();
  const [formData, setFormData] = useState({
    username: user.username,
    role: user.role,
    language: user.language,
    timezone: user.timezone || "",
    notes: user.notes || "",
  });
  const [policyText, setPolicyText] = useState(JSON.stringify(user.policy, null, 2));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(false);

    let parsedPolicy;
    try {
      parsedPolicy = JSON.parse(policyText);
    } catch (err) {
      setError("Invalid JSON in Policy field");
      setLoading(false);
      return;
    }

    try {
      const result = await updateUser(user.id, {
        ...formData,
        policy: parsedPolicy,
      });

      if (result.error) {
        toast.error(result.error);
        throw new Error(result.error);
      }

      setSuccess(true);
      toast.success("User changes saved successfully!");
      router.refresh();
      // Hide success message after 3 seconds
      setTimeout(() => setSuccess(false), 3000);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="grid gap-6 md:grid-cols-2">
        <div className="space-y-4">
          <h3 className="text-lg font-medium">Basic Information</h3>
          
          <div>
            <label className="mb-1 block text-sm font-medium text-neutral-700 dark:text-neutral-300">
              Username
            </label>
            <input
              type="text"
              name="username"
              value={formData.username}
              onChange={handleChange}
              className="w-full rounded-lg border border-neutral-300 bg-white px-4 py-2 text-sm focus:border-indigo-500 focus:outline-none dark:border-neutral-700 dark:bg-neutral-800"
              required
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-neutral-700 dark:text-neutral-300">
              Role
            </label>
            <select
              name="role"
              value={formData.role}
              onChange={handleChange}
              className="w-full rounded-lg border border-neutral-300 bg-white px-4 py-2 text-sm focus:border-indigo-500 focus:outline-none dark:border-neutral-700 dark:bg-neutral-800"
            >
              <option value="user">User</option>
              <option value="admin">Admin</option>
              <option value="guest">Guest</option>
            </select>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-neutral-700 dark:text-neutral-300">
              Language
            </label>
            <input
              type="text"
              name="language"
              value={formData.language}
              onChange={handleChange}
              className="w-full rounded-lg border border-neutral-300 bg-white px-4 py-2 text-sm focus:border-indigo-500 focus:outline-none dark:border-neutral-700 dark:bg-neutral-800"
              placeholder="e.g. en, ko"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-neutral-700 dark:text-neutral-300">
              Timezone
            </label>
            <input
              type="text"
              name="timezone"
              value={formData.timezone}
              onChange={handleChange}
              className="w-full rounded-lg border border-neutral-300 bg-white px-4 py-2 text-sm focus:border-indigo-500 focus:outline-none dark:border-neutral-700 dark:bg-neutral-800"
              placeholder="e.g. UTC, Asia/Seoul"
            />
          </div>
        </div>

        <div className="space-y-4">
          <h3 className="text-lg font-medium">Additional Details</h3>
          
          <div>
            <label className="mb-1 block text-sm font-medium text-neutral-700 dark:text-neutral-300">
              Notes
            </label>
            <textarea
              name="notes"
              value={formData.notes}
              onChange={handleChange}
              rows={5}
              className="w-full rounded-lg border border-neutral-300 bg-white px-4 py-2 text-sm focus:border-indigo-500 focus:outline-none dark:border-neutral-700 dark:bg-neutral-800"
              placeholder="User notes..."
            />
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <ShieldAlert className="h-5 w-5 text-rose-500" />
          <h3 className="text-lg font-medium">Policy Configuration (JSON)</h3>
        </div>
        <p className="text-sm text-neutral-500 dark:text-neutral-400">
          Advanced security policies and restrictions for this user.
        </p>
        <textarea
          value={policyText}
          onChange={(e) => setPolicyText(e.target.value)}
          rows={10}
          className="w-full rounded-lg border border-neutral-300 bg-neutral-50 p-4 font-mono text-sm focus:border-indigo-500 focus:outline-none dark:border-neutral-700 dark:bg-neutral-950"
          placeholder='{ "key": "value" }'
        />
      </div>

      <div className="flex items-center justify-between pt-4">
        <div className="flex-1 pr-4">
          {error && (
            <div className="flex items-center gap-2 text-sm text-rose-600 dark:text-rose-400">
              <AlertCircle className="h-4 w-4" />
              {error}
            </div>
          )}
          {success && (
            <div className="flex items-center gap-2 text-sm text-emerald-600 dark:text-emerald-400">
              <CheckCircle2 className="h-4 w-4" />
              Changes saved successfully!
            </div>
          )}
        </div>

        <button
          type="submit"
          disabled={loading}
          className="flex items-center gap-2 rounded-lg bg-indigo-600 px-6 py-2 text-sm font-semibold text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Save className="h-4 w-4" />
          )}
          Save Changes
        </button>
      </div>
    </form>
  );
}
