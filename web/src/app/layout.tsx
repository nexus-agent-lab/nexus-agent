import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { cookies } from "next/headers";
import { verifyAuthToken } from "@/lib/auth";
import "./globals.css";
import Layout from "@/components/Layout";

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

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;
  let user = null;

  if (token) {
    try {
      user = await verifyAuthToken(token) as any;
    } catch (error) {
      // Token invalid or expired, user remains null
      console.debug("Failed to verify auth token:", error);
    }
  }

  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <Layout user={user}>{children}</Layout>
      </body>
    </html>
  );
}
