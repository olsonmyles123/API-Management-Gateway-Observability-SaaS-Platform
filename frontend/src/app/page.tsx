"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { Header } from "@/components/header";
import { MetricCard } from "@/components/metric-card";
import {
  Zap,
  AlertTriangle,
  HardDrive,
  Clock,
  Filter,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Cell,
} from "recharts";

export default function DashboardOverviewPage() {
  const [tenantId, setTenantId] = useState<string>("");
  const [timeWindow, setTimeWindow] = useState<number>(3600); // 1 hr default

  // Continuous 5-second polling of ClickHouse telemetry metrics
  const {
    data: metrics,
    isLoading,
    isRefetching,
  } = useQuery({
    queryKey: ["metrics", tenantId, timeWindow],
    queryFn: () => apiClient.getMetrics(tenantId || undefined, timeWindow),
    refetchInterval: 5000,
  });

  const latencyChartData = [
    { name: "P50", ms: metrics?.latency_percentiles_ms.p50 || 0, label: "P50 Latency" },
    { name: "Avg", ms: metrics?.latency_percentiles_ms.avg || 0, label: "Average" },
    { name: "P95", ms: metrics?.latency_percentiles_ms.p95 || 0, label: "P95 Latency" },
    { name: "P99", ms: metrics?.latency_percentiles_ms.p99 || 0, label: "P99 Tail" },
  ];

  const statusBreakdownData = [
    { name: "2xx Success", count: metrics?.status_breakdown["2xx"] || 0, fill: "#10b981" },
    { name: "4xx Client Err", count: metrics?.status_breakdown["4xx"] || 0, fill: "#f59e0b" },
    { name: "5xx Server Err", count: metrics?.status_breakdown["5xx"] || 0, fill: "#f43f5e" },
  ];

  const totalRequests = metrics?.total_requests || 0;
  const errorRate = metrics?.error_rate_pct || 0;
  const p95Latency = metrics?.latency_percentiles_ms.p95 || 0;
  const totalBandwidthKb = (
    (metrics?.bandwidth_bytes.total_bytes || 0) / 1024
  ).toFixed(2);

  return (
    <div className="flex-1 flex flex-col min-h-screen">
      <Header
        title="High-Cardinality Telemetry & Performance"
        subtitle="ClickHouse OLAP Real-Time Aggregations"
        selectedTenantId={tenantId}
        onTenantChange={setTenantId}
      />

      <div className="p-6 space-y-6 flex-1 max-w-7xl w-full mx-auto">
        {/* Time Window Selector */}
        <div className="flex items-center justify-between bg-zinc-900/40 p-2.5 rounded-lg border border-zinc-800">
          <div className="flex items-center gap-2">
            <Filter className="h-3.5 w-3.5 text-zinc-400" />
            <span className="text-xs font-medium text-zinc-400 uppercase tracking-wider">
              Time Window
            </span>
          </div>
          <div className="flex items-center gap-1 bg-zinc-950 p-1 rounded-md border border-zinc-800 text-xs">
            {[
              { label: "15m", val: 900 },
              { label: "1h", val: 3600 },
              { label: "6h", val: 21600 },
              { label: "24h", val: 86400 },
            ].map((w) => (
              <button
                key={w.val}
                onClick={() => setTimeWindow(w.val)}
                className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                  timeWindow === w.val
                    ? "bg-zinc-800 text-zinc-100 border border-zinc-700/60"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                {w.label}
              </button>
            ))}
          </div>
        </div>

        {/* High-Density KPI Metric Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            title="Total Proxied Requests"
            value={totalRequests.toLocaleString()}
            subtitle="Processed through Gateway"
            icon={Zap}
            trend={{ value: "Live Stream", isPositive: true }}
          />

          <MetricCard
            title="Error Rate"
            value={`${errorRate}%`}
            subtitle={`${metrics?.error_count || 0} non-2xx failures`}
            icon={AlertTriangle}
            trend={{ value: errorRate > 5 ? "Exceeded" : "Healthy", isPositive: errorRate <= 5 }}
          />

          <MetricCard
            title="P95 Latency"
            value={`${p95Latency} ms`}
            subtitle={`P50: ${metrics?.latency_percentiles_ms.p50 || 0}ms · P99: ${metrics?.latency_percentiles_ms.p99 || 0}ms`}
            icon={Clock}
          />

          <MetricCard
            title="Total Bandwidth"
            value={`${totalBandwidthKb} KB`}
            subtitle={`Req: ${((metrics?.bandwidth_bytes.request_bytes || 0) / 1024).toFixed(1)}KB · Res: ${((metrics?.bandwidth_bytes.response_bytes || 0) / 1024).toFixed(1)}KB`}
            icon={HardDrive}
          />
        </div>

        {/* Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {/* Latency Percentiles Visualizer */}
          <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-xs font-medium text-zinc-200 uppercase tracking-wider">
                  Latency Distribution (ms)
                </h3>
                <p className="text-xs text-zinc-500">P50, Avg, P95, and P99 tail latency</p>
              </div>
              <span className="text-[11px] font-mono text-zinc-400 bg-zinc-800/80 px-2 py-0.5 rounded border border-zinc-700/60">
                ClickHouse OLAP
              </span>
            </div>
            <div className="h-56 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={latencyChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                  <XAxis dataKey="name" stroke="#71717a" fontSize={11} tickLine={false} />
                  <YAxis stroke="#71717a" fontSize={11} unit="ms" tickLine={false} axisLine={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#18181b", borderColor: "#27272a", borderRadius: "6px" }}
                    itemStyle={{ color: "#f4f4f5", fontSize: "12px" }}
                    labelStyle={{ color: "#a1a1aa", fontSize: "11px" }}
                  />
                  <Bar dataKey="ms" fill="#3b82f6" fillOpacity={0.85} radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Status Breakdown Visualizer */}
          <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-xs font-medium text-zinc-200 uppercase tracking-wider">
                  HTTP Status Breakdown
                </h3>
                <p className="text-xs text-zinc-500">Response classification distribution</p>
              </div>
              <span className="text-[11px] font-mono text-zinc-400 bg-zinc-800/80 px-2 py-0.5 rounded border border-zinc-700/60">
                2xx / 4xx / 5xx
              </span>
            </div>
            <div className="h-56 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={statusBreakdownData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                  <XAxis dataKey="name" stroke="#71717a" fontSize={11} tickLine={false} />
                  <YAxis stroke="#71717a" fontSize={11} tickLine={false} axisLine={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#18181b", borderColor: "#27272a", borderRadius: "6px" }}
                    itemStyle={{ color: "#f4f4f5", fontSize: "12px" }}
                    labelStyle={{ color: "#a1a1aa", fontSize: "11px" }}
                  />
                  <Bar dataKey="count" radius={[3, 3, 0, 0]}>
                    {statusBreakdownData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.fill} fillOpacity={0.85} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Live Route Breakdown Table */}
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-xs font-medium text-zinc-200 uppercase tracking-wider">
                Live Route Telemetry Breakdown
              </h3>
              <p className="text-xs text-zinc-500">Endpoint query performance and error rates</p>
            </div>
            <span className="text-[11px] text-zinc-500 font-mono">Top active routes</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-zinc-800 text-zinc-400 uppercase tracking-wider bg-zinc-950/40">
                <tr>
                  <th className="py-2.5 px-3 font-medium">Method</th>
                  <th className="py-2.5 px-3 font-medium">Endpoint Route</th>
                  <th className="py-2.5 px-3 font-medium text-right">Calls</th>
                  <th className="py-2.5 px-3 font-medium text-right">Avg Latency</th>
                  <th className="py-2.5 px-3 font-medium text-right">P95 Latency</th>
                  <th className="py-2.5 px-3 font-medium text-right">Error Rate</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60 font-mono">
                {metrics?.routes_breakdown && metrics.routes_breakdown.length > 0 ? (
                  metrics.routes_breakdown.map((r, idx) => (
                    <tr key={idx} className="hover:bg-zinc-800/20 transition-colors">
                      <td className="py-2.5 px-3">
                        <span className="px-1.5 py-0.5 rounded text-[11px] font-mono font-medium bg-zinc-800 text-zinc-300 border border-zinc-700/60">
                          {r.method}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-zinc-200 font-sans font-medium">{r.route}</td>
                      <td className="py-2.5 px-3 text-right text-zinc-300">{r.count.toLocaleString()}</td>
                      <td className="py-2.5 px-3 text-right text-zinc-300">{r.avg_latency} ms</td>
                      <td className="py-2.5 px-3 text-right text-zinc-300">{r.p95_latency} ms</td>
                      <td className="py-2.5 px-3 text-right">
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                          r.error_rate > 0 ? "bg-rose-950/40 text-rose-400 border border-rose-800/40" : "text-emerald-400"
                        }`}>
                          {r.error_rate.toFixed(1)}%
                        </span>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-zinc-500 font-sans text-xs">
                      No traffic detected in selected time window. Send requests via the{" "}
                      <span className="text-zinc-300 underline">Gateway Playground</span> to populate live telemetry.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
