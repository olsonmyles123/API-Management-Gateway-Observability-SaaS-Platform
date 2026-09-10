"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { User } from "@/lib/types";
import { apiClient } from "@/lib/api-client";
import { useRouter, usePathname } from "next/navigation";
import { toast } from "sonner";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    async function initUser() {
      try {
        const currentUser = await apiClient.getMe();
        setUser(currentUser);
      } catch {
        setUser(null);
      } finally {
        setLoading(false);
      }
    }
    initUser();
  }, []);

  const login = async (email: string, password: string) => {
    try {
      const res = await apiClient.login({ email, password });
      if (res.access_token) {
        localStorage.setItem("auth_token", res.access_token);
      }
      setUser(res.user);
      toast.success(`Welcome back, ${res.user.full_name || res.user.email}!`);
      router.push("/");
    } catch (err: any) {
      toast.error(err.message || "Invalid login credentials.");
      throw err;
    }
  };

  const register = async (email: string, password: string, fullName?: string) => {
    try {
      const res = await apiClient.register({ email, password, full_name: fullName });
      if (res.access_token) {
        localStorage.setItem("auth_token", res.access_token);
      }
      setUser(res.user);
      toast.success("Account created successfully!");
      router.push("/");
    } catch (err: any) {
      toast.error(err.message || "Registration failed.");
      throw err;
    }
  };

  const logout = async () => {
    try {
      await apiClient.logout();
    } catch {
      // Ignore network errors on logout
    }
    localStorage.removeItem("auth_token");
    setUser(null);
    toast.info("Logged out successfully.");
    router.push("/login");
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
