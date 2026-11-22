import { useCallback, useEffect, useState } from "react";
import { Download, Lock, Paperclip } from "lucide-react";
import { toast } from "sonner";
import { api, formatApiError } from "@/lib/api";
import { useAction } from "@/hooks/useAction";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/common/States";
import { TextArea } from "@/components/common/FormDialog";
import { Timeline } from "@/components/lending/Timeline";
import { HandoverStatus, PriorityPill } from "@/components/handover/HandoverBits";
import { BAD_FILE, fileOk } from "@/components/handover/HandoverDialog";

const Section = ({ label, text, testId }) => text ? (
  <div><div className="eyebrow mb-1">{label}</div><p data-testid={testId} className="whitespace-pre-wrap text-sm text-slate-700">{text}</p></div>
) : null;

const download = async (taskId, a) => {
  try {
    const { data } = await api.get(`/handovers/${taskId}/attachments/${a.id}`, { responseType: "blob" });
    const url = URL.createObjectURL(data);
    const link = Object.assign(document.createElement("a"), { href: url, download: a.filename });
    link.click();
    URL.revokeObjectURL(url);
  } catch (e) { toast.error(formatApiError(e)); }
};

const Actions = ({ t, act }) => {
  const [note, setNote] = useState("");
  const [mode, setMode] = useState(null);
  const go = async (path, body, msg) => { if (await act(path, body, msg)) { setMode(null); setNote(""); } };
  if (mode) {
    return (
      <div className="space-y-2" data-testid={`handover-${mode}-form`}>
        <TextArea id={`${mode}-note`} label={mode === "reject" ? "Reason for rejecting" : "Completion note (optional)"} value={note} onChange={(e) => setNote(e.target.value)} />
        <div className="flex gap-2">
          <Button size="sm" data-testid={`handover-${mode}-submit`} variant={mode === "reject" ? "destructive" : "default"}
            onClick={() => go(`/handovers/${t.id}/${mode}`, { note }, mode === "reject" ? "Handover rejected" : "Marked complete")}>
            {mode === "reject" ? "Reject" : "Mark complete"}</Button>
          <Button size="sm" variant="outline" onClick={() => setMode(null)}>Back</Button>
        </div>
      </div>
    );
  }
  return (
    <div className="flex flex-wrap gap-2">
      {t.actions.accept && <Button size="sm" data-testid="handover-accept" onClick={() => go(`/handovers/${t.id}/accept`, {}, "Handover accepted")}>Accept</Button>}
      {t.actions.reject && <Button size="sm" variant="outline" data-testid="handover-reject" onClick={() => setMode("reject")}>Reject</Button>}
      {t.actions.complete && <Button size="sm" data-testid="handover-complete" onClick={() => setMode("complete")}>Mark complete</Button>}
      {t.actions.cancel && <Button size="sm" variant="outline" data-testid="handover-cancel" onClick={() => go(`/handovers/${t.id}/cancel`, {}, "Handover cancelled")}>Cancel handover</Button>}
    </div>
  );
};

export const HandoverSheet = ({ taskId, onClose, onChanged, onEdit }) => {
  const [t, setT] = useState(null);
  const [loadError, setLoadError] = useState("");
  const action = useAction();
  const load = useCallback(async () => {
    setLoadError("");
    try { setT((await api.get(`/handovers/${taskId}`)).data); } catch (e) { setLoadError(formatApiError(e)); }
  }, [taskId]);
  useEffect(() => { setT(null); action.reset(); if (taskId) load(); }, [taskId, load]); // eslint-disable-line react-hooks/exhaustive-deps

  const act = async (path, body, msg) => {
    const res = await action.run(() => api.post(path, body), msg);
    if (res) { setT(res); onChanged(); } else load();
    return res;
  };
  const attach = async (e) => {
    const f = e.target.files[0];
    e.target.value = "";
    if (!f) return;
    if (!fileOk(f)) return toast.error(BAD_FILE);
    const fd = new FormData();
    fd.append("file", f);
    if (await action.run(() => api.post(`/handovers/${t.id}/attachments`, fd), "Attachment added")) { load(); onChanged(); }
  };

  return (
    <Sheet open={!!taskId} onOpenChange={(o) => !o && onClose()}>
      <SheetContent side="right" data-testid="handover-sheet" className="w-full overflow-y-auto sm:max-w-lg">
        <SheetHeader className="mb-5 text-left">
          <SheetTitle data-testid="handover-title">{t?.title || "Handover"}</SheetTitle>
          <SheetDescription>{t ? `${t.creator_name} → ${t.assignee_name}` : "Loading"}</SheetDescription>
        </SheetHeader>
        {loadError ? <ErrorState message={loadError} onRetry={load} /> : !t ? <Skeleton className="h-64" /> : (
          <div className="space-y-5">
            <div className="flex flex-wrap items-center gap-1.5"><HandoverStatus status={t.status} testId="handover-status" /><PriorityPill priority={t.priority} /></div>
            {t.rejection_reason && <p data-testid="handover-rejection-reason" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">Rejected: “{t.rejection_reason}”</p>}
            {t.completion_note && <p data-testid="handover-completion-note" className="rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-700">Completed: “{t.completion_note}”</p>}
            {action.error && <p data-testid="handover-action-error" className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{action.error}</p>}
            <Actions t={t} act={act} />
            {t.actions.edit && <Button size="sm" variant="ghost" data-testid="handover-edit" onClick={() => onEdit(t)}>Edit details</Button>}
            {t.content_restricted ? (
              <p data-testid="handover-restricted-note" className="flex items-start gap-2 rounded-md border border-border bg-slate-50 px-3.5 py-2.5 text-sm text-slate-600">
                <Lock className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" /> {t.restricted_note} You can see who, what, status and dates.
              </p>
            ) : <>
            <Section label="Objective" text={t.objective} testId="handover-objective" />
            <Section label="Description" text={t.description} />
            <Section label="Completed work" text={t.completed_work} />
            <Section label="Pending work" text={t.pending_work} testId="handover-pending-work" />
            <Section label="Context notes" text={t.context_notes} />
            </>}
            <div className={t.content_restricted ? "hidden" : ""}>
              <div className="eyebrow mb-2">Attachments · {t.attachments.length}</div>
              <ul className="space-y-1.5">
                {t.attachments.map((a) => (
                  <li key={a.id}>
                    <button type="button" data-testid={`attachment-${a.id}`} onClick={() => download(t.id, a)}
                      className="focus-ring flex w-full items-center gap-2 rounded-md border border-border-subtle px-3 py-2 text-left text-sm hover:bg-slate-50">
                      <Paperclip className="h-3.5 w-3.5 text-slate-400" /><span className="flex-1 truncate">{a.filename}</span>
                      <span className="text-xs text-slate-400">{Math.ceil(a.size / 1024)} KB</span><Download className="h-3.5 w-3.5 text-slate-400" />
                    </button>
                  </li>
                ))}
              </ul>
              {t.actions.attach && t.attachments.length < 5 && (
                <label className="mt-2 inline-flex cursor-pointer items-center gap-1.5 text-sm font-medium text-indigo-600">
                  <Paperclip className="h-4 w-4" /> Add attachment
                  <input data-testid="handover-sheet-file-input" type="file" className="sr-only" accept=".pdf,.png,.jpg,.jpeg,.docx,.txt,.md" onChange={attach} />
                </label>
              )}
            </div>
            <div><div className="eyebrow mb-3">History</div><Timeline items={t.history} testId="handover-timeline" /></div>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
};
