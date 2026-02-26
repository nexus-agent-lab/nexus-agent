"use client";

import { useState } from "react";
import { CheckCircle2, XCircle, Trash2, Lightbulb, Loader2 } from "lucide-react";
import { updateSuggestionStatus, deleteSuggestion } from "../actions/roadmap";
import { toast } from "@/lib/toast";

interface RoadmapActionsProps {
  id: number;
  status: string;
  isAdmin: boolean;
}

export default function RoadmapActions({ id, status, isAdmin }: RoadmapActionsProps) {
  const [loading, setLoading] = useState<string | null>(null);

  if (!isAdmin) return null;

  const handleUpdate = async (newStatus: string) => {
    setLoading(newStatus);
    const result = await updateSuggestionStatus(id, newStatus);
    if (result.error) {
      toast.error(result.error);
    } else {
      toast.success(`Suggestion marked as ${newStatus}`);
    }
    setLoading(null);
  };

  const handleDelete = async () => {
    if (!confirm("Are you sure you want to delete this suggestion?")) return;
    setLoading("delete");
    const result = await deleteSuggestion(id);
    if (result.error) {
      toast.error(result.error);
    } else {
      toast.success("Suggestion deleted");
    }
    setLoading(null);
  };

  return (
    <div className="flex items-center gap-1">
      {status === "pending" && (
        <>
          <button
            onClick={() => handleUpdate("approved")}
            disabled={!!loading}
            className="rounded-md p-1.5 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 disabled:opacity-50"
            title="Approve"
          >
            {loading === "approved" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Lightbulb className="h-4 w-4" />}
          </button>
          <button
            onClick={() => handleUpdate("rejected")}
            disabled={!!loading}
            className="rounded-md p-1.5 text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-900/20 disabled:opacity-50"
            title="Reject"
          >
            {loading === "rejected" ? <Loader2 className="h-4 w-4 animate-spin" /> : <XCircle className="h-4 w-4" />}
          </button>
        </>
      )}
      
      {status === "approved" && (
        <button
          onClick={() => handleUpdate("implemented")}
          disabled={!!loading}
          className="rounded-md p-1.5 text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 disabled:opacity-50"
          title="Mark as Done"
        >
          {loading === "implemented" ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
        </button>
      )}

      <button
        onClick={handleDelete}
        disabled={!!loading}
        className="rounded-md p-1.5 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-600 dark:hover:bg-neutral-800 disabled:opacity-50"
        title="Delete"
      >
        {loading === "delete" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
      </button>
    </div>
  );
}
