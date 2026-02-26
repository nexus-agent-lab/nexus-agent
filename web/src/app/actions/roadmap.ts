"use server";

import { cookies } from "next/headers";
import { revalidatePath } from "next/cache";
import { verifyAuthToken } from "@/lib/auth";

const API_URL = process.env.API_URL || "http://127.0.0.1:8000";

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

export async function updateSuggestionStatus(suggestionId: number, status: string) {
  const apiKey = await getApiKey();
  if (!apiKey) return { error: "Unauthorized" };

  try {
    const response = await fetch(`${API_URL}/roadmap/${suggestionId}/status?new_status=${status}`, {
      method: "POST",
      headers: { "X-API-Key": apiKey },
    });

    if (!response.ok) {
      const data = await response.json();
      return { error: data.detail || "Failed to update status" };
    }

    revalidatePath("/roadmap");
    return { success: true };
  } catch (error) {
    return { error: "Failed to connect to backend" };
  }
}

export async function deleteSuggestion(suggestionId: number) {
  const apiKey = await getApiKey();
  if (!apiKey) return { error: "Unauthorized" };

  try {
    const response = await fetch(`${API_URL}/roadmap/${suggestionId}`, {
      method: "DELETE",
      headers: { "X-API-Key": apiKey },
    });

    if (!response.ok) {
      const data = await response.json();
      return { error: data.detail || "Failed to delete suggestion" };
    }

    revalidatePath("/roadmap");
    return { success: true };
  } catch (error) {
    return { error: "Failed to connect to backend" };
  }
}
