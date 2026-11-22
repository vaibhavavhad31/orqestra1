import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAction } from "@/hooks/useAction";
import { Field } from "@/components/auth/Field";
import { FormDialog, toInt } from "@/components/common/FormDialog";

// Edit a single credit value (org budget, department budget or member allocation).
export const CreditsDialog = ({ target, onClose, onSaved }) => {
  const [value, setValue] = useState("");
  const { run, busy, fields, error, reset } = useAction();
  useEffect(() => { setValue(target ? String(target.value) : ""); reset(); }, [target]); // eslint-disable-line react-hooks/exhaustive-deps

  const submit = async () => {
    if (await run(() => api.put(target.path, { credits: toInt(value) }), "Saved")) onSaved();
  };

  return (
    <FormDialog open={!!target} onOpenChange={(o) => !o && onClose()} title={target?.title} description={target?.description}
      onSubmit={submit} busy={busy} error={error} testId="credits-dialog">
      <Field id="credits" label="Monthly credits" type="number" inputMode="numeric" min="0" step="1" value={value}
        onChange={(e) => setValue(e.target.value)} error={fields.credits} />
    </FormDialog>
  );
};
