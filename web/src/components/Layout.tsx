"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  Brain,
  History,
  Network,
  Puzzle,
  LogOut,
  User,
  Menu,
  X,
  Bell,
  Search,
  ChevronDown,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { logout } from "@/app/actions/auth";
import { UserPayload } from "@/lib/auth";

interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
}

const navItems: NavItem[] = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Users", href: "/users", icon: Users },
  { label: "Cortex", href: "/cortex", icon: Brain },
  { label: "Audit", href: "/audit", icon: History },
  { label: "Network", href: "/network", icon: Network },
  { label: "Integrations", href: "/integrations", icon: Puzzle },
];

/**
 * Main application layout with sidebar and top bar.
 */
export default function Layout({ 
  children,
  user
}: { 
  children: React.ReactNode;
  user?: UserPayload | null;
}) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const pathname = usePathname();

  // Do not show the layout on the login page
  if (pathname === "/login") {
    return <>{children}</>;
  }

  return (
    <div className="flex h-screen bg-neutral-50 dark:bg-black text-neutral-900 dark:text-neutral-100">
      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-64 transform border-r border-neutral-200 bg-white transition-transform duration-300 ease-in-out dark:border-neutral-800 dark:bg-neutral-900 lg:static lg:translate-x-0",
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex h-full flex-col">
          {/* Sidebar Header */}
          <div className="flex h-16 items-center border-b border-neutral-200 px-6 dark:border-neutral-800">
            <Link href="/" className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white">
                <Brain className="h-5 w-5" />
              </div>
              <span className="text-xl font-bold tracking-tight">Nexus</span>
            </Link>
            <button
              className="ml-auto lg:hidden"
              onClick={() => setSidebarOpen(false)}
            >
              <X className="h-6 w-6" />
            </button>
          </div>

          {/* Sidebar Nav */}
          <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
            {navItems.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-indigo-50 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400"
                      : "text-neutral-600 hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-800/50"
                  )}
                >
                  <item.icon className="h-5 w-5" />
                  {item.label}
                </Link>
              );
            })}
          </nav>

          {/* Sidebar Footer */}
          <div className="border-t border-neutral-200 p-4 dark:border-neutral-800">
            <button
              onClick={() => logout()}
              className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-neutral-600 transition-colors hover:bg-rose-50 hover:text-rose-600 dark:text-neutral-400 dark:hover:bg-rose-900/20 dark:hover:text-rose-400"
            >
              <LogOut className="h-5 w-5" />
              Logout
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top Bar */}
        <header className="flex h-16 items-center justify-between border-b border-neutral-200 bg-white px-4 dark:border-neutral-800 dark:bg-neutral-900 lg:px-8">
          <div className="flex items-center gap-4">
            <button
              className="lg:hidden"
              onClick={() => setSidebarOpen(true)}
            >
              <Menu className="h-6 w-6" />
            </button>
            <div className="hidden items-center gap-2 rounded-lg bg-neutral-100 px-3 py-2 dark:bg-neutral-800 md:flex">
              <Search className="h-4 w-4 text-neutral-500" />
              <input
                type="text"
                placeholder="Search..."
                className="bg-transparent text-sm outline-none placeholder:text-neutral-500"
              />
            </div>
          </div>

          <div className="flex items-center gap-4">
            <button className="rounded-full p-2 text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800">
              <Bell className="h-5 w-5" />
            </button>
            <div className="h-8 w-px bg-neutral-200 dark:bg-neutral-800" />
            <div className="flex items-center gap-3">
              <div className="hidden text-right md:block">
                <p className="text-sm font-medium">{user?.username || "Guest"}</p>
                <p className="text-xs text-neutral-500 capitalize">
                  {user?.role === "admin" ? "Administrator" : (user?.role || "Guest")}
                </p>
              </div>
              <button className="flex items-center gap-1 rounded-full p-1 transition-colors hover:bg-neutral-100 dark:hover:bg-neutral-800">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-neutral-200 dark:bg-neutral-700">
                  <User className="h-5 w-5 text-neutral-500 dark:text-neutral-400" />
                </div>
                <ChevronDown className="h-4 w-4 text-neutral-500" />
              </button>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto p-4 lg:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
