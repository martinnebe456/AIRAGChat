import type { ReactNode } from "react";
import clsx from "clsx";

export function PageCard({
  title,
  subtitle,
  children,
  actions,
  variant = "glass",
  framed = false,
  density = "comfortable",
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  actions?: ReactNode;
  variant?: "glass" | "soft" | "plain" | "panelDark";
  framed?: boolean;
  density?: "comfortable" | "compact";
}) {
  const variantClass =
    variant === "plain"
      ? "bg-transparent shadow-none backdrop-blur-0"
      : variant === "soft"
        ? "bg-white/45 shadow-[0_10px_24px_rgba(54,116,181,0.10)] backdrop-blur-lg"
        : variant === "panelDark"
          ? "rail-dark text-white shadow-[var(--shadow-rail)]"
          : "surface-glass shadow-panel backdrop-blur-xl";
  return (
    <section
      className={clsx(
        "rounded-2xl",
        variant === "panelDark"
          ? framed
            ? "border border-white/12"
            : "border border-white/8"
          : framed
            ? "border border-white/70"
            : "border border-white/45",
        variantClass,
        density === "compact" ? "p-4" : "p-5",
      )}
    >
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className={clsx("text-lg font-semibold", variant === "panelDark" ? "text-white" : "text-ink")}>
            {title}
          </h1>
          {subtitle && (
            <p className={clsx("mt-1 text-sm", variant === "panelDark" ? "text-white/65" : "text-ink/65")}>
              {subtitle}
            </p>
          )}
        </div>
        {actions}
      </div>
      {children}
    </section>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="surface-soft rounded-xl border border-dashed border-ink/8 p-6 text-center text-sm text-ink/65">
      {message}
    </div>
  );
}

export function LoadingState({ message = "Loading..." }: { message?: string }) {
  return <div className="p-4 text-sm text-ink/70">{message}</div>;
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-[#FADA7A]/65 bg-[#F5F0CD]/90 p-3 text-sm text-ink shadow-[0_8px_18px_rgba(250,218,122,0.18)]">
      {message}
    </div>
  );
}

export function ProviderBadge({ provider, category }: { provider: string; category?: string | null }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-ink/8 bg-white/72 px-2 py-1 text-xs text-ink/75">
      <span
        className={`inline-block h-2 w-2 rounded-full ${
          provider === "openai_api" ? "bg-sky" : "bg-moss"
        }`}
      />
      {provider}
      {category ? ` / ${category}` : ""}
    </span>
  );
}

export function Surface({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={clsx("surface-soft rounded-xl p-4", className)}>{children}</div>;
}

export function SectionHeader({
  title,
  subtitle,
  actions,
  dark = false,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  dark?: boolean;
}) {
  return (
    <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 className={clsx("text-sm font-semibold", dark ? "text-white" : "text-ink")}>{title}</h2>
        {subtitle ? (
          <p className={clsx("mt-1 text-xs", dark ? "text-white/62" : "text-ink/60")}>{subtitle}</p>
        ) : null}
      </div>
      {actions}
    </div>
  );
}

export function Toolbar({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={clsx(
        "flex flex-wrap items-center justify-between gap-2 rounded-xl border border-ink/8 bg-white/55 px-3 py-2",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function ListRow({
  children,
  active = false,
  className,
}: {
  children: ReactNode;
  active?: boolean;
  className?: string;
}) {
  return (
    <div
      className={clsx(
        "rounded-xl border px-3 py-2.5",
        active ? "border-ink/12 bg-white/88 shadow-soft" : "border-ink/8 bg-white/58 hover:bg-white/75",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function TableSurface({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={clsx("overflow-hidden rounded-xl border border-ink/8 bg-white/55", className)}>
      {children}
    </div>
  );
}

export function StatPill({
  label,
  value,
  className,
}: {
  label: string;
  value: ReactNode;
  className?: string;
}) {
  return (
    <div className={clsx("rounded-xl border border-ink/8 bg-white/75 px-3 py-2", className)}>
      <div className="text-[11px] uppercase tracking-[0.12em] text-ink/55">{label}</div>
      <div className="mt-1 text-lg font-semibold text-ink">{value}</div>
    </div>
  );
}
