"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import {
  Activity,
  KeyRound,
  Users,
  Bell,
  Terminal,
  Server,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/context/AuthContext";
import { LogOut } from "lucide-react";

const navigation = [
  { name: "Telemetry & Overview", href: "/", icon: Activity },
  { name: "Tenants & Upstream", href: "/tenants", icon: Users },
  { name: "API Keys", href: "/keys", icon: KeyRound },
  { name: "Alert Engine", href: "/alerts", icon: Bell },
  { name: "Gateway Playground", href: "/playground", icon: Terminal },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  // Hide sidebar on auth pages
  if (pathname === "/login" || pathname === "/register") {
    return null;
  }

  return (
    <aside className="w-60 border-r border-zinc-800 bg-zinc-950 flex flex-col justify-between shrink-0 h-screen sticky top-0 z-40">
      <div>
        {/* Logo / Header */}
        <div className="h-14 flex items-center px-4 gap-2.5 border-b border-zinc-800">
          <Image
            src="/logo.jpg"
            alt="API Gateway Logo"
            width={28}
            height={28}
            className="rounded-md shrink-0"
          />
          <div className="flex items-center gap-1.5 min-w-0">
            <span className="font-semibold text-sm tracking-tight text-zinc-100 truncate">
              API Gateway
            </span>
            <span className="text-[10px] font-mono px-1 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-zinc-700/50 shrink-0">
              PRO
            </span>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="p-3 space-y-1">
          <p className="text-[11px] font-medium text-zinc-500 px-3 uppercase tracking-wider mb-2">
            Control Plane
          </p>
          {navigation.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  "flex items-center gap-2.5 px-3 py-2 rounded-md text-xs font-medium transition-colors",
                  isActive
                    ? "bg-zinc-800 text-zinc-100 border border-zinc-700/60"
                    : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900"
                )}
              >
                <Icon className={cn("h-4 w-4", isActive ? "text-zinc-100" : "text-zinc-400")} />
                {item.name}
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="space-y-3 p-3">
        {/* User Account / Logout bar */}
        {user ? (
          <div className="p-2.5 rounded-lg bg-zinc-900/50 border border-zinc-800 flex items-center justify-between">
            <div className="flex items-center gap-2 overflow-hidden">
              <div className="h-7 w-7 rounded-full bg-zinc-800 border border-zinc-700 text-zinc-300 font-semibold text-xs flex items-center justify-center shrink-0">
                {user.full_name ? user.full_name[0].toUpperCase() : user.email[0].toUpperCase()}
              </div>
              <div className="overflow-hidden">
                <span className="text-xs font-medium text-zinc-200 block truncate">
                  {user.full_name || user.email.split("@")[0]}
                </span>
                <span className="text-[10px] text-zinc-500 block truncate">{user.email}</span>
              </div>
            </div>
            <button
              onClick={logout}
              className="text-zinc-500 hover:text-rose-400 p-1.5 rounded transition-colors cursor-pointer"
              title="Logout"
            >
              <LogOut className="h-3.5 w-3.5" />
            </button>
          </div>
        ) : (
          <div className="p-2.5 rounded-lg bg-zinc-900/50 border border-zinc-800 flex items-center justify-between">
            <Link
              href="/login"
              className="w-full text-center text-xs font-medium text-zinc-300 hover:text-white py-0.5"
            >
              Sign In to Account →
            </Link>
          </div>
        )}

        {/* Cluster System Status Footer */}
        <div className="p-3 rounded-lg bg-zinc-900/40 border border-zinc-800">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-zinc-300 flex items-center gap-1.5">
              <Server className="h-3.5 w-3.5 text-zinc-400" /> Cluster Engine
            </span>
            <span className="flex items-center gap-1 text-[10px] font-medium text-emerald-400 bg-emerald-950/40 px-1.5 py-0.5 rounded border border-emerald-800/40">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
              Online
            </span>
          </div>
          <div className="space-y-1 text-[10px] text-zinc-500 font-mono">
            <div className="flex justify-between">
              <span className="font-sans text-zinc-400">Data Plane</span>
              <span className="text-zinc-300">Port 8000</span>
            </div>
            <div className="flex justify-between">
              <span className="font-sans text-zinc-400">OLAP Engine</span>
              <span className="text-zinc-300">ClickHouse</span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
