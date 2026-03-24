import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { cookies } from "next/headers";
import { verifyAuthToken } from "@/lib/auth";
import type { UserPayload } from "@/lib/auth";
import "./globals.css";
import AuthRedirectOnUnauthorized from "@/components/AuthRedirectOnUnauthorized";
import Layout from "@/components/Layout";
import SessionKeepAlive from "@/components/SessionKeepAlive";
import ToastContainer from "@/components/ToastContainer";
import { getDictionary, getServerLocale } from "@/lib/locale";


const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Nexus Agent",
  description: "Private, intelligent control center",
  icons: {
    icon: "https://avatars.githubusercontent.com/u/257899476",
  },
};

function isUserPayload(value: unknown): value is UserPayload {
  if (!value || typeof value !== "object") {
    return false;
  }

  const payload = value as Record<string, unknown>;
  return (
    typeof payload.sub === "string" &&
    typeof payload.username === "string" &&
    typeof payload.role === "string" &&
    typeof payload.api_key === "string" &&
    typeof payload.exp === "number"
  );
}

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;
  const locale = await getServerLocale();
  const dict = getDictionary(locale);
  let user = null;

  if (token) {
    try {
      const payload = await verifyAuthToken(token);
      if (isUserPayload(payload)) {
        user = payload;
      }
    } catch (error) {
      // Token invalid or expired, user remains null
      console.debug("Failed to verify auth token:", error);
    }
  }

  return (
    <html lang={locale}>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <AuthRedirectOnUnauthorized />
        <SessionKeepAlive initialExp={user?.exp ?? null} />
        <Layout user={user} locale={locale} dict={dict.layout}>{children}</Layout>
        <ToastContainer />

      </body>
    </html>
  );
}
