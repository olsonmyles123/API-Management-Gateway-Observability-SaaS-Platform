import React from "react";
import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  trend?: {
    value: string;
    isPositive?: boolean;
  };
  variant?: "default" | "blue" | "emerald" | "amber" | "rose";
}

export function MetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
}: MetricCardProps) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-5 flex flex-col justify-between">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-zinc-400 tracking-wider uppercase">
          {title}
        </span>
        <div className="p-1.5 rounded-md bg-zinc-800/70 border border-zinc-700/50 text-zinc-400">
          <Icon className="h-4 w-4" />
        </div>
      </div>

      <div className="mt-4 flex items-baseline justify-between">
        <div className="text-2xl font-semibold font-mono tracking-tight text-zinc-100">
          {value}
        </div>
        {trend && (
          <span
            className={cn(
              "text-[11px] font-medium px-2 py-0.5 rounded border",
              trend.isPositive
                ? "text-emerald-400 bg-emerald-950/40 border-emerald-800/40"
                : "text-rose-400 bg-rose-950/40 border-rose-800/40"
            )}
          >
            {trend.value}
          </span>
        )}
      </div>

      {subtitle && <p className="mt-2 text-xs text-zinc-500">{subtitle}</p>}
    </div>
  );
}
