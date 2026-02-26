"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

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
    const backendUrl = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    
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
    
    const cookieStore = await cookies();
    cookieStore.set("access_token", data.access_token, {
      httpOnly: true,
      // For local AI OS deployments, disable Secure flag unless explicitly requested via REQUIRE_HTTPS.
      // This prevents the cookie from being dropped on local HTTP connections.
      secure: process.env.REQUIRE_HTTPS === "true",
      sameSite: "lax",
      path: "/",
      maxAge: 24 * 60 * 60,
    });

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
  const cookieStore = await cookies();
  cookieStore.delete("access_token");
  redirect("/login");
}
