"use server";

import { revalidatePath } from "next/cache";
import { buildBearerHeaders, getServerAccessToken } from "@/lib/server-auth";

const API_URL = process.env.API_URL || "http://127.0.0.1:8000/api";

/**
 * Server action to create a new user.
 */
export async function createUser(formData: { username: string; role: string }) {
  const token = await getServerAccessToken();
  if (!token) {
    return { error: "Unauthorized" };
  }

  try {
    const response = await fetch(`${API_URL}/users/`, {
      method: "POST",
      headers: buildBearerHeaders(token, { "Content-Type": "application/json" }),
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
  groups?: string[];

}) {
  const token = await getServerAccessToken();
  if (!token) {
    return { error: "Unauthorized" };
  }

  try {
    const response = await fetch(`${API_URL}/users/${userId}`, {
      method: "PATCH",
      headers: buildBearerHeaders(token, { "Content-Type": "application/json" }),
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
