import { AlertCircle } from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

export const FormDialog = ({ open, onOpenChange, title, description, onSubmit, busy, error, submitLabel = "Save", testId, children, destructive }) => (
  <Dialog open={open} onOpenChange={onOpenChange}>
    <DialogContent data-testid={testId} className="max-h-[90vh] w-[calc(100vw-2rem)] max-w-md overflow-y-auto rounded-lg">
      <DialogHeader className="text-left">
        <DialogTitle className="text-base">{title}</DialogTitle>
        {description && <DialogDescription className="text-sm">{description}</DialogDescription>}
      </DialogHeader>
      <form onSubmit={(e) => { e.preventDefault(); onSubmit(); }} className="space-y-4" noValidate>
        {error && (
          <p data-testid={`${testId}-error`} role="alert" className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /> {error}
          </p>
        )}
        {children}
        <DialogFooter className="flex-row justify-end gap-2 sm:space-x-0">
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)} data-testid={`${testId}-cancel`}>Cancel</Button>
          <Button type="submit" disabled={busy} variant={destructive ? "destructive" : "default"} data-testid={`${testId}-submit`}>
            {busy ? "Saving…" : submitLabel}
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
);

export const TextArea = ({ id, label, error, ...props }) => (
  <div className="space-y-1.5">
    <label htmlFor={id} className="text-xs font-medium text-slate-700">{label}</label>
    <textarea
      id={id}
      data-testid={`input-${id}`}
      rows={3}
      aria-invalid={!!error}
      className={`focus-ring w-full rounded-md border bg-white px-3 py-2 text-sm ${error ? "border-red-400" : "border-input"}`}
      {...props}
    />
    {error && <p data-testid={`field-error-${id}`} className="text-xs text-red-600">{error}</p>}
  </div>
);

export const toInt = (v) => (v === "" || v == null ? v : Number(v));
