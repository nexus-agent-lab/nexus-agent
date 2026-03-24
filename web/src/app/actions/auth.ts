"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { verifyAuthToken } from "@/lib/auth";

const DEFAULT_SESSION_MAX_AGE = 24 * 60 * 60;

function getSessionMaxAge(data: { expires_in?: unknown }) {
  return typeof data.expires_in === "number" ? data.expires_in : DEFAULT_SESSION_MAX_AGE;
}

async function writeAccessTokenCookie(accessToken: string, maxAge: number) {
  const cookieStore = await cookies();
  cookieStore.set("access_token", accessToken, {
    httpOnly: true,
    secure: process.env.REQUIRE_HTTPS === "true",
    sameSite: "lax",
    path: "/",
    maxAge,
  });
}

/**
 * Server action to handle user login.
 * Calls the backend /auth/token endpoint to authenticate.
 * 
 * @param formData The form data submitted by the user
 * @returns An object containing an error message if failed
 */
export async function login(prevState: { error?: string } | null | undefined, formData: FormData) {
  const username = formData.get("username") as string;
  const password = formData.get("password") as string;

  if (!username || !password) {
    return { error: "Username and password (API key) are required" };
  }

  try {
    const backendUrl = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
    
    const params = new URLSearchParams();
    params.append("username", username);
    params.append("password", password);

    const response = await fetch(`${backendUrl}/auth/token`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: params,
    });

    if (!response.ok) {
      if (response.status === 401) {
        return { error: "Invalid username or API key" };
      }
      return { error: "An error occurred while logging in" };
    }

    const data = await response.json();
    
    await writeAccessTokenCookie(data.access_token, getSessionMaxAge(data));

  } catch (error) {
    console.error("Login action error:", error);
    return { error: "Failed to connect to authentication server" };
  }

  redirect("/dashboard");
}

/**
 * Server action to log out the user by deleting the access_token cookie.
 */
export async function logout() {
  await clearSession();
  redirect("/login");
}

/**
 * Server action to clear the access_token cookie without redirecting.
 * Useful when the client needs to recover from an expired session first.
 */
export async function clearSession() {
  const cookieStore = await cookies();
  cookieStore.delete("access_token");
}

export async function refreshSession() {
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;
  if (!token) {
    await clearSession();
    return { expired: true };
  }

  try {
    await verifyAuthToken(token);
  } catch {
    await clearSession();
    return { expired: true };
  }

  try {
    const backendUrl = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
    const response = await fetch(`${backendUrl}/auth/refresh`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      cache: "no-store",
    });

    if (!response.ok) {
      if (response.status === 401) {
        await clearSession();
        return { expired: true };
      }
      return { error: "Failed to refresh session" };
    }

    const data = await response.json();
    await writeAccessTokenCookie(data.access_token, getSessionMaxAge(data));
    const payload = await verifyAuthToken(data.access_token);
    return { exp: payload.exp ?? null };
  } catch (error) {
    console.error("Refresh session error:", error);
    return { error: "Failed to refresh session" };
  }
}
