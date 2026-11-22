import { X } from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const ALL = "all";

const FilterSelect = ({ id, label, value, onChange, options, allLabel }) => (
  <Select value={value || ALL} onValueChange={(v) => onChange(v === ALL ? undefined : v)}>
    <SelectTrigger data-testid={`usage-filter-${id}`} aria-label={label} className="h-9 w-full bg-white text-sm sm:w-[190px]">
      <SelectValue placeholder={allLabel} />
    </SelectTrigger>
    <SelectContent>
      <SelectItem value={ALL} data-testid={`usage-filter-${id}-all`}>{allLabel}</SelectItem>
      {options.map((o) => (
        <SelectItem key={o.id} value={o.id} data-testid={`usage-filter-${id}-option-${o.id}`}>{o.name}</SelectItem>
      ))}
    </SelectContent>
  </Select>
);

export const UsageFilters = ({ filters, setFilters, providers, options, scopeType }) => {
  const members = filters.department_id
    ? options.members.filter((m) => m.department_id === filters.department_id)
    : options.members;
  const active = filters.provider || filters.department_id || filters.member_id;
  return (
    <div data-testid="usage-filters" className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
      <FilterSelect id="provider" label="Filter by provider" allLabel="All providers" value={filters.provider}
        options={providers} onChange={(provider) => setFilters({ ...filters, provider })} />
      {scopeType === "organisation" && (
        <FilterSelect id="department" label="Filter by department" allLabel="All departments" value={filters.department_id}
          options={options.departments} onChange={(department_id) => setFilters({ ...filters, department_id, member_id: undefined })} />
      )}
      {scopeType !== "self" && (
        <FilterSelect id="member" label="Filter by member" allLabel="All members" value={filters.member_id}
          options={members} onChange={(member_id) => setFilters({ ...filters, member_id })} />
      )}
      {active && (
        <button type="button" data-testid="usage-filters-clear" onClick={() => setFilters({})}
          className="focus-ring inline-flex h-9 items-center gap-1 rounded-md px-2.5 text-xs font-medium text-slate-500 hover:bg-slate-100 hover:text-slate-800">
          <X className="h-3.5 w-3.5" /> Clear filters
        </button>
      )}
    </div>
  );
};
