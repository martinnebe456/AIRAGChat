import type { ReactNode } from "react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAuthStore } from "../store/authStore";
import { AppNavDrawer } from "./AppNavDrawer";
import { TopHeader } from "./TopHeader";

export function AppLayout({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const { me, logout } = useAuthStore();
  const [drawerOpen, setDrawerOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <>
      <div className="mx-auto flex min-h-screen w-full max-w-[1480px] flex-col p-3 md:p-5">
        <TopHeader
          userName={me?.display_name}
          userRole={me?.role}
          onLogout={handleLogout}
          onOpenNav={() => setDrawerOpen(true)}
          subtitle="OpenAI RAG Platform"
        />

        <main className="flex-1 min-h-0">
          <div className="mx-auto w-full max-w-[1380px]">{children}</div>
        </main>
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
    </>
  );
}

