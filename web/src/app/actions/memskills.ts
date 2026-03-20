"use server";

import { revalidatePath } from "next/cache";
import { buildBearerHeaders, getServerAccessToken } from "@/lib/server-auth";

const API_URL = process.env.API_URL || "http://127.0.0.1:8000/api";

/**
 * Approve a canary changelog.
 * 
 * @param changelogId The ID of the changelog to approve
 */
export async function approveChangelog(changelogId: number) {
  const token = await getServerAccessToken();
  if (!token) return { error: "Unauthorized" };

  try {
    const response = await fetch(`${API_URL}/memskills/changelogs/${changelogId}/approve`, {
      method: "POST",
      headers: buildBearerHeaders(token),
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
  const token = await getServerAccessToken();
  if (!token) return { error: "Unauthorized" };

  try {
    const response = await fetch(`${API_URL}/memskills/changelogs/${changelogId}/reject`, {
      method: "POST",
      headers: buildBearerHeaders(token),
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
