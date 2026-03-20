"use server";

import { revalidatePath } from "next/cache";
import { buildBearerHeaders, getServerAccessToken } from "@/lib/server-auth";

const API_URL = process.env.API_URL || "http://127.0.0.1:8000/api";

export async function updateSuggestionStatus(suggestionId: number, status: string) {
  const token = await getServerAccessToken();
  if (!token) return { error: "Unauthorized" };

  try {
    const response = await fetch(`${API_URL}/roadmap/${suggestionId}/status?new_status=${status}`, {
      method: "POST",
      headers: buildBearerHeaders(token),
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
  const token = await getServerAccessToken();
  if (!token) return { error: "Unauthorized" };

  try {
    const response = await fetch(`${API_URL}/roadmap/${suggestionId}`, {
      method: "DELETE",
      headers: buildBearerHeaders(token),
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
