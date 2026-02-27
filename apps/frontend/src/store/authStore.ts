import { create } from "zustand";

import { apiClient } from "../api/client";

type Me = {
  id: string;
  username: string;
  email: string;
  display_name: string;
  role: "user" | "contributor" | "admin";
  is_active: boolean;
};

type AuthState = {
  accessToken: string | null;
  me: Me | null;
  loading: boolean;
  setAccessToken: (token: string | null) => void;
  refreshSession: () => Promise<boolean>;
  login: (usernameOrEmail: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  loadMe: () => Promise<void>;
};

export const useAuthStore = create<AuthState>((set, get) => ({
  accessToken: null,
  me: null,
  loading: true,
  setAccessToken: (token) => set({ accessToken: token }),
  async refreshSession() {
    try {
      const tokenResp = await apiClient.post<{ access_token: string }>("/auth/refresh");
      set({ accessToken: tokenResp.access_token });
      await get().loadMe();
      return true;
    } catch {
      set({ accessToken: null, me: null, loading: false });
      return false;
    }
  },
  async login(usernameOrEmail, password) {
    const tokenResp = await apiClient.post<{ access_token: string }>("/auth/login", {
      username_or_email: usernameOrEmail,
      password,
    });
    set({ accessToken: tokenResp.access_token });
    await get().loadMe();
  },
  async logout() {
    try {
      await apiClient.post("/auth/logout");
    } finally {
      set({ accessToken: null, me: null, loading: false });
    }
  },
  async loadMe() {
    const me = await apiClient.get<Me>("/auth/me");
    set({ me, loading: false });
  },
}));

