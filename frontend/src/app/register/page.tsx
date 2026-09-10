"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { useAuth } from "@/context/AuthContext";
import { Lock, Mail, User as UserIcon, ArrowRight, CheckCircle2 } from "lucide-react";

export default function RegisterPage() {
  const { register } = useAuth();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await register(email, password, fullName);
    } catch {
      // Handled in AuthContext
    } finally {
      setLoading(false);
    }
  };

  const passwordStrength =
    password.length === 0
      ? null
      : password.length < 6
      ? "weak"
      : password.length < 10
      ? "fair"
      : "strong";

  const strengthConfig = {
    weak: { label: "Weak", color: "bg-rose-500", width: "w-1/4", text: "text-rose-400" },
    fair: { label: "Fair", color: "bg-amber-500", width: "w-2/4", text: "text-amber-400" },
    strong: { label: "Strong", color: "bg-emerald-500", width: "w-full", text: "text-emerald-400" },
  };

  return (
    <div className="min-h-screen w-full flex bg-zinc-950">
      {/* ── Left Panel: Brand & Benefits ── */}
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

        {/* Center: Copy */}
        <div className="relative z-10 space-y-8">
          <div className="space-y-4">
            <p className="text-xs font-medium text-zinc-500 uppercase tracking-widest">
              Get Started
            </p>
            <h1 className="text-4xl font-bold text-zinc-100 leading-tight tracking-tight">
              Full observability
              <br />
              from day one.
              <br />
              <span className="text-zinc-400">No configuration needed.</span>
            </h1>
            <p className="text-sm text-zinc-500 leading-relaxed max-w-sm">
              Your account comes with full access to the control plane — create
              tenants, issue API keys, configure rate limits, and monitor live
              telemetry within seconds.
            </p>
          </div>

          {/* Checklist */}
          <div className="space-y-3 max-w-sm">
            {[
              "Unlimited real-time telemetry queries",
              "Multi-tenant API key management",
              "Automated alert rules & webhook delivery",
              "Interactive gateway proxy playground",
            ].map((item) => (
              <div key={item} className="flex items-center gap-3">
                <CheckCircle2 className="h-4 w-4 text-zinc-400 shrink-0" />
                <span className="text-sm text-zinc-400">{item}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom: Security note */}
        <div className="relative z-10">
          <p className="text-[11px] text-zinc-600">
            Passwords are hashed with bcrypt · JWT tokens are HttpOnly · Zero plaintext storage
          </p>
        </div>
      </div>

      {/* ── Right Panel: Register Form ── */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-sm space-y-8">
          {/* Mobile logo */}
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
              Create your account
            </h2>
            <p className="text-sm text-zinc-500">
              Start managing your API gateway in minutes
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-1.5">
              <label
                htmlFor="reg-name"
                className="block text-xs font-medium text-zinc-400 uppercase tracking-wide"
              >
                Full name
              </label>
              <div className="relative">
                <UserIcon className="h-4 w-4 text-zinc-600 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  id="reg-name"
                  type="text"
                  required
                  autoComplete="name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Your full name"
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-lg pl-10 pr-4 py-3 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-zinc-600 focus:ring-2 focus:ring-zinc-700/50 transition-all"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label
                htmlFor="reg-email"
                className="block text-xs font-medium text-zinc-400 uppercase tracking-wide"
              >
                Work email
              </label>
              <div className="relative">
                <Mail className="h-4 w-4 text-zinc-600 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  id="reg-email"
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
                htmlFor="reg-password"
                className="block text-xs font-medium text-zinc-400 uppercase tracking-wide"
              >
                Password
              </label>
              <div className="relative">
                <Lock className="h-4 w-4 text-zinc-600 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  id="reg-password"
                  type="password"
                  required
                  minLength={6}
                  autoComplete="new-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Min. 6 characters"
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-lg pl-10 pr-4 py-3 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-zinc-600 focus:ring-2 focus:ring-zinc-700/50 transition-all"
                />
              </div>
              {/* Password strength meter */}
              {passwordStrength && (
                <div className="space-y-1 pt-1">
                  <div className="h-1 w-full bg-zinc-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-300 ${strengthConfig[passwordStrength].color} ${strengthConfig[passwordStrength].width}`}
                    />
                  </div>
                  <p className={`text-[11px] font-medium ${strengthConfig[passwordStrength].text}`}>
                    {strengthConfig[passwordStrength].label} password
                  </p>
                </div>
              )}
            </div>

            <button
              type="submit"
              disabled={loading}
              id="register-submit"
              className="w-full flex items-center justify-center gap-2.5 bg-zinc-100 hover:bg-white text-zinc-950 font-semibold text-sm py-3 rounded-lg transition-colors disabled:opacity-40 cursor-pointer"
            >
              {loading ? (
                <div className="h-4 w-4 rounded-full border-2 border-zinc-400 border-t-zinc-950 animate-spin" />
              ) : (
                <ArrowRight className="h-4 w-4" />
              )}
              {loading ? "Creating account…" : "Create account"}
            </button>
          </form>

          {/* Divider */}
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-zinc-800" />
            </div>
            <div className="relative flex justify-center">
              <span className="bg-zinc-950 px-3 text-xs text-zinc-600">
                Already have an account?
              </span>
            </div>
          </div>

          <Link
            href="/login"
            className="w-full flex items-center justify-center gap-2 border border-zinc-800 hover:border-zinc-700 text-zinc-300 hover:text-zinc-100 font-medium text-sm py-3 rounded-lg transition-all"
          >
            Sign in instead
          </Link>
        </div>
      </div>
    </div>
  );
}
