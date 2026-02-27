import type { ReactNode } from "react";

type TopHeaderProps = {
  appName?: string;
  subtitle?: string;
  userName?: string | null;
  userRole?: string | null;
  onLogout: () => Promise<void> | void;
  onOpenNav?: () => void;
  actions?: ReactNode;
};

export function TopHeader({
  appName = "AIRAGChat",
  subtitle = "OpenAI RAG Platform",
  userName,
  userRole,
  onLogout,
  onOpenNav,
  actions,
}: TopHeaderProps) {
  return (
    <header className="surface-glass sticky top-3 z-20 mb-4 flex items-center justify-between gap-3 rounded-[1.15rem] border border-white/55 px-4 py-3 backdrop-blur-xl">
      <div className="flex min-w-0 items-center gap-2">
        {onOpenNav ? (
          <button
            type="button"
            onClick={onOpenNav}
            className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-ink/10 bg-white/75 text-ink transition hover:bg-white"
            aria-label="Open navigation"
          >
            <span className="block h-[2px] w-4 rounded bg-current shadow-[0_-5px_0_0_currentColor,0_5px_0_0_currentColor]" />
          </button>
        ) : null}
        <div className="min-w-0">
        <div className="text-[11px] uppercase tracking-[0.16em] text-ink/55">{appName}</div>
        <div className="truncate text-sm font-semibold text-ink md:text-base">{subtitle}</div>
        </div>
      </div>
      <div className="flex items-center gap-2">
        {actions}
        <div className="hidden items-center gap-2 rounded-full border border-white/50 bg-white/70 px-3 py-1.5 md:flex">
          <div className="text-right leading-tight">
            <div className="max-w-[160px] truncate text-xs font-medium text-ink">{userName ?? "User"}</div>
            <div className="text-[11px] uppercase tracking-[0.1em] text-ink/55">{userRole ?? "-"}</div>
          </div>
        </div>
        <button
          type="button"
          onClick={() => void onLogout()}
          className="rounded-xl border border-ink/10 bg-ink px-3 py-2 text-sm font-medium text-paper shadow-soft hover:bg-ink/90"
        >
          Logout
        </button>
      </div>
    </header>
  );
}
