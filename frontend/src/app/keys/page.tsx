"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { Header } from "@/components/header";
import { ApiKey, ApiKeyCreatedResponse } from "@/lib/types";
import {
  KeyRound,
  Plus,
  Copy,
  Check,
  Trash2,
  Lock,
} from "lucide-react";
import { toast } from "sonner";

export default function ApiKeysPage() {
  const queryClient = useQueryClient();
  const [selectedTenantId, setSelectedTenantId] = useState<string>("");
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [createdSecret, setCreatedSecret] = useState<ApiKeyCreatedResponse | null>(null);
  const [hasCopied, setHasCopied] = useState(false);

  // Form State
  const [keyName, setKeyName] = useState("");
  const [tenantTarget, setTenantTarget] = useState("");
  const [rateLimitOverride, setRateLimitOverride] = useState<number | undefined>(undefined);

  // Fetch tenants for dropdown
  const { data: tenants = [] } = useQuery({
    queryKey: ["tenants"],
    queryFn: apiClient.getTenants,
  });

  // Fetch API Keys
  const { data: keysData } = useQuery({
    queryKey: ["keys", selectedTenantId],
    queryFn: () => apiClient.getKeys(selectedTenantId || undefined),
  });

  const keys = keysData?.items || [];

  // Create Key Mutation
  const createMutation = useMutation({
    mutationFn: apiClient.createKey,
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ["keys"] });
      setCreatedSecret(res);
      setIsCreateOpen(false);
      setKeyName("");
      toast.success("API key generated successfully!");
    },
    onError: (err: any) => {
      toast.error(err.message || "Failed to create API key.");
    },
  });

  // Optimistic UI Update for Key Revocation
  const revokeMutation = useMutation({
    mutationFn: apiClient.revokeKey,
    onMutate: async (keyId) => {
      await queryClient.cancelQueries({ queryKey: ["keys", selectedTenantId] });
      const previousKeys = queryClient.getQueryData<{ items: ApiKey[]; total: number }>([
        "keys",
        selectedTenantId,
      ]);

      if (previousKeys) {
        queryClient.setQueryData(["keys", selectedTenantId], {
          items: previousKeys.items.filter((k) => k.id !== keyId),
          total: previousKeys.total - 1,
        });
      }
      return { previousKeys };
    },
    onError: (err, keyId, context) => {
      if (context?.previousKeys) {
        queryClient.setQueryData(["keys", selectedTenantId], context.previousKeys);
      }
      toast.error("Failed to revoke API key.");
    },
    onSuccess: () => {
      toast.success("API key permanently revoked.");
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["keys"] });
    },
  });

  const copyToClipboard = (text: string, label: string = "API key") => {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text);
      } else {
        const textArea = document.createElement("textarea");
        textArea.value = text;
        textArea.style.position = "fixed";
        textArea.style.left = "-999999px";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        document.execCommand("copy");
        document.body.removeChild(textArea);
      }
      toast.success(`Copied ${label} to clipboard!`);
    } catch {
      toast.error("Failed to copy to clipboard");
    }
  };

  const handleCopySecret = () => {
    if (createdSecret) {
      copyToClipboard(createdSecret.raw_key, "raw API key");
      setHasCopied(true);
      setTimeout(() => setHasCopied(false), 2000);
    }
  };

  return (
    <div className="flex-1 flex flex-col min-h-screen">
      <Header
        title="API Keys & Access Control"
        subtitle="Cryptographic SHA-256 tokens & zero-knowledge storage"
        selectedTenantId={selectedTenantId}
        onTenantChange={setSelectedTenantId}
      />

      <div className="p-6 space-y-6 flex-1 max-w-7xl w-full mx-auto">
        {/* Top Action Bar */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-zinc-100 tracking-tight">Active API Keys</h2>
            <p className="text-xs text-zinc-500">
              Only SHA-256 digests are stored in DB. Keys are verified via Redis in sub-milliseconds.
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
            <Plus className="h-3.5 w-3.5" /> Issue New API Key
          </button>
        </div>

        {/* Keys Table */}
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-zinc-800 text-zinc-400 uppercase tracking-wider bg-zinc-950/40">
                <tr>
                  <th className="py-2.5 px-3 font-medium">Key Name</th>
                  <th className="py-2.5 px-3 font-medium">Prefix</th>
                  <th className="py-2.5 px-3 font-medium">Tenant</th>
                  <th className="py-2.5 px-3 font-medium">Rate Limit</th>
                  <th className="py-2.5 px-3 font-medium">Status</th>
                  <th className="py-2.5 px-3 font-medium">Created</th>
                  <th className="py-2.5 px-3 font-medium text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60 font-mono">
                {keys.length > 0 ? (
                  keys.map((k) => {
                    const tenant = tenants.find((t) => t.id === k.tenant_id);
                    return (
                      <tr key={k.id} className="hover:bg-zinc-800/20 transition-colors">
                        <td className="py-2.5 px-3 font-medium text-zinc-100 flex items-center gap-2 font-sans">
                          <Lock className="h-3.5 w-3.5 text-zinc-400" />
                          {k.name}
                        </td>
                        <td className="py-2.5 px-3 text-zinc-300">
                          <button
                            onClick={() => copyToClipboard(k.full_key || k.key_prefix, k.full_key ? "full API key" : "key prefix")}
                            className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 font-medium border border-zinc-700/60 cursor-pointer transition-colors"
                            title="Click to copy API key"
                          >
                            <span>{k.key_prefix}...</span>
                            <Copy className="h-3 w-3 text-zinc-400" />
                          </button>
                        </td>
                        <td className="py-2.5 px-3 text-zinc-300 font-sans">
                          {tenant ? `${tenant.name} (${tenant.slug})` : k.tenant_id.slice(0, 8)}
                        </td>
                        <td className="py-2.5 px-3 text-zinc-300">
                          {k.rate_limit_override_rpm ? `${k.rate_limit_override_rpm} RPM` : "Default"}
                        </td>
                        <td className="py-2.5 px-3 font-sans">
                          <span className="flex items-center gap-1.5 text-emerald-400 font-medium text-[11px]">
                            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
                            Active
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-zinc-400 text-[11px]">
                          {new Date(k.created_at).toLocaleDateString()}
                        </td>
                        <td className="py-2.5 px-3 text-right">
                          <div className="flex items-center justify-end gap-1">
                            <button
                              onClick={() => copyToClipboard(k.full_key || k.key_prefix, k.full_key ? "full API key" : "key prefix")}
                              className="text-zinc-500 hover:text-zinc-200 p-1 rounded transition-colors cursor-pointer"
                              title="Copy Full API Key"
                            >
                              <Copy className="h-3.5 w-3.5" />
                            </button>
                            <button
                              onClick={() => {
                                if (confirm(`Permanently revoke key '${k.name}'?`)) {
                                  revokeMutation.mutate(k.id);
                                }
                              }}
                              className="text-zinc-500 hover:text-rose-400 p-1 rounded transition-colors cursor-pointer"
                              title="Revoke Key"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-zinc-500 font-sans text-xs">
                      No API keys found. Click &quot;Issue New API Key&quot; to generate your first key.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Modal 1: Create Key Form */}
        {isCreateOpen && (
          <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl max-w-md w-full p-6 shadow-xl space-y-5">
              <div className="flex items-center justify-between border-b border-zinc-800 pb-3.5">
                <div className="flex items-center gap-2">
                  <KeyRound className="h-4 w-4 text-zinc-300" />
                  <h3 className="text-sm font-semibold text-zinc-100">Issue API Key</h3>
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
                        {t.name} ({t.slug}) - {t.plan_tier.toUpperCase()}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1">
                    Key Friendly Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={keyName}
                    onChange={(e) => setKeyName(e.target.value)}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-100 focus:outline-none focus:border-zinc-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1">
                    Rate Limit Override (Optional RPM)
                  </label>
                  <input
                    type="number"
                    placeholder="Leave empty to use tenant tier default"
                    value={rateLimitOverride || ""}
                    onChange={(e) =>
                      setRateLimitOverride(e.target.value ? parseInt(e.target.value) : undefined)
                    }
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
                        name: keyName,
                        rate_limit_override_rpm: rateLimitOverride,
                      });
                    }}
                    disabled={createMutation.isPending}
                    className="px-4 py-2 text-xs font-medium bg-zinc-100 hover:bg-white text-zinc-950 rounded-md transition-colors disabled:opacity-50"
                  >
                    {createMutation.isPending ? "Generating..." : "Generate Key"}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Modal 2: One-Time Secret Copy Modal */}
        {createdSecret && (
          <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl max-w-md w-full p-6 shadow-xl space-y-5">
              <div>
                <h3 className="text-sm font-semibold text-zinc-100">Save Your API Key</h3>
                <p className="text-xs text-zinc-400 mt-1">
                  This key will never be shown again. Store it in a secure secret store.
                </p>
              </div>

              <div className="p-3.5 rounded-lg bg-zinc-950 border border-zinc-800 space-y-2">
                <span className="text-[10px] font-medium text-zinc-500 uppercase tracking-wider block">
                  Raw API Key (`X-API-Key`)
                </span>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    readOnly
                    value={createdSecret.raw_key}
                    className="w-full bg-zinc-900 border border-zinc-800 rounded-md px-2.5 py-1.5 text-xs font-mono text-zinc-200 select-all focus:outline-none"
                  />
                  <button
                    onClick={handleCopySecret}
                    className="flex items-center gap-1.5 bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-medium px-3 py-1.5 rounded-md transition-colors shrink-0 cursor-pointer"
                  >
                    {hasCopied ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5" />}
                    {hasCopied ? "Copied" : "Copy"}
                  </button>
                </div>
              </div>

              <div className="pt-2 flex justify-end">
                <button
                  onClick={() => setCreatedSecret(null)}
                  className="w-full bg-zinc-800 hover:bg-zinc-700 text-zinc-100 text-xs font-medium py-2 rounded-md transition-colors"
                >
                  Done
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
