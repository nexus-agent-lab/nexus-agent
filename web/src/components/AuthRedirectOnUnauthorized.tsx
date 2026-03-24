"use client";

import { useEffect } from "react";

import { handleUnauthorizedSession } from "@/lib/client-auth";

function getAuthorizationHeader(
  input: RequestInfo | URL,
  init?: RequestInit,
) {
  if (init?.headers) {
    const headers = new Headers(init.headers);
    return headers.get("Authorization");
  }

  if (input instanceof Request) {
    return input.headers.get("Authorization");
  }

  return null;
}

export default function AuthRedirectOnUnauthorized() {
  useEffect(() => {
    const originalFetch = window.fetch.bind(window);

    window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      const response = await originalFetch(input, init);
      const authorization = getAuthorizationHeader(input, init);

      if (response.status === 401 && authorization?.startsWith("Bearer ")) {
        void handleUnauthorizedSession("Session expired. Please log in again.");
      }

      return response;
    };

    return () => {
      window.fetch = originalFetch;
    };
  }, []);

  return null;
}
