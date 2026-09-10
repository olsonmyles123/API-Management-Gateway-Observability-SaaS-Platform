"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { useAuth } from "@/context/AuthContext";
import { Lock, Mail, ArrowRight, Activity, Zap, BarChart3 } from "lucide-react";

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(email, password);
    } catch {
      // toast error handled in AuthContext
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex bg-zinc-950">
      {/* ── Left Panel: Brand & Features ── */}
      <div className="hidden lg:flex lg:w-1/2 xl:w-[55%] flex-col justify-between p-12 relative overflow-hidden border-r border-zinc-800/60">
        {/* Subtle grid background */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            backgroundImage:
              "linear-gradient(rgba(39,39,42,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(39,39,42,0.5) 1px, transparent 1px)",
            backgroundSize: "48px 48px",
          }}
        />
        {/* Gradient fade over grid */}
        <div className="absolute inset-0 bg-gradient-to-br from-zinc-950 via-zinc-950/80 to-zinc-900/40 pointer-events-none" />

        {/* Top: Wordmark */}
        <div className="relative z-10 flex items-center gap-3">
          <Image
            src="/logo.jpg"
            alt="API Gateway Logo"
            width={32}
            height={32}
            className="rounded-md"
          />
          <span className="text-sm font-semibold text-zinc-100 tracking-tight">
            API Gateway Console
          </span>
        </div>

        {/* Center: Hero copy */}
        <div className="relative z-10 space-y-8">
          <div className="space-y-4">
            <p className="text-xs font-medium text-zinc-500 uppercase tracking-widest">
              Control Plane
            </p>
            <h1 className="text-4xl font-bold text-zinc-100 leading-tight tracking-tight">
              Observe, control,
              <br />
              and secure every
              <br />
              <span className="text-zinc-400">API request.</span>
            </h1>
            <p className="text-sm text-zinc-500 leading-relaxed max-w-sm">
              High-cardinality telemetry with ClickHouse OLAP, sub-millisecond
              key validation via Redis, and sliding-window rate limiting — all
              from a single control plane.
            </p>
          </div>

          {/* Feature pills */}
          <div className="grid grid-cols-1 gap-3 max-w-sm">
            {[
              {
                icon: Activity,
                title: "Real-time telemetry",
                desc: "P50/P95/P99 latency via ClickHouse aggregations",
              },
              {
                icon: Zap,
                title: "Sub-ms key validation",
                desc: "SHA-256 digest lookup with Redis bloom filter",
              },
              {
                icon: BarChart3,
                title: "Multi-tenant isolation",
                desc: "Per-tenant quotas, burst limits, and routing",
              },
            ].map(({ icon: Icon, title, desc }) => (
              <div
                key={title}
                className="flex items-start gap-3 p-3.5 rounded-lg border border-zinc-800/80 bg-zinc-900/30"
              >
                <div className="h-7 w-7 rounded-md bg-zinc-800 border border-zinc-700/60 flex items-center justify-center shrink-0 mt-0.5">
                  <Icon className="h-3.5 w-3.5 text-zinc-300" />
                </div>
                <div>
                  <p className="text-xs font-semibold text-zinc-200">{title}</p>
                  <p className="text-xs text-zinc-500 mt-0.5">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom: Trust signal */}
        <div className="relative z-10">
          <p className="text-[11px] text-zinc-600">
            All sessions are JWT-signed · HttpOnly cookie transport · XSS-hardened
          </p>
        </div>
      </div>

      {/* ── Right Panel: Auth Form ── */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-sm space-y-8">
          {/* Mobile logo (hidden on lg) */}
          <div className="flex items-center gap-2.5 lg:hidden">
            <Image
              src="/logo.jpg"
              alt="API Gateway Logo"
              width={28}
              height={28}
              className="rounded-md"
            />
            <span className="text-sm font-semibold text-zinc-100">
              API Gateway Console
            </span>
          </div>

          {/* Heading */}
          <div className="space-y-1.5">
            <h2 className="text-2xl font-bold text-zinc-100 tracking-tight">
              Welcome back
            </h2>
            <p className="text-sm text-zinc-500">
              Sign in to your control plane
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-1.5">
              <label
                htmlFor="login-email"
                className="block text-xs font-medium text-zinc-400 uppercase tracking-wide"
              >
                Email address
              </label>
              <div className="relative">
                <Mail className="h-4 w-4 text-zinc-600 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  id="login-email"
                  type="email"
                  required
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@company.com"
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-lg pl-10 pr-4 py-3 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-zinc-600 focus:ring-2 focus:ring-zinc-700/50 transition-all"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label
                htmlFor="login-password"
                className="block text-xs font-medium text-zinc-400 uppercase tracking-wide"
              >
                Password
              </label>
              <div className="relative">
                <Lock className="h-4 w-4 text-zinc-600 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  id="login-password"
                  type="password"
                  required
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-lg pl-10 pr-4 py-3 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-zinc-600 focus:ring-2 focus:ring-zinc-700/50 transition-all"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              id="login-submit"
              className="w-full flex items-center justify-center gap-2.5 bg-zinc-100 hover:bg-white text-zinc-950 font-semibold text-sm py-3 rounded-lg transition-colors disabled:opacity-40 cursor-pointer"
            >
              {loading ? (
                <div className="h-4 w-4 rounded-full border-2 border-zinc-400 border-t-zinc-950 animate-spin" />
              ) : (
                <ArrowRight className="h-4 w-4" />
              )}
              {loading ? "Authenticating…" : "Sign in"}
            </button>
          </form>

          {/* Divider */}
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-zinc-800" />
            </div>
            <div className="relative flex justify-center">
              <span className="bg-zinc-950 px-3 text-xs text-zinc-600">
                New to the platform?
              </span>
            </div>
          </div>

          <Link
            href="/register"
            className="w-full flex items-center justify-center gap-2 border border-zinc-800 hover:border-zinc-700 text-zinc-300 hover:text-zinc-100 font-medium text-sm py-3 rounded-lg transition-all"
          >
            Create an account
          </Link>
        </div>
      </div>
    </div>
  );
}
