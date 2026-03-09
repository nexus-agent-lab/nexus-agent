"use server";

import { cookies } from "next/headers";
import { revalidatePath } from "next/cache";
import { verifyAuthToken } from "@/lib/auth";

const API_URL = process.env.API_URL || "http://127.0.0.1:8000/api";

/**
 * Utility to get API key from session.
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
 * Delete a memory.
 * 
 * @param id The ID of the memory to delete
 */
export async function deleteMemory(id: number) {
  const apiKey = await getApiKey();
  if (!apiKey) return { error: "Unauthorized" };

  try {
    const response = await fetch(`${API_URL}/memories/${id}`, {
      method: "DELETE",
      headers: {
        "X-API-Key": apiKey,
      },
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

