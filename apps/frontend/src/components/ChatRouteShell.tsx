import { createContext, useContext, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";

import { useAuthStore } from "../store/authStore";
import { AppNavDrawer } from "./AppNavDrawer";

type ChatRouteShellContextValue = {
  openNavDrawer: () => void;
  closeNavDrawer: () => void;
};

const ChatRouteShellContext = createContext<ChatRouteShellContextValue | null>(null);

export function useChatRouteShell() {
  const ctx = useContext(ChatRouteShellContext);
  if (!ctx) {
    return {
      openNavDrawer: () => {},
      closeNavDrawer: () => {},
    } satisfies ChatRouteShellContextValue;
  }
  return ctx;
}

export function ChatRouteShell({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const { me, logout } = useAuthStore();
  const [drawerOpen, setDrawerOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <ChatRouteShellContext.Provider
      value={{
        openNavDrawer: () => setDrawerOpen(true),
        closeNavDrawer: () => setDrawerOpen(false),
      }}
    >
      <div className="box-border h-[100dvh] overflow-hidden p-3 md:p-4 lg:p-5">
        <div className="mx-auto h-full w-full max-w-[1700px]">
          {children}
        </div>
      </div>
      <AppNavDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        userName={me?.display_name}
        userRole={me?.role}
        isAdmin={me?.role === "admin"}
        onLogout={handleLogout}
        title="Navigation"
      />
    </ChatRouteShellContext.Provider>
  );
}
