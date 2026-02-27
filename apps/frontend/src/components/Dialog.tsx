import { useEffect, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";

import clsx from "clsx";

type DialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: ReactNode;
  closeOnOverlayClick?: boolean;
  closeOnEsc?: boolean;
};

export function Dialog({
  open,
  onOpenChange,
  children,
  closeOnOverlayClick = true,
  closeOnEsc = true,
}: DialogProps) {
  const overlayRef = useRef<HTMLDivElement | null>(null);
  const panelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && closeOnEsc) {
        event.preventDefault();
        onOpenChange(false);
      }
    };
    window.addEventListener("keydown", onKeyDown);

    queueMicrotask(() => {
      const autoFocus = panelRef.current?.querySelector<HTMLElement>("[data-dialog-autofocus]");
      (autoFocus ?? panelRef.current)?.focus();
    });

    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [closeOnEsc, onOpenChange, open]);

  if (!open || typeof document === "undefined") return null;

  return createPortal(
    <div
      ref={overlayRef}
      className="modal-backdrop fixed inset-0 z-[100] flex items-center justify-center p-4 md:p-6"
      onMouseDown={(e) => {
        if (!closeOnOverlayClick) return;
        if (e.target === overlayRef.current) onOpenChange(false);
      }}
    >
      <div className="w-full max-w-2xl">
        <div ref={panelRef} tabIndex={-1} className="outline-none">
          {children}
        </div>
      </div>
    </div>,
    document.body,
  );
}

export function DialogContent({
  className,
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return (
    <div
      role="dialog"
      aria-modal="true"
      className={clsx("modal-panel surface-glass mx-auto rounded-2xl p-4 md:p-5", className)}
      onMouseDown={(e) => e.stopPropagation()}
    >
      {children}
    </div>
  );
}

export function DialogHeader({ children }: { children: ReactNode }) {
  return <div className="mb-4 space-y-1">{children}</div>;
}

export function DialogTitle({ children }: { children: ReactNode }) {
  return <h2 className="text-base font-semibold text-ink md:text-lg">{children}</h2>;
}

export function DialogDescription({ children }: { children: ReactNode }) {
  return <p className="text-sm text-ink/65">{children}</p>;
}

export function DialogBody({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={clsx("space-y-3", className)}>{children}</div>;
}

export function DialogFooter({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={clsx("mt-5 flex flex-wrap justify-end gap-2", className)}>{children}</div>;
}
