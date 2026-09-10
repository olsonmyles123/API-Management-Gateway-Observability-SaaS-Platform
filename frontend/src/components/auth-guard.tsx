"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";

const PUBLIC_ROUTES = ["/login", "/register"];

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  const isPublicRoute = PUBLIC_ROUTES.includes(pathname);

  useEffect(() => {
    if (loading) return; // Wait until auth state is resolved

    if (!user && !isPublicRoute) {
      // Not authenticated and trying to access a protected route
      router.replace("/login");
    } else if (user && isPublicRoute) {
      // Already authenticated, redirect away from login/register
      router.replace("/");
    }
  }, [user, loading, isPublicRoute, router]);

  // Show nothing while auth is loading (prevents flash of wrong content)
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-950">
        <div className="flex flex-col items-center gap-4">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-zinc-700 border-t-zinc-300" />
          <p className="text-sm text-zinc-500 tracking-wide">Authenticating…</p>
        </div>
      </div>
    );
  }

  // Block render if redirect is about to happen
  if (!user && !isPublicRoute) return null;
  if (user && isPublicRoute) return null;

  return <>{children}</>;
}
