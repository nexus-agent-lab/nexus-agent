"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Copy, ExternalLink, Loader2, MessageSquare, QrCode, RefreshCw, X } from "lucide-react";
import { toast } from "@/lib/toast";

type WeChatStatus = {
  connected: boolean;
  polling_active: boolean;
  token_hint?: string | null;
};

type BindingSession = {
  session_id: string;
  status: string;
  qrcode?: string | null;
  qrcode_img_content?: string | null;
  expires_in?: number | null;
  connected?: boolean | null;
  token_hint?: string | null;
  detail?: string | null;
};

interface WeChatBindingCardProps {
  token: string;
  userId: number;
}

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

function isTerminalStatus(status: string | undefined) {
  return status === "bound" || status === "failed" || status === "expired";
}

function isScanDetectedStatus(status: string | undefined) {
  return status === "scanned" || status === "confirmed";
}

function looksLikeDirectImage(value: string) {
  return (
    value.startsWith("data:image/") ||
    value.startsWith("<svg") ||
    /\.(png|jpg|jpeg|gif|webp|svg)(\?|$)/i.test(value)
  );
}

function buildQrPreviewSource(value: string | null | undefined) {
  if (!value) {
    return null;
  }
  if (value.startsWith("<svg")) {
    return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(value)}`;
  }
  if (looksLikeDirectImage(value)) {
    return value;
  }
  if (value.startsWith("http://") || value.startsWith("https://")) {
    return `https://api.qrserver.com/v1/create-qr-code/?size=320x320&data=${encodeURIComponent(value)}`;
  }
  return null;
}

export default function WeChatBindingCard({ token, userId }: WeChatBindingCardProps) {
  const [status, setStatus] = useState<WeChatStatus | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [bindingSession, setBindingSession] = useState<BindingSession | null>(null);
  const [starting, setStarting] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);

  const imageSource = useMemo(() => {
    return buildQrPreviewSource(bindingSession?.qrcode_img_content || null);
  }, [bindingSession]);

  const rawQrContent = bindingSession?.qrcode_img_content || null;
  const qrNeedsLinkFallback =
    !!rawQrContent &&
    (rawQrContent.startsWith("http://") || rawQrContent.startsWith("https://")) &&
    !looksLikeDirectImage(rawQrContent);

  const loadStatus = useCallback(async () => {
    setLoadingStatus(true);
    try {
      const response = await fetch(`${BACKEND_URL}/users/${userId}/wechat/status`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (!response.ok) {
        throw new Error("Failed to load WeChat binding status");
      }
      setStatus((await response.json()) as WeChatStatus);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to load WeChat status");
    } finally {
      setLoadingStatus(false);
    }
  }, [token, userId]);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  useEffect(() => {
    if (!bindingSession?.session_id || isTerminalStatus(bindingSession.status) || !modalOpen) {
      return;
    }

    const interval = window.setInterval(async () => {
      try {
        const response = await fetch(
          `${BACKEND_URL}/users/${userId}/wechat/bind/${bindingSession.session_id}`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
            cache: "no-store",
          }
        );
        if (!response.ok) {
          throw new Error("Failed to check WeChat binding status");
        }
        const next = (await response.json()) as BindingSession;
        setBindingSession((prev) => ({ ...prev, ...next }));
        if (next.status === "bound") {
          toast.success("WeChat connected successfully");
          loadStatus();
        }
      } catch (error) {
        toast.error(error instanceof Error ? error.message : "Failed to poll WeChat binding");
        window.clearInterval(interval);
      }
    }, 2000);

    return () => window.clearInterval(interval);
  }, [bindingSession?.session_id, bindingSession?.status, loadStatus, modalOpen, token, userId]);

  const handleStartBinding = async () => {
    setStarting(true);
    try {
      const response = await fetch(`${BACKEND_URL}/users/${userId}/wechat/bind`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      const payload = (await response.json()) as BindingSession | { detail?: string };
      if (!response.ok) {
        throw new Error(payload.detail || "Failed to start WeChat binding");
      }

      setBindingSession(payload as BindingSession);
      setModalOpen(true);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to start WeChat binding");
    } finally {
      setStarting(false);
    }
  };

  const handleCopyLink = async () => {
    if (!rawQrContent) {
      return;
    }
    try {
      await navigator.clipboard.writeText(rawQrContent);
      toast.success("WeChat link copied");
    } catch {
      toast.error("Failed to copy link");
    }
  };

  const handleOpenLink = () => {
    if (!rawQrContent) {
      return;
    }
    window.open(rawQrContent, "_blank", "noopener,noreferrer");
  };

  return (
    <>
      <div className="rounded-xl border border-neutral-200 bg-white p-6 shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="flex items-center gap-2 font-semibold">
              <MessageSquare className="h-4 w-4 text-neutral-400" />
              WeChat ClawBot
            </h3>
            <p className="mt-2 text-sm text-neutral-500">
              WeChat uses web-initiated QR binding. Telegram keeps the chat-side <code>/bind</code> flow.
            </p>
          </div>
          <button
            onClick={handleStartBinding}
            disabled={starting}
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-emerald-700 disabled:opacity-50"
          >
            {starting ? <Loader2 className="h-4 w-4 animate-spin" /> : <QrCode className="h-4 w-4" />}
            Bind WeChat
          </button>
        </div>

        <div className="mt-4 rounded-lg border border-dashed border-neutral-200 bg-neutral-50 p-4 text-sm dark:border-neutral-700 dark:bg-neutral-950">
          {loadingStatus ? (
            <div className="flex items-center gap-2 text-neutral-500">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading WeChat status...
            </div>
          ) : status?.connected ? (
            <div className="space-y-2">
              <div className="inline-flex rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-semibold text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400">
                Connected
              </div>
              <p className="text-neutral-600 dark:text-neutral-300">
                Token hint: <code>{status.token_hint || "hidden"}</code>
              </p>
              <p className="text-xs text-neutral-500">
                Polling: {status.polling_active ? "active" : "not started yet"}
              </p>
            </div>
          ) : (
            <p className="text-neutral-500">No WeChat session is bound to this user yet.</p>
          )}
        </div>
      </div>

      {modalOpen && bindingSession && (
        <div className="fixed inset-0 z-[110] flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="w-full max-w-xl overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-2xl dark:border-neutral-800 dark:bg-neutral-900">
            <div className="flex items-center justify-between border-b border-neutral-200 bg-neutral-50/70 p-5 dark:border-neutral-800 dark:bg-neutral-800/50">
              <div>
                <h2 className="text-xl font-bold">Bind WeChat</h2>
                <p className="text-sm text-neutral-500">Scan this QR code in WeChat to connect this user.</p>
              </div>
              <button
                onClick={() => setModalOpen(false)}
                className="rounded-full p-2 transition-colors hover:bg-neutral-200 dark:hover:bg-neutral-700"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-5 p-6">
              <div className="flex justify-center">
                {bindingSession.status === "bound" ? (
                  <div className="w-full max-w-md rounded-2xl border border-emerald-200 bg-emerald-50 p-6 text-center dark:border-emerald-900/40 dark:bg-emerald-950/30">
                    <div className="text-sm font-semibold text-emerald-700 dark:text-emerald-300">
                      WeChat connected successfully
                    </div>
                    <p className="mt-2 text-sm text-emerald-700/80 dark:text-emerald-200/80">
                      This user now has an active WeChat ClawBot session.
                    </p>
                    {bindingSession.token_hint && (
                      <p className="mt-3 text-xs text-emerald-800/80 dark:text-emerald-200/70">
                        Token hint: <code>{bindingSession.token_hint}</code>
                      </p>
                    )}
                  </div>
                ) : imageSource ? (
                  <div className="space-y-3">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={imageSource}
                      alt="WeChat QR code"
                      className="h-72 w-72 rounded-2xl border border-neutral-200 bg-white object-contain p-3 dark:border-neutral-800"
                    />
                    {qrNeedsLinkFallback && (
                      <div className="max-w-md rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800 dark:border-amber-900/40 dark:bg-amber-950/40 dark:text-amber-200">
                        WeChat returned a login link, not a direct image. The QR above is generated from that link for browser display.
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="w-full max-w-md rounded-xl border border-neutral-200 bg-neutral-50 p-5 text-center dark:border-neutral-700 dark:bg-neutral-950">
                    <div className="flex flex-col items-center gap-3 text-neutral-500 dark:text-neutral-400">
                      <Loader2 className="h-6 w-6 animate-spin" />
                      <div className="space-y-1">
                        <p className="text-sm font-medium text-neutral-700 dark:text-neutral-200">
                          {isScanDetectedStatus(bindingSession.status)
                            ? "QR scan detected. Finishing WeChat binding..."
                            : "Waiting for WeChat scan..."}
                        </p>
                        <p className="text-xs">
                          {bindingSession.qrcode
                            ? "The QR token is active even if the browser preview is temporarily unavailable."
                            : "The browser preview is temporarily unavailable, but the binding check is still running."}
                        </p>
                      </div>
                      {bindingSession.qrcode && (
                        <div className="w-full rounded-lg bg-white p-3 font-mono text-[11px] break-all dark:bg-black/30">
                          {bindingSession.qrcode}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {qrNeedsLinkFallback && rawQrContent && (
                <div className="rounded-xl border border-neutral-200 bg-neutral-50 p-4 text-xs text-neutral-500 dark:border-neutral-800 dark:bg-neutral-950">
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-medium text-neutral-700 dark:text-neutral-200">WeChat Login Link</span>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={handleCopyLink}
                        className="inline-flex items-center gap-1 rounded-lg border border-neutral-200 px-3 py-1.5 text-xs font-medium transition-colors hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-800"
                      >
                        <Copy className="h-3.5 w-3.5" />
                        Copy Link
                      </button>
                      <button
                        onClick={handleOpenLink}
                        className="inline-flex items-center gap-1 rounded-lg border border-neutral-200 px-3 py-1.5 text-xs font-medium transition-colors hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-800"
                      >
                        <ExternalLink className="h-3.5 w-3.5" />
                        Open Link
                      </button>
                    </div>
                  </div>
                  <div className="mt-3 break-all rounded-lg bg-white p-3 font-mono dark:bg-black/30">{rawQrContent}</div>
                  <p className="mt-3 text-[11px] text-neutral-500">
                    If scanning is inconvenient, open this link in a new tab or send it to your phone and open it in WeChat.
                  </p>
                </div>
              )}

              <div className="rounded-xl border border-neutral-200 bg-neutral-50 p-4 dark:border-neutral-800 dark:bg-neutral-950">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Status</span>
                  <span className="rounded-full bg-indigo-100 px-2.5 py-1 text-xs font-semibold text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400">
                    {bindingSession.status}
                  </span>
                </div>
                {bindingSession.detail && (
                  <p className="mt-2 text-xs text-neutral-500">{bindingSession.detail}</p>
                )}
                {bindingSession.token_hint && (
                  <p className="mt-2 text-xs text-neutral-500">
                    Token hint: <code>{bindingSession.token_hint}</code>
                  </p>
                )}
              </div>

              <div className="flex items-center justify-between">
                <button
                  onClick={loadStatus}
                  className="inline-flex items-center gap-2 rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium transition-colors hover:bg-neutral-50 dark:border-neutral-700 dark:hover:bg-neutral-800"
                >
                  <RefreshCw className="h-4 w-4" />
                  Refresh Status
                </button>
                {isTerminalStatus(bindingSession.status) && (
                  <button
                    onClick={handleStartBinding}
                    disabled={starting}
                    className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-emerald-700 disabled:opacity-50"
                  >
                    {starting ? <Loader2 className="h-4 w-4 animate-spin" /> : <QrCode className="h-4 w-4" />}
                    {bindingSession.status === "bound" ? "Reconnect" : "Generate New QR"}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
