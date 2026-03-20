"use server";

import { revalidatePath } from "next/cache";
import { buildBearerHeaders, getServerAccessToken } from "@/lib/server-auth";

const API_URL = process.env.API_URL || "http://127.0.0.1:8000/api";

/**
 * Delete a memory.
 * 
 * @param id The ID of the memory to delete
 */
export async function deleteMemory(id: number) {
  const token = await getServerAccessToken();
  if (!token) return { error: "Unauthorized" };

  try {
    const response = await fetch(`${API_URL}/memories/${id}`, {
      method: "DELETE",
      headers: buildBearerHeaders(token),
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      return { error: data.detail || "Failed to delete memory" };
    }

    revalidatePath("/cortex");
    return { success: true };
  } catch (error) {
    console.error("Delete memory error:", error);
    return { error: "Failed to connect to backend" };
  }
}
