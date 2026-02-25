"use server";

import { cookies } from "next/headers";
import { revalidatePath } from "next/cache";
import { verifyAuthToken } from "@/lib/auth";

const API_URL = process.env.API_URL || "http://127.0.0.1:8000";

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
 * Approve a canary changelog.
 * 
 * @param changelogId The ID of the changelog to approve
 */
export async function approveChangelog(changelogId: number) {
  const apiKey = await getApiKey();
  if (!apiKey) return { error: "Unauthorized" };

  try {
    const response = await fetch(`${API_URL}/memskills/changelogs/${changelogId}/approve`, {
      method: "POST",
      headers: {
        "X-API-Key": apiKey,
      },
    });

    if (!response.ok) {
      const data = await response.json();
      return { error: data.detail || "Failed to approve changelog" };
    }

    revalidatePath("/cortex");
    return { success: true };
  } catch (error) {
    console.error("Approve changelog error:", error);
    return { error: "Failed to connect to backend" };
  }
}

/**
 * Reject a canary changelog.
 * 
 * @param changelogId The ID of the changelog to reject
 */
export async function rejectChangelog(changelogId: number) {
  const apiKey = await getApiKey();
  if (!apiKey) return { error: "Unauthorized" };

  try {
    const response = await fetch(`${API_URL}/memskills/changelogs/${changelogId}/reject`, {
      method: "POST",
      headers: {
        "X-API-Key": apiKey,
      },
    });

    if (!response.ok) {
      const data = await response.json();
      return { error: data.detail || "Failed to reject changelog" };
    }

    revalidatePath("/cortex");
    return { success: true };
  } catch (error) {
    console.error("Reject changelog error:", error);
    return { error: "Failed to connect to backend" };
  }
}
