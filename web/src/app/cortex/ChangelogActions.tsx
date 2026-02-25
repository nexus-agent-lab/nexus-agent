"use client";

import { useState } from "react";
import { Check, X, Loader2 } from "lucide-react";
import { approveChangelog, rejectChangelog } from "@/app/actions/memskills";
import { cn } from "@/lib/utils";

interface ChangelogActionsProps {
  id: number;
  status: string;
}

/**
 * Client component for approving or rejecting a changelog.
 */
export default function ChangelogActions({ id, status }: ChangelogActionsProps) {
  const [loading, setLoading] = useState<"approve" | "reject" | null>(null);

  if (status !== "canary") {
    return (
      <span className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
        status === "approved" 
          ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
          : "bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400"
      )}>
        {status.toUpperCase()}
      </span>
    );
  }

  const handleApprove = async () => {
    setLoading("approve");
    await approveChangelog(id);
    setLoading(null);
  };

  const handleReject = async () => {
    setLoading("reject");
    await rejectChangelog(id);
    setLoading(null);
  };

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={handleApprove}
        disabled={loading !== null}
        className="inline-flex items-center gap-1 rounded-md bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-700 hover:bg-emerald-100 disabled:opacity-50 dark:bg-emerald-900/20 dark:text-emerald-400 dark:hover:bg-emerald-900/30"
      >
        {loading === "approve" ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />}
        Approve
      </button>
      <button
        onClick={handleReject}
        disabled={loading !== null}
        className="inline-flex items-center gap-1 rounded-md bg-rose-50 px-2 py-1 text-xs font-medium text-rose-700 hover:bg-rose-100 disabled:opacity-50 dark:bg-rose-900/20 dark:text-rose-400 dark:hover:bg-rose-900/30"
      >
        {loading === "reject" ? <Loader2 className="h-3 w-3 animate-spin" /> : <X className="h-3 w-3" />}
        Reject
      </button>
    </div>
  );
}
