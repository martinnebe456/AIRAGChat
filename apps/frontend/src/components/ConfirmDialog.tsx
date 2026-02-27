import { Dialog, DialogBody, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "./Dialog";

type ConfirmDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  tone?: "default" | "warning";
  isPending?: boolean;
  onConfirm: () => void;
};

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  tone = "default",
  isPending = false,
  onConfirm,
}: ConfirmDialogProps) {
  return (
    <Dialog open={open} onOpenChange={(next) => (!isPending ? onOpenChange(next) : undefined)} closeOnOverlayClick={!isPending} closeOnEsc={!isPending}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          {description ? <DialogDescription>{description}</DialogDescription> : null}
        </DialogHeader>
        <DialogBody>
          <div className="separator-soft" />
        </DialogBody>
        <DialogFooter>
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            disabled={isPending}
            className="rounded-lg border border-ink/12 bg-white/85 px-3 py-2 text-sm text-ink disabled:opacity-60"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            data-dialog-autofocus
            onClick={onConfirm}
            disabled={isPending}
            className={
              tone === "warning"
                ? "rounded-lg border border-[#FADA7A]/90 bg-[#F5F0CD] px-3 py-2 text-sm font-medium text-ink disabled:opacity-60"
                : "rounded-lg bg-ink px-3 py-2 text-sm font-medium text-paper disabled:opacity-60"
            }
          >
            {isPending ? "Working..." : confirmLabel}
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
