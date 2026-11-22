import { useCallback, useEffect, useRef, useState } from "react";
import { api, formatApiError } from "@/lib/api";

export function useApi(path, params) {
  const key = JSON.stringify(params || {});
  const [state, setState] = useState({ data: null, loading: true, error: null });
  const reqId = useRef(0);

  const load = useCallback(async () => {
    const id = ++reqId.current;
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const { data } = await api.get(path, { params: JSON.parse(key) });
      if (id === reqId.current) setState({ data, loading: false, error: null });
    } catch (e) {
      if (id === reqId.current) setState({ data: null, loading: false, error: formatApiError(e) });
    }
  }, [path, key]);

  useEffect(() => { load(); }, [load]);

  return { ...state, reload: load };
}
