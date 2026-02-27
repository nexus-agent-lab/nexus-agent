"use server";

import { cookies } from "next/headers";
import { revalidatePath } from "next/cache";
import { verifyAuthToken } from "@/lib/auth";

const API_URL = process.env.API_URL || "http://127.0.0.1:8000";

/**
 * Helper to get the API key from the session.
 */
async function getApiKey() {
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;
  if (!token) return null;
  
  try {
    const payload = await verifyAuthToken(token);
    return payload.api_key as string;
  } catch {
    return null;
  }
}

/**
 * Server action to create a new plugin.
 * 
 * @param formData The plugin details (name, type, source_url, status, config)
 */
export async function createPlugin(formData: {
  name: string;
  type: string;
  source_url: string;
  status?: string;
  config?: Record<string, any>;
  manifest_id?: string;
  required_role?: string;
}) {
  const apiKey = await getApiKey();
  if (!apiKey) {
    return { error: "Unauthorized" };
  }

  try {
    const response = await fetch(`${API_URL}/plugins/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": apiKey,
      },
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
 * 
 * @param pluginId The ID of the plugin to update
 * @param formData The plugin details to update
 */
export async function updatePlugin(pluginId: number, formData: {
  name?: string;
  type?: string;
  source_url?: string;
  status?: string;
  config?: Record<string, any>;
  manifest_id?: string;
  required_role?: string;
}) {
  const apiKey = await getApiKey();
  if (!apiKey) {
    return { error: "Unauthorized" };
  }

  try {
    const response = await fetch(`${API_URL}/plugins/${pluginId}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": apiKey,
      },
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
 * 
 * @param pluginId The ID of the plugin to delete
 */
export async function deletePlugin(pluginId: number) {
  const apiKey = await getApiKey();
  if (!apiKey) {
    return { error: "Unauthorized" };
  }

  try {
    const response = await fetch(`${API_URL}/plugins/${pluginId}`, {
      method: "DELETE",
      headers: {
        "X-API-Key": apiKey,
      },
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
  const apiKey = await getApiKey();
  if (!apiKey) {
    return { error: "Unauthorized" };
  }

  try {
    const response = await fetch(`${API_URL}/admin/mcp/reload`, {
      method: "POST",
      headers: {
        "X-API-Key": apiKey,
      },
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
