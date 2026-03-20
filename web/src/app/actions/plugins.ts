"use server";

import { revalidatePath } from "next/cache";
import { buildBearerHeaders, getServerAccessToken } from "@/lib/server-auth";

const API_URL = process.env.API_URL || "http://127.0.0.1:8000/api";

/**
 * Server action to create a new plugin.
 */
export async function createPlugin(formData: {
  name: string;
  type: string;
  source_url: string;
  status?: string;
  config?: Record<string, any>;
  manifest_id?: string;
  required_role?: string;
  allowed_groups?: string[];
  secrets?: Record<string, string>;
}) {
  const token = await getServerAccessToken();
  if (!token) {
    return { error: "Unauthorized" };
  }

  try {
    const response = await fetch(`${API_URL}/plugins/`, {
      method: "POST",
      headers: buildBearerHeaders(token, { "Content-Type": "application/json" }),
      body: JSON.stringify(formData),
    });

    if (!response.ok) {
      const data = await response.json();
      return { error: data.detail || "Failed to create plugin" };
    }

    const newPlugin = await response.json();
    revalidatePath("/integrations");
    return { data: newPlugin };
  } catch (error) {
    console.error("Create plugin error:", error);
    return { error: "Failed to connect to backend" };
  }
}

/**
 * Server action to update an existing plugin.
 */
export async function updatePlugin(pluginId: number, formData: {
  name?: string;
  type?: string;
  source_url?: string;
  status?: string;
  config?: Record<string, any>;
  manifest_id?: string;
  required_role?: string;
  allowed_groups?: string[];
  secrets?: Record<string, string>;
}) {
  const token = await getServerAccessToken();
  if (!token) {
    return { error: "Unauthorized" };
  }

  try {
    const response = await fetch(`${API_URL}/plugins/${pluginId}`, {
      method: "PATCH",
      headers: buildBearerHeaders(token, { "Content-Type": "application/json" }),
      body: JSON.stringify(formData),
    });

    if (!response.ok) {
      const data = await response.json();
      return { error: data.detail || "Failed to update plugin" };
    }

    const updatedPlugin = await response.json();
    revalidatePath("/integrations");
    return { data: updatedPlugin };
  } catch (error) {
    console.error("Update plugin error:", error);
    return { error: "Failed to connect to backend" };
  }
}

/**
 * Server action to delete a plugin.
 */
export async function deletePlugin(pluginId: number) {
  const token = await getServerAccessToken();
  if (!token) {
    return { error: "Unauthorized" };
  }

  try {
    const response = await fetch(`${API_URL}/plugins/${pluginId}`, {
      method: "DELETE",
      headers: buildBearerHeaders(token),
    });

    if (!response.ok) {
      const data = await response.json();
      return { error: data.detail || "Failed to delete plugin" };
    }

    revalidatePath("/integrations");
    return { success: true };
  } catch (error) {
    console.error("Delete plugin error:", error);
    return { error: "Failed to connect to backend" };
  }
}

/**
 * Server action to reload MCP servers.
 */
export async function reloadMCP() {
  const token = await getServerAccessToken();
  if (!token) {
    return { error: "Unauthorized" };
  }

  try {
    const response = await fetch(`${API_URL}/admin/mcp/reload`, {
      method: "POST",
      headers: buildBearerHeaders(token),
    });

    if (!response.ok) {
      const data = await response.json();
      return { error: data.detail || "Failed to reload MCP servers" };
    }

    const result = await response.json();
    revalidatePath("/integrations");
    return { data: result };
  } catch (error) {
    console.error("Reload MCP error:", error);
    return { error: "Failed to connect to backend" };
  }
}
