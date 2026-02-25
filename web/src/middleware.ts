import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { verifyAuthToken } from "./lib/auth";

/**
 * Middleware to protect routes that require authentication.
 * Verifies the JWT token from the access_token cookie.
 * 
 * Protected routes: /dashboard, /users, /cortex, /plugins, /audit
 * 
 * @param request The incoming HTTP request
 */
export async function middleware(request: NextRequest) {
  const token = request.cookies.get("access_token")?.value;

  if (!token) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  try {
    await verifyAuthToken(token);
    return NextResponse.next();
  } catch {
    const response = NextResponse.redirect(new URL("/login", request.url));
    response.cookies.delete("access_token");
    return response;
  }
}

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/users/:path*",
    "/cortex/:path*",
    "/plugins/:path*",
    "/audit/:path*",
  ],
};
