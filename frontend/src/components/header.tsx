"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

interface HeaderProps {
  title: string;
  subtitle?: string;
  selectedTenantId?: string;
  onTenantChange?: (tenantId: string) => void;
}

export function Header({
  title,
  subtitle,
  selectedTenantId,
  onTenantChange,
}: HeaderProps) {
  const { data: rawTenants = [] } = useQuery({
    queryKey: ["tenants"],
    queryFn: apiClient.getTenants,
  });

  const tenants = Array.isArray(rawTenants) ? rawTenants : [];

  return (
    <header className="min-h-[3.5rem] border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-md px-6 py-2.5 flex items-center justify-between sticky top-0 z-30">
      <div className="flex flex-col justify-center">
        <h1 className="text-sm font-semibold text-zinc-100 tracking-tight leading-tight">{title}</h1>
        {subtitle && <p className="text-xs text-zinc-400 leading-tight mt-0.5">{subtitle}</p>}
      </div>

      <div className="flex items-center gap-3">
        {/* Tenant Switcher Filter */}
        {onTenantChange && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-zinc-400">Tenant:</span>
            <select
              value={selectedTenantId || "all"}
              onChange={(e) =>
                onTenantChange(e.target.value === "all" ? "" : e.target.value)
              }
              className="bg-zinc-900 border border-zinc-800 text-zinc-200 text-xs rounded-md px-2.5 py-1.5 focus:outline-none focus:border-zinc-600 font-medium"
            >
              <option value="all">All Tenants (Global)</option>
              {tenants.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name} ({t.slug})
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Real-time Indicator */}
        <div className="flex items-center gap-2 text-xs text-zinc-400 bg-zinc-900 border border-zinc-800 px-2.5 py-1.5 rounded-md">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
          <span className="text-[11px] font-medium text-zinc-300">5s Live</span>
        </div>
      </div>
    </header>
  );
}
