import { create } from "zustand";

export interface AuthUser {
  id?: number;
  email?: string;
  full_name?: string;
  role?: string;
  /** Some endpoints return a roles array; we treat the first entry as the active role. */
  roles?: string[];
  profile_picture_url?: string | null;
  [key: string]: unknown;
}

interface AuthState {
  user: AuthUser | null;
  setUser: (user: AuthUser | null) => void;
  logout: () => void;
}

function getInitialUser(): AuthUser | null {
  try {
    const stored = localStorage.getItem("user");
    if (stored) {
      try {
        return JSON.parse(stored) as AuthUser;
      } catch {
        // fall through
      }
    }
    // Reconstruct minimal user for sessions that predate user persistence
    const role = localStorage.getItem("role");
    if (role) {
      return { role };
    }
  } catch {
    /* ignore storage errors (e.g. SSR or disabled storage) */
  }
  return null;
}

// Auth tokens are stored as httpOnly cookies (set by the backend on
// /auth/login and /auth/refresh). The store no longer holds the access token.
// Components that need to know whether the user is authenticated can read
// `user` (populated on login + on app reload from localStorage).
export const useAuthStore = create<AuthState>((set) => ({
  user: getInitialUser(),

  setUser: (user) => set({ user }),

  logout: () => {
    try {
      localStorage.removeItem("user");
      localStorage.removeItem("role");
    } catch {
      /* ignore */
    }
    set({ user: null });
  },
}));

// Listen for global 401s emitted by the API helper and clear auth state so
// any subscribed component re-renders / route guards kick in immediately
// (the helper itself also handles the redirect to "/").
if (typeof window !== "undefined") {
  window.addEventListener("auth:unauthorized", () => {
    useAuthStore.setState({ user: null });
  });
}
