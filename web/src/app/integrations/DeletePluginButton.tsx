"use client";

import { useState } from "react";
import { Trash2, Loader2 } from "lucide-react";
import { deletePlugin } from "@/app/actions/plugins";
import { toast } from "@/lib/toast";

interface DeletePluginButtonProps {
  pluginId: number;
  pluginName: string;
}

export default function DeletePluginButton({ pluginId, pluginName }: DeletePluginButtonProps) {
  const [loading, setLoading] = useState(false);

  const handleDelete = async () => {
    if (!confirm(`Are you sure you want to delete the plugin "${pluginName}"?`)) {
      return;
    }

    setLoading(true);
    try {
      const result = await deletePlugin(pluginId);
      if (result.error) {
        toast.error(result.error);
      } else {
        toast.success("Plugin deleted successfully");
      }
    } catch (error) {
      toast.error("Failed to delete plugin");
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={handleDelete}
      disabled={loading}
      className="text-rose-600 hover:text-rose-700 dark:text-rose-400 dark:hover:text-rose-300 transition-colors p-1 rounded-md hover:bg-rose-50 dark:hover:bg-rose-900/20 disabled:opacity-50"
      title="Delete Plugin"
    >
      {loading ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : (
        <Trash2 className="h-4 w-4" />
      )}
    </button>
  );
}
