import { createPortal } from "react-dom";
import { useEffect } from "react";
import { NavLink, useLocation } from "react-router-dom";

import { getAppNavigationSections } from "./appNavigation";

type AppNavDrawerProps = {
  open: boolean;
  onClose: () => void;
  userName?: string | null;
  userRole?: string | null;
  isAdmin: boolean;
  onLogout: () => Promise<void> | void;
  title?: string;
  showHeaderBrand?: boolean;
};

const navClass = ({ isActive }: { isActive: boolean }) =>
  `flex items-center justify-between rounded-xl px-3 py-2 text-sm transition ${
    isActive
      ? "bg-white/18 text-white shadow-[inset_0_0_0_1px_rgba(255,255,255,0.16)]"
      : "text-white/78 hover:bg-white/10 hover:text-white"
  }`;

export function AppNavDrawer({
  open,
  onClose,
  userName,
  userRole,
  isAdmin,
  onLogout,
  title = "Navigation",
  showHeaderBrand = true,
}: AppNavDrawerProps) {
  const location = useLocation();
  const nav = getAppNavigationSections(isAdmin);

  useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", onKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [onClose, open]);

  useEffect(() => {
    if (!open) return;
    onClose();
  }, [location.pathname]); // close drawer after route change

  if (!open || typeof document === "undefined") return null;

  return createPortal(
    <div className="fixed inset-0 z-[120]" aria-modal="true" role="dialog">
      <button
        type="button"
        aria-label="Close navigation"
        className="drawer-backdrop absolute inset-0"
        onClick={onClose}
      />

      <aside className="drawer-panel rail-dark absolute inset-y-0 left-0 flex w-[min(90vw,340px)] flex-col p-4 shadow-floating">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            {showHeaderBrand ? (
              <div className="text-[11px] uppercase tracking-[0.18em] text-white/55">AIRAGChat</div>
            ) : null}
            <div className="mt-1 text-base font-semibold text-white">{title}</div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-white/15 bg-white/5 px-2.5 py-2 text-xs font-medium text-white/85 hover:bg-white/10"
          >
            Close
          </button>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto pr-1">
          {nav.main.map((item) => (
            <NavLink key={item.path} className={navClass} to={item.path}>
              <span>{item.label}</span>
              <span className="text-xs opacity-60">/</span>
            </NavLink>
          ))}

          {nav.admin.length > 0 ? (
            <>
              <div className="my-3 px-2 text-[11px] uppercase tracking-[0.16em] text-white/45">Admin</div>
              {nav.admin.map((item) => (
                <NavLink key={item.path} className={navClass} to={item.path}>
                  <span>{item.label}</span>
                  <span className="text-xs opacity-60">/</span>
                </NavLink>
              ))}
            </>
          ) : null}
        </nav>

        <div className="mt-4 rounded-2xl border border-white/10 bg-white/5 p-3">
          <div className="text-sm font-medium text-white">{userName ?? "User"}</div>
          <div className="mt-1 text-[11px] uppercase tracking-[0.12em] text-white/55">{userRole ?? "-"}</div>
          <button
            type="button"
            onClick={() => void onLogout()}
            className="mt-3 w-full rounded-xl bg-white/90 px-3 py-2 text-sm font-semibold text-[#3674B5] hover:bg-white"
          >
            Logout
          </button>
        </div>
      </aside>
    </div>,
    document.body,
  );
}

