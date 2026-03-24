"use client";

import { useEffect, useState } from "react";

import { refreshSession } from "@/app/actions/auth";
import { handleUnauthorizedSession } from "@/lib/client-auth";

const REFRESH_WINDOW_MS = 60 * 60 * 1000;
const RETRY_DELAY_MS = 5 * 60 * 1000;
const MIN_DELAY_MS = 30 * 1000;

function getRefreshDelay(exp: number) {
  const refreshAt = exp * 1000 - REFRESH_WINDOW_MS;
  return Math.max(MIN_DELAY_MS, refreshAt - Date.now());
}

export default function SessionKeepAlive({ initialExp }: { initialExp: number | null }) {
  const [expiresAt, setExpiresAt] = useState<number | null>(initialExp);

  useEffect(() => {
    setExpiresAt(initialExp);
  }, [initialExp]);

  useEffect(() => {
    if (!expiresAt) {
      return;
    }

    let cancelled = false;
    let timeoutId: number | null = null;

    const scheduleRefresh = (delay: number) => {
      timeoutId = window.setTimeout(runRefresh, delay);
    };

    const runRefresh = async () => {
      if (document.visibilityState === "hidden") {
        scheduleRefresh(RETRY_DELAY_MS);
        return;
      }

      const result = await refreshSession();
      if (cancelled) {
        return;
      }

      if (result.expired) {
        await handleUnauthorizedSession("Session expired. Please log in again.");
        return;
      }

      if (typeof result.exp === "number") {
        setExpiresAt(result.exp);
        return;
      }

      scheduleRefresh(RETRY_DELAY_MS);
    };

    scheduleRefresh(getRefreshDelay(expiresAt));
    return () => {
      cancelled = true;
      if (timeoutId !== null) {
        window.clearTimeout(timeoutId);
      }
    };
  }, [expiresAt]);

  return null;
}
