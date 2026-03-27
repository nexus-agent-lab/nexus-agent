import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { verifyAuthToken } from "./lib/auth";

/**
 * Middleware to protect routes that require authentication.
 * Verifies the JWT token from the access_token cookie.
 * 
 * Protected routes: /dashboard, /users, /cortex, /integrations, /audit, /network, /roadmap
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
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    console.error(`Middleware Auth Error for ${request.nextUrl.pathname}:`, message);
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
    "/integrations/:path*",
    "/audit/:path*",
    "/network/:path*",
    "/roadmap/:path*",
  ],
};
