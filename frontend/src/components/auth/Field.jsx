import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export const Field = ({ id, label, error, ...props }) => (
  <div className="space-y-1.5">
    <Label htmlFor={id} className="text-xs font-medium text-slate-700">{label}</Label>
    <Input
      id={id}
      data-testid={`input-${id}`}
      aria-invalid={!!error}
      className={`h-10 bg-white ${error ? "border-red-400 focus-visible:ring-red-300" : ""}`}
      {...props}
    />
    {error && <p data-testid={`field-error-${id}`} className="text-xs text-red-600">{error}</p>}
  </div>
);
