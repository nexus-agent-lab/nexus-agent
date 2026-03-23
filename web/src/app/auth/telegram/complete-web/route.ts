import { cookies } from "next/headers";
import { NextResponse } from "next/server";

export async function POST(request: Request) {
  const body = await request.json();
  const backendUrl = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

  const response = await fetch(`${backendUrl}/auth/telegram/complete`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      challenge_id: body.challengeId,
      exchange_token: body.exchangeToken,
      csrf_token: body.csrfToken,
    }),
  });

  const data = await response.json();
  if (!response.ok) {
    return NextResponse.json({ error: data.detail || "Failed to complete Telegram login" }, { status: response.status });
  }

  const cookieStore = await cookies();
  cookieStore.set("access_token", data.access_token, {
    httpOnly: true,
    secure: process.env.REQUIRE_HTTPS === "true",
    sameSite: "lax",
    path: "/",
    maxAge: 24 * 60 * 60,
  });

  return NextResponse.json({ ok: true, redirectTo: "/dashboard" });
}
