import { useCallback, useEffect, useMemo, useState } from "react";

export interface PaginationState {
  page: number;
  page_size: number;
  total: number;
}

export interface SortState {
  sort_by: string | null;
  sort_order: "asc" | "desc" | null;
}

interface PaginatedResponse<TRow> {
  data?: TRow[];
  page?: number;
  page_size?: number;
  total?: number;
  pagination?: { page?: number; page_size?: number; total?: number };
}

type Filters = Record<string, unknown>;

interface UsePaginatedTableArgs<TRow> {
  fetcher: (params: Record<string, unknown>) => Promise<PaginatedResponse<TRow>>;
  defaultFilters?: Filters;
  initialFilters?: Filters;
  initialPageSize?: number;
  initialSort?: SortState;
}

export interface UsePaginatedTableResult<TRow> {
  rows: TRow[];
  loading: boolean;
  error: string | null;
  pagination: PaginationState;
  filters: Filters;
  /** First active sort, for backward compat with single-sort consumers. */
  sort: SortState;
  /** Full ordered list of active sorts (multi-column). */
  sorts: SortState[];
  updateFilters: (patch: Filters) => void;
  resetAllFilters: () => void;
  // Accept Ant Design Table.onChange args: (pagination, filters, sorter)
  handleTableChange: (
    p: { current?: number; pageSize?: number },
    tableFilters?: Record<string, (string | number | boolean)[] | null>,
    sorter?: unknown,
  ) => void;
  loadData: (extra?: Filters) => Promise<void>;
}

type AntSorter = {
  field?: string | string[];
  columnKey?: string;
  order?: "ascend" | "descend" | null;
};

function sorterToSortState(s: AntSorter | undefined | null): SortState | null {
  if (!s || !s.order) return null;
  // Prefer columnKey so the backend receives a stable identifier that
  // matches the column's `key` (independent of the underlying dataIndex).
  const field =
    s.columnKey ||
    (Array.isArray(s.field) ? s.field.join(".") : s.field) ||
    null;
  if (!field) return null;
  return {
    sort_by: String(field),
    sort_order: s.order === "ascend" ? "asc" : "desc",
  };
}

function normalizeSorter(sorter: unknown): SortState[] | null {
  if (!sorter) return null;
  const list = Array.isArray(sorter) ? sorter : [sorter as AntSorter];
  const out: SortState[] = [];
  for (const item of list) {
    const next = sorterToSortState(item as AntSorter);
    if (next) out.push(next);
  }
  // An empty array means "no active sort" (user toggled the last column off).
  // Return [] so the caller can distinguish from `null` (sorter param missing).
  return out;
}

/**
 * Generic server-side paginated/filtered/sorted table hook.
 *
 * Compatible with backends that return either:
 *   - `{ data, page, page_size, total }` (flat shape), or
 *   - `{ data, pagination: { page, page_size, total } }` (nested shape).
 *
 * Sorting is wired through Ant Design Table's `onChange(pagination, _, sorter)`
 * callback — the sorter's columnKey maps to `sort_by` and the order to
 * `sort_order` (`asc`/`desc`). For columns to opt-in to server-side sorting,
 * set `sorter: true` (or `{ multiple: n }` for multi-column sort) on the
 * column definition. When multiple sorts are active, `sort_by` and
 * `sort_order` are sent as comma-separated values in the same order.
 */
export function usePaginatedTable<TRow = unknown>({
  fetcher,
  defaultFilters = {},
  initialFilters = {},
  initialPageSize = 20,
  initialSort,
}: UsePaginatedTableArgs<TRow>): UsePaginatedTableResult<TRow> {
  const [rows, setRows] = useState<TRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pagination, setPagination] = useState<PaginationState>({
    page: 1,
    page_size: initialPageSize,
    total: 0,
  });
  const [filters, setFilters] = useState<Filters>({
    ...defaultFilters,
    ...initialFilters,
  });
  const [sorts, setSorts] = useState<SortState[]>(
    initialSort && initialSort.sort_by ? [initialSort] : [],
  );

  const sortKey = sorts.map((s) => `${s.sort_by}:${s.sort_order}`).join("|");

  const loadData = useCallback(
    async (extra: Filters = {}) => {
      setLoading(true);
      setError(null);
      try {
        const params: Record<string, unknown> = {
          page: pagination.page,
          page_size: pagination.page_size,
          ...filters,
          ...extra,
        };
        if (sorts.length > 0) {
          params.sort_by = sorts.map((s) => s.sort_by).join(",");
          params.sort_order = sorts
            .map((s) => s.sort_order || "asc")
            .join(",");
        }
        const result = await fetcher(params);

        const page = result.pagination?.page ?? result.page ?? Number(params.page);
        const pageSize =
          result.pagination?.page_size ?? result.page_size ?? Number(params.page_size);
        const total = result.pagination?.total ?? result.total ?? 0;

        setRows(result.data ?? []);
        setPagination((prev) => ({ ...prev, page, page_size: pageSize, total }));
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Failed to load data";
        setError(msg);
        setRows([]);
      } finally {
        setLoading(false);
      }
    },
    [fetcher, pagination.page, pagination.page_size, filters, sortKey],
  );

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pagination.page, pagination.page_size, filters, sortKey]);

  function updateFilters(patch: Filters): void {
    setFilters((prev) => ({ ...prev, ...patch }));
    setPagination((prev) => ({ ...prev, page: 1 }));
  }

  function resetAllFilters(): void {
    setFilters({ ...defaultFilters, ...initialFilters });
    setSorts(initialSort && initialSort.sort_by ? [initialSort] : []);
    setPagination((prev) => ({ ...prev, page: 1 }));
  }

  function handleTableChange(
    p: { current?: number; pageSize?: number },
    _tableFilters?: Record<string, (string | number | boolean)[] | null>,
    sorter?: unknown,
  ): void {
    setPagination((prev) => ({
      ...prev,
      page: p.current ?? prev.page,
      page_size: p.pageSize ?? prev.page_size,
    }));
    const next = normalizeSorter(sorter);
    if (next !== null) {
      setSorts(next);
    }
  }

  const sort: SortState = useMemo(
    () => sorts[0] || { sort_by: null, sort_order: null },
    [sorts],
  );

  return {
    rows,
    loading,
    error,
    pagination,
    filters,
    sort,
    sorts,
    updateFilters,
    resetAllFilters,
    handleTableChange,
    loadData,
  };
}

/**
 * Lookup the current sort order for a column, supporting multi-column sort.
 * Returns the Ant Design Table `sortOrder` value (`"ascend"|"descend"|null`).
 */
export function sortOrderFor(
  sorts: SortState[] | SortState | undefined,
  field: string,
): "ascend" | "descend" | null {
  if (!sorts) return null;
  const list = Array.isArray(sorts) ? sorts : [sorts];
  for (const s of list) {
    if (s && s.sort_by === field) {
      return s.sort_order === "asc" ? "ascend" : "descend";
    }
  }
  return null;
}
