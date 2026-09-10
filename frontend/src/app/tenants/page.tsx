"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { Header } from "@/components/header";
import { TenantCreateInput } from "@/lib/types";
import {
  Plus,
  Globe,
  Trash2,
  ExternalLink,
} from "lucide-react";
import { toast } from "sonner";

export default function TenantsPage() {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formData, setFormData] = useState<TenantCreateInput>({
    name: "",
    slug: "",
    upstream_url: "",
    plan_tier: "free",
    rate_limit_rpm: 60,
    burst_limit: 10,
  });

  const { data: tenants = [] } = useQuery({
    queryKey: ["tenants"],
    queryFn: apiClient.getTenants,
  });

  const createMutation = useMutation({
    mutationFn: apiClient.createTenant,
    onSuccess: (newTenant) => {
      queryClient.invalidateQueries({ queryKey: ["tenants"] });
      toast.success(`Tenant '${newTenant.name}' created successfully!`);
      setIsModalOpen(false);
      setFormData({
        name: "",
        slug: "",
        upstream_url: "",
        plan_tier: "free",
        rate_limit_rpm: 60,
        burst_limit: 10,
      });
    },
    onError: (err: any) => {
      toast.error(err.message || "Failed to create tenant.");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: apiClient.deleteTenant,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tenants"] });
      toast.success("Tenant removed.");
    },
    onError: (err: any) => {
      toast.error(err.message || "Failed to remove tenant.");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name || !formData.slug || !formData.upstream_url) {
      toast.error("Please fill in all required fields.");
      return;
    }
    createMutation.mutate(formData);
  };

  const getTierBadge = (tier: string) => {
    switch (tier) {
      case "enterprise":
        return "bg-zinc-800 text-zinc-100 border-zinc-700";
      case "pro":
        return "bg-zinc-800 text-zinc-300 border-zinc-700/80";
      default:
        return "bg-zinc-900 text-zinc-400 border-zinc-800";
    }
  };

  return (
    <div className="flex-1 flex flex-col min-h-screen">
      <Header
        title="Tenants & Upstream Routing"
        subtitle="Configure target APIs, plan tiers, and rate limit quotas"
      />

      <div className="p-6 space-y-6 flex-1 max-w-7xl w-full mx-auto">
        {/* Action Bar */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-zinc-100 tracking-tight">
              Registered Organizations
            </h2>
            <p className="text-xs text-zinc-500">
              {tenants.length} active tenant isolation boundaries
            </p>
          </div>
          <button
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-1.5 bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-medium px-3.5 py-2 rounded-md transition-colors cursor-pointer"
          >
            <Plus className="h-3.5 w-3.5" /> Register Tenant
          </button>
        </div>

        {/* Tenant Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {tenants.map((t) => (
            <div
              key={t.id}
              className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-5 flex flex-col justify-between hover:border-zinc-700/80 transition-colors"
            >
              <div>
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-zinc-100">{t.name}</h3>
                    <span className="text-xs font-mono text-zinc-500">slug: {t.slug}</span>
                  </div>
                  <span
                    className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded border ${getTierBadge(
                      t.plan_tier
                    )}`}
                  >
                    {t.plan_tier}
                  </span>
                </div>

                {/* Target Upstream */}
                <div className="mt-4 p-3 rounded-md bg-zinc-950/60 border border-zinc-800/80 space-y-1.5">
                  <div className="flex items-center justify-between text-xs text-zinc-400">
                    <span className="flex items-center gap-1.5">
                      <Globe className="h-3.5 w-3.5 text-zinc-400" /> Upstream Target
                    </span>
                    <a
                      href={t.upstream_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-zinc-500 hover:text-zinc-300 transition-colors"
                    >
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  </div>
                  <p className="text-xs font-mono text-zinc-300 truncate">{t.upstream_url}</p>
                </div>

                {/* Quota Details */}
                <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                  <div className="p-2 rounded-md bg-zinc-950/40 border border-zinc-800">
                    <span className="text-zinc-500 block text-[10px] uppercase">Rate Limit</span>
                    <span className="font-mono font-medium text-zinc-200 text-xs">
                      {t.rate_limit_rpm} <span className="text-[10px] text-zinc-500 font-sans">RPM</span>
                    </span>
                  </div>
                  <div className="p-2 rounded-md bg-zinc-950/40 border border-zinc-800">
                    <span className="text-zinc-500 block text-[10px] uppercase">Burst Limit</span>
                    <span className="font-mono font-medium text-zinc-200 text-xs">
                      {t.burst_limit} <span className="text-[10px] text-zinc-500 font-sans">reqs</span>
                    </span>
                  </div>
                </div>
              </div>

              {/* Card Footer */}
              <div className="mt-5 pt-3.5 border-t border-zinc-800/80 flex items-center justify-between text-xs text-zinc-500">
                <span className="font-mono text-[11px]">ID: {t.id.slice(0, 8)}...</span>
                <button
                  onClick={() => {
                    if (confirm(`Are you sure you want to delete tenant '${t.name}'?`)) {
                      deleteMutation.mutate(t.id);
                    }
                  }}
                  className="text-zinc-500 hover:text-rose-400 p-1 rounded transition-colors cursor-pointer"
                  title="Delete Tenant"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Modal: Register Tenant */}
        {isModalOpen && (
          <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl max-w-md w-full p-6 shadow-xl space-y-5">
              <div className="flex items-center justify-between border-b border-zinc-800 pb-3.5">
                <div>
                  <h3 className="text-sm font-semibold text-zinc-100">Register New Tenant</h3>
                  <p className="text-xs text-zinc-400">
                    Establish an isolated API proxy route and rate limit quota
                  </p>
                </div>
                <button
                  onClick={() => setIsModalOpen(false)}
                  className="text-zinc-500 hover:text-zinc-300 text-sm font-medium"
                >
                  ✕
                </button>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1">
                    Organization Name *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Acme Corporation"
                    value={formData.name}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        name: e.target.value,
                        slug: e.target.value.toLowerCase().replace(/[^a-z0-9]/g, "-"),
                      })
                    }
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-zinc-500 focus:ring-1 focus:ring-zinc-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1">
                    Unique Slug *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. acme"
                    value={formData.slug}
                    onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-100 font-mono placeholder:text-zinc-600 focus:outline-none focus:border-zinc-500 focus:ring-1 focus:ring-zinc-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1">
                    Target Upstream API URL *
                  </label>
                  <input
                    type="url"
                    required
                    placeholder="https://api.example.com"
                    value={formData.upstream_url}
                    onChange={(e) => setFormData({ ...formData, upstream_url: e.target.value })}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-100 font-mono placeholder:text-zinc-600 focus:outline-none focus:border-zinc-500 focus:ring-1 focus:ring-zinc-500"
                  />
                </div>

                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-zinc-300 mb-1">
                      Plan Tier
                    </label>
                    <select
                      value={formData.plan_tier}
                      onChange={(e) => {
                        const tier = e.target.value;
                        const rpm = tier === "enterprise" ? 5000 : tier === "pro" ? 1000 : 60;
                        const burst = tier === "enterprise" ? 100 : tier === "pro" ? 50 : 10;
                        setFormData({ ...formData, plan_tier: tier, rate_limit_rpm: rpm, burst_limit: burst });
                      }}
                      className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-2.5 py-2 text-xs text-zinc-100 focus:outline-none focus:border-zinc-500"
                    >
                      <option value="free">Free (60 RPM)</option>
                      <option value="pro">Pro (1K RPM)</option>
                      <option value="enterprise">Enterprise (5K RPM)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-zinc-300 mb-1">
                      Rate Limit (RPM)
                    </label>
                    <input
                      type="number"
                      value={formData.rate_limit_rpm}
                      onChange={(e) =>
                        setFormData({ ...formData, rate_limit_rpm: parseInt(e.target.value) || 60 })
                      }
                      className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-2.5 py-2 text-xs text-zinc-100 font-mono focus:outline-none focus:border-zinc-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-zinc-300 mb-1">
                      Burst Limit
                    </label>
                    <input
                      type="number"
                      value={formData.burst_limit}
                      onChange={(e) =>
                        setFormData({ ...formData, burst_limit: parseInt(e.target.value) || 10 })
                      }
                      className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-2.5 py-2 text-xs text-zinc-100 font-mono focus:outline-none focus:border-zinc-500"
                    />
                  </div>
                </div>

                <div className="flex items-center justify-end gap-2.5 pt-4 border-t border-zinc-800">
                  <button
                    type="button"
                    onClick={() => setIsModalOpen(false)}
                    className="px-3.5 py-2 text-xs font-medium text-zinc-400 hover:text-zinc-200 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={createMutation.isPending}
                    className="px-4 py-2 text-xs font-medium bg-zinc-100 hover:bg-white text-zinc-950 rounded-md transition-colors disabled:opacity-50"
                  >
                    {createMutation.isPending ? "Registering..." : "Create Tenant"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
