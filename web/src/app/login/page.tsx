"use client";

import { useActionState, useEffect, useMemo, useRef, useState } from "react";
import { login } from "../actions/auth";

/**
 * Login page component.
 * Provides a form to authenticate via API key.
 */
export default function LoginPage() {
  const [state, formAction, isPending] = useActionState(login, null);
  const [telegramState, setTelegramState] = useState<{
    challengeId?: string;
    csrfToken?: string;
    deepLinkUrl?: string;
    error?: string;
    status?: "idle" | "starting" | "pending" | "approved" | "completing" | "expired" | "rejected_unbound";
  }>({ status: "idle" });
  const completionStartedRef = useRef(false);
  const backendUrl = useMemo(
    () => process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api",
    [],
  );

  async function startTelegramLogin() {
    setTelegramState({ status: "starting" });

    try {
      const response = await fetch(`${backendUrl}/auth/telegram/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      const data = await response.json();
      if (!response.ok) {
        setTelegramState({ status: "idle", error: data.detail || "Failed to start Telegram login" });
        return;
      }

      setTelegramState({
        challengeId: data.challenge_id,
        csrfToken: data.csrf_token,
        deepLinkUrl: data.telegram_deep_link_url,
        status: "pending",
      });
      completionStartedRef.current = false;
    } catch (error) {
      setTelegramState({ status: "idle", error: "Failed to connect to authentication server" });
    }
  }

  useEffect(() => {
    if (!telegramState.challengeId || !telegramState.csrfToken || telegramState.status !== "pending") {
      return;
    }

    let cancelled = false;

    const poll = async () => {
      try {
        const response = await fetch(
          `${backendUrl}/auth/telegram/status?challenge_id=${encodeURIComponent(telegramState.challengeId!)}`,
          { cache: "no-store" },
        );
        const data = await response.json();

        if (cancelled) {
          return;
        }

        if (data.status === "expired") {
          setTelegramState((current) => ({ ...current, status: "expired", error: "Telegram login expired. Please start again." }));
          return;
        }

        if (data.status === "rejected_unbound") {
          setTelegramState((current) => ({
            ...current,
            status: "rejected_unbound",
            error: "This Telegram account is not linked yet. Please bind it first, then try Telegram login again.",
          }));
          return;
        }

        if (data.status === "approved" && data.exchange_token && !completionStartedRef.current) {
          completionStartedRef.current = true;
          setTelegramState((current) => ({ ...current, status: "completing" }));

          const completeResponse = await fetch("/api/auth/telegram/complete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              challengeId: telegramState.challengeId,
              csrfToken: telegramState.csrfToken,
              exchangeToken: data.exchange_token,
            }),
          });
          const completeData = await completeResponse.json();

          if (!completeResponse.ok) {
            setTelegramState((current) => ({
              ...current,
              status: "pending",
              error: completeData.error || "Failed to complete Telegram login",
            }));
            completionStartedRef.current = false;
            return;
          }

          window.location.href = completeData.redirectTo || "/dashboard";
        }
      } catch (error) {
        if (!cancelled) {
          setTelegramState((current) => ({ ...current, error: "Failed to poll Telegram login status" }));
        }
      }
    };

    poll();
    const intervalId = window.setInterval(poll, 2000);
    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [backendUrl, telegramState.challengeId, telegramState.csrfToken, telegramState.status]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="w-full max-w-md space-y-8 rounded-lg bg-white p-8 shadow-md">
        <div className="flex flex-col items-center">
          <img 
            src="https://avatars.githubusercontent.com/u/257899476" 
            alt="Nexus Logo" 
            className="h-16 w-16 rounded-xl shadow-sm mb-4"
          />
          <h2 className="text-center text-3xl font-extrabold text-gray-900">
            Sign in to Nexus Agent
          </h2>
          <p className="mt-2 text-center text-sm text-gray-500">
            Use API key login or confirm a web handoff from your linked Telegram account.
          </p>
        </div>
        
        <form action={formAction} className="mt-8 space-y-6">
          {state?.error && (
            <div className="rounded-md bg-red-50 p-4">
              <div className="text-sm text-red-700">{state.error}</div>
            </div>
          )}
          
          <div className="-space-y-px rounded-md shadow-sm">
            <div>
              <label htmlFor="username" className="sr-only">
                Username
              </label>
              <input
                id="username"
                name="username"
                type="text"
                required
                className="relative block w-full appearance-none rounded-none rounded-t-md border border-gray-300 px-3 py-2 text-gray-900 placeholder-gray-500 focus:z-10 focus:border-indigo-500 focus:outline-none focus:ring-indigo-500 sm:text-sm"
                placeholder="Username"
              />
            </div>
            <div>
              <label htmlFor="password" className="sr-only">
                API Key (Password)
              </label>
              <input
                id="password"
                name="password"
                type="password"
                required
                className="relative block w-full appearance-none rounded-none rounded-b-md border border-gray-300 px-3 py-2 text-gray-900 placeholder-gray-500 focus:z-10 focus:border-indigo-500 focus:outline-none focus:ring-indigo-500 sm:text-sm"
                placeholder="API Key"
              />
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={isPending}
              className="group relative flex w-full justify-center rounded-md border border-transparent bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50"
            >
              {isPending ? "Signing in..." : "Sign in"}
            </button>
          </div>

          <div className="relative py-2">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-200" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-white px-2 text-gray-400">Or</span>
            </div>
          </div>

          <div className="space-y-3">
            <button
              type="button"
              onClick={startTelegramLogin}
              disabled={telegramState.status === "starting" || telegramState.status === "completing"}
              className="group relative flex w-full justify-center rounded-md border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-medium text-blue-700 hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
            >
              {telegramState.status === "starting" ? "Starting Telegram login..." : "Continue with Telegram"}
            </button>

            {telegramState.error && (
              <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
                {telegramState.error}
              </div>
            )}

            {telegramState.deepLinkUrl && (
              <div className="rounded-md border border-blue-100 bg-blue-50 p-4 text-sm text-blue-900">
                <p className="font-medium">Telegram handoff started</p>
                <ol className="mt-2 list-decimal space-y-1 pl-5 text-blue-800">
                  <li>Open the link below in Telegram.</li>
                  <li>Confirm login from your already linked Telegram account.</li>
                  <li>Come back here and this page will continue automatically.</li>
                </ol>
                <a
                  href={telegramState.deepLinkUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-3 inline-block break-all text-sm font-medium text-blue-700 underline"
                >
                  Open Telegram login link
                </a>
                <p className="mt-3 text-xs text-blue-700">
                  Status: {telegramState.status === "completing" ? "Completing sign-in..." : "Waiting for Telegram confirmation..."}
                </p>
              </div>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
