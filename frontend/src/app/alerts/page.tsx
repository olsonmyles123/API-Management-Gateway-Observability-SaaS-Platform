"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { Header } from "@/components/header";
import { AlertRuleCreateInput } from "@/lib/types";
import {
  Bell,
  Plus,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";

export default function AlertsPage() {
  const queryClient = useQueryClient();
  const [selectedTenantId, setSelectedTenantId] = useState<string>("");
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  // Form State
  const [tenantTarget, setTenantTarget] = useState("");
  const [name, setName] = useState("");
  const [metricType, setMetricType] = useState<"p95_latency" | "error_rate" | "req_count">("p95_latency");
  const [threshold, setThreshold] = useState<number>(300);
  const [windowMinutes, setWindowMinutes] = useState<number>(5);
  const [webhookUrl, setWebhookUrl] = useState("");

  const { data: tenants = [] } = useQuery({
    queryKey: ["tenants"],
    queryFn: apiClient.getTenants,
  });

  const { data: rulesData } = useQuery({
    queryKey: ["alertRules", selectedTenantId],
    queryFn: () => apiClient.getAlertRules(selectedTenantId || undefined),
  });

  const { data: historyData } = useQuery({
    queryKey: ["alertHistory", selectedTenantId],
    queryFn: () => apiClient.getAlertHistory(selectedTenantId || undefined),
    refetchInterval: 5000,
  });

  const rules = rulesData?.items || [];
  const history = historyData?.items || [];

  const createMutation = useMutation({
    mutationFn: apiClient.createAlertRule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alertRules"] });
      toast.success("Alert rule registered successfully!");
      setIsCreateOpen(false);
    },
    onError: (err: any) => {
      toast.error(err.message || "Failed to create alert rule.");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: apiClient.deleteAlertRule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alertRules"] });
      toast.success("Alert rule deleted.");
    },
  });

  return (
    <div className="flex-1 flex flex-col min-h-screen">
      <Header
        title="Automated Alert Engine & Webhooks"
        subtitle="Real-time threshold evaluation across ClickHouse metrics"
        selectedTenantId={selectedTenantId}
        onTenantChange={setSelectedTenantId}
      />

      <div className="p-6 space-y-6 flex-1 max-w-7xl w-full mx-auto">
        {/* Top Action Bar */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-zinc-100 tracking-tight">Active Metric Rules</h2>
            <p className="text-xs text-zinc-500">
              Evaluated every 30 seconds by background daemon worker
            </p>
          </div>
          <button
            onClick={() => {
              if (tenants.length > 0 && !tenantTarget) {
                setTenantTarget(tenants[0].id);
              }
              setIsCreateOpen(true);
            }}
            className="flex items-center gap-1.5 bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-medium px-3.5 py-2 rounded-md transition-colors cursor-pointer"
          >
            <Plus className="h-3.5 w-3.5" /> Create Alert Rule
          </button>
        </div>

        {/* Rules Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {rules.map((rule) => {
            const tenant = tenants.find((t) => t.id === rule.tenant_id);
            return (
              <div
                key={rule.id}
                className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-5 flex flex-col justify-between hover:border-zinc-700/80 transition-colors"
              >
                <div>
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-sm font-semibold text-zinc-100 flex items-center gap-2">
                        <Bell className="h-3.5 w-3.5 text-zinc-400" />
                        {rule.name}
                      </h3>
                      <span className="text-xs font-mono text-zinc-500">
                        {tenant ? `${tenant.name}` : rule.tenant_id.slice(0, 8)}
                      </span>
                    </div>
                    <span className="text-[10px] font-medium px-2 py-0.5 rounded border text-emerald-400 bg-emerald-950/40 border-emerald-800/40">
                      Monitoring
                    </span>
                  </div>

                  {/* Trigger Condition */}
                  <div className="mt-4 p-3 rounded-md bg-zinc-950/60 border border-zinc-800 space-y-1">
                    <span className="text-[10px] font-medium text-zinc-500 uppercase">Trigger</span>
                    <p className="text-xs font-mono text-zinc-200">
                      {rule.metric_type === "p95_latency" && `P95 Latency > ${rule.threshold} ms`}
                      {rule.metric_type === "error_rate" && `Error Rate > ${rule.threshold}%`}
                      {rule.metric_type === "req_count" && `Request Count > ${rule.threshold}`}
                    </p>
                    <p className="text-[11px] text-zinc-500 font-sans">Window: {rule.window_minutes} min</p>
                  </div>

                  {/* Webhook Endpoint */}
                  <div className="mt-3 text-xs">
                    <span className="text-zinc-500 block text-[10px] uppercase">Webhook Target:</span>
                    <p className="font-mono text-[11px] text-zinc-300 truncate mt-0.5">
                      {rule.webhook_url}
                    </p>
                  </div>
                </div>

                <div className="mt-5 pt-3.5 border-t border-zinc-800/80 flex items-center justify-between text-xs text-zinc-500">
                  <span className="font-mono text-[11px]">ID: {rule.id.slice(0, 8)}...</span>
                  <button
                    onClick={() => {
                      if (confirm("Delete this alert rule?")) {
                        deleteMutation.mutate(rule.id);
                      }
                    }}
                    className="text-zinc-500 hover:text-rose-400 p-1 rounded transition-colors cursor-pointer"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {/* Webhook Trigger History */}
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xs font-medium text-zinc-200 uppercase tracking-wider">Recent Alert Incidents</h3>
              <p className="text-xs text-zinc-500">Webhook delivery logs and threshold violations</p>
            </div>
            <span className="text-[11px] font-mono text-zinc-400 bg-zinc-800/80 px-2 py-0.5 rounded border border-zinc-700/60">
              Live Sync
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-zinc-800 text-zinc-400 uppercase tracking-wider bg-zinc-950/40">
                <tr>
                  <th className="py-2.5 px-3 font-medium">Incident Time</th>
                  <th className="py-2.5 px-3 font-medium">Metric</th>
                  <th className="py-2.5 px-3 font-medium">Observed Value</th>
                  <th className="py-2.5 px-3 font-medium">Threshold</th>
                  <th className="py-2.5 px-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60 font-mono">
                {history.length > 0 ? (
                  history.map((h) => (
                    <tr key={h.id} className="hover:bg-zinc-800/20 transition-colors">
                      <td className="py-2.5 px-3 text-zinc-300">
                        {new Date(h.triggered_at).toLocaleTimeString()}
                      </td>
                      <td className="py-2.5 px-3 text-zinc-200 font-sans">{h.metric_type}</td>
                      <td className="py-2.5 px-3 text-rose-400 font-medium">{h.triggered_value}</td>
                      <td className="py-2.5 px-3 text-zinc-400">{h.threshold}</td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`px-1.5 py-0.5 rounded text-[10px] font-medium uppercase ${
                            h.status === "sent"
                              ? "bg-emerald-950/40 text-emerald-400 border border-emerald-800/40"
                              : "bg-rose-950/40 text-rose-400 border border-rose-800/40"
                          }`}
                        >
                          {h.status}
                        </span>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5} className="py-6 text-center text-zinc-500 font-sans text-xs">
                      No alert violations triggered. System metrics within healthy thresholds.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Modal: Create Alert Rule */}
        {isCreateOpen && (
          <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl max-w-md w-full p-6 shadow-xl space-y-5">
              <div className="flex items-center justify-between border-b border-zinc-800 pb-3.5">
                <div className="flex items-center gap-2">
                  <Bell className="h-4 w-4 text-zinc-300" />
                  <h3 className="text-sm font-semibold text-zinc-100">Configure Alert Rule</h3>
                </div>
                <button
                  onClick={() => setIsCreateOpen(false)}
                  className="text-zinc-500 hover:text-zinc-300 text-sm font-medium"
                >
                  ✕
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1">
                    Assign to Tenant *
                  </label>
                  <select
                    value={tenantTarget}
                    onChange={(e) => setTenantTarget(e.target.value)}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-100 focus:outline-none focus:border-zinc-500"
                  >
                    {tenants.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.name} ({t.slug})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1">
                    Rule Friendly Name *
                  </label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-100 focus:outline-none focus:border-zinc-500"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-zinc-300 mb-1">
                      Metric Condition
                    </label>
                    <select
                      value={metricType}
                      onChange={(e: any) => setMetricType(e.target.value)}
                      className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-2.5 py-2 text-xs text-zinc-100 focus:outline-none focus:border-zinc-500"
                    >
                      <option value="p95_latency">P95 Latency (ms)</option>
                      <option value="error_rate">Error Rate (%)</option>
                      <option value="req_count">Request Count</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-zinc-300 mb-1">
                      Threshold Value *
                    </label>
                    <input
                      type="number"
                      value={threshold}
                      onChange={(e) => setThreshold(parseFloat(e.target.value) || 0)}
                      className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-2.5 py-2 text-xs text-zinc-100 font-mono focus:outline-none focus:border-zinc-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1">
                    Webhook Destination URL *
                  </label>
                  <input
                    type="url"
                    value={webhookUrl}
                    onChange={(e) => setWebhookUrl(e.target.value)}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-100 font-mono focus:outline-none focus:border-zinc-500"
                  />
                </div>

                <div className="flex items-center justify-end gap-2.5 pt-4 border-t border-zinc-800">
                  <button
                    type="button"
                    onClick={() => setIsCreateOpen(false)}
                    className="px-3.5 py-2 text-xs font-medium text-zinc-400 hover:text-zinc-200 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => {
                      if (!tenantTarget) {
                        toast.error("Please select a tenant.");
                        return;
                      }
                      createMutation.mutate({
                        tenant_id: tenantTarget,
                        name,
                        metric_type: metricType,
                        threshold,
                        window_minutes: windowMinutes,
                        webhook_url: webhookUrl,
                      });
                    }}
                    disabled={createMutation.isPending}
                    className="px-4 py-2 text-xs font-medium bg-zinc-100 hover:bg-white text-zinc-950 rounded-md transition-colors disabled:opacity-50"
                  >
                    {createMutation.isPending ? "Registering..." : "Enable Alert Rule"}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
