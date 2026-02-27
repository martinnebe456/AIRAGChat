import type { FormEvent, ReactNode } from "react";

import { Dialog, DialogBody, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "./Dialog";

type FormDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  children: ReactNode;
  submitLabel?: string;
  cancelLabel?: string;
  isSubmitting?: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  maxWidthClassName?: string;
};

export function FormDialog({
  open,
  onOpenChange,
  title,
  description,
  children,
  submitLabel = "Save",
  cancelLabel = "Cancel",
  isSubmitting = false,
  onSubmit,
  maxWidthClassName = "max-w-xl",
}: FormDialogProps) {
  return (
    <Dialog open={open} onOpenChange={(next) => (!isSubmitting ? onOpenChange(next) : undefined)} closeOnOverlayClick={!isSubmitting} closeOnEsc={!isSubmitting}>
      <DialogContent className={maxWidthClassName}>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onSubmit(e);
          }}
        >
          <DialogHeader>
            <DialogTitle>{title}</DialogTitle>
            {description ? <DialogDescription>{description}</DialogDescription> : null}
          </DialogHeader>
          <DialogBody>{children}</DialogBody>
          <DialogFooter>
            <button
              type="button"
              onClick={() => onOpenChange(false)}
              disabled={isSubmitting}
              className="rounded-lg border border-ink/12 bg-white/85 px-3 py-2 text-sm text-ink disabled:opacity-60"
            >
              {cancelLabel}
            </button>
            <button
              type="submit"
              data-dialog-autofocus
              disabled={isSubmitting}
              className="rounded-lg bg-ink px-3 py-2 text-sm font-medium text-paper disabled:opacity-60"
            >
              {isSubmitting ? "Saving..." : submitLabel}
            </button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
