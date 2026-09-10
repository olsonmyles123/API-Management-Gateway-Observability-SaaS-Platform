"use client";

import { usePathname } from "next/navigation";
import { Sidebar } from "@/components/sidebar";
import { AuthGuard } from "@/components/auth-guard";

const PUBLIC_ROUTES = ["/login", "/register"];

export function LayoutShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isPublicRoute = PUBLIC_ROUTES.includes(pathname);

  return (
    <AuthGuard>
      <div className="flex min-h-screen">
        {!isPublicRoute && <Sidebar />}
        <main
          className={`flex-1 min-w-0 flex flex-col bg-zinc-950 ${
            isPublicRoute ? "w-full" : ""
          }`}
        >
          {children}
        </main>
      </div>
    </AuthGuard>
  );
}
