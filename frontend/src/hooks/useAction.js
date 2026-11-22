import { useState } from "react";
import { toast } from "sonner";
import { fieldErrors, formatApiError } from "@/lib/api";

// Runs a mutation, tracking busy state plus form-level and field-level errors.
export function useAction() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [fields, setFields] = useState({});

  const reset = () => { setError(""); setFields({}); };

  const run = async (fn, success) => {
    setBusy(true);
    reset();
    try {
      const res = await fn();
      if (success) toast.success(success);
      return res?.data ?? true;
    } catch (e) {
      const f = fieldErrors(e);
      setFields(f);
      const msg = formatApiError(e);
      if (!Object.keys(f).length) setError(msg);
      if (e?.response?.status === 409) toast.error(msg);
      return null;
    } finally {
      setBusy(false);
    }
  };

  return { busy, error, fields, run, reset, setFields };
}
