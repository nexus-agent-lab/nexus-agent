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

/**
 * Server action to create a new user.
 */
export async function createUser(formData: { username: string; role: string }) {
  const apiKey = await getApiKey();
  if (!apiKey) {
    return { error: "Unauthorized" };
  }

  try {
    const response = await fetch(`${API_URL}/users/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": apiKey,
      },
      body: JSON.stringify(formData),
    });

    if (!response.ok) {
      const data = await response.json();
      return { error: data.detail || "Failed to create user" };
    }

    const newUser = await response.json();
    revalidatePath("/users");
return { data: newUser };
  } catch (error) {
    console.error("Create user error:", error);
    return { error: "Failed to connect to backend" };
  }
}

/**
 * Server action to update an existing user.
 */
export async function updateUser(userId: number, formData: {
  username?: string;
  role?: string;
  language?: string;
  timezone?: string;
  notes?: string;
  policy?: any;
}) {
  const apiKey = await getApiKey();
  if (!apiKey) {
    return { error: "Unauthorized" };
  }

  try {
    const response = await fetch(`${API_URL}/users/${userId}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": apiKey,
      },
      body: JSON.stringify(formData),
    });

    if (!response.ok) {
      const data = await response.json();
      return { error: data.detail || "Failed to update user" };
    }

    const updatedUser = await response.json();
    revalidatePath("/users");
    revalidatePath(`/users/${userId}`);
    return { data: updatedUser };
  } catch (error) {
    console.error("Update user error:", error);
    return { error: "Failed to connect to backend" };
  }
}
