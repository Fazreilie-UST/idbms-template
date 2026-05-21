import { useCallback, useEffect, useState } from "react";

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
  sort: SortState;
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

function normalizeSorter(sorter: unknown): SortState | null {
  if (!sorter) return null;
  // Ant returns either an object or an array of objects.
  const s = Array.isArray(sorter) ? sorter[0] : (sorter as {
    field?: string | string[];
    columnKey?: string;
    order?: "ascend" | "descend" | null;
  });
  if (!s) return null;
  const order = s.order;
  if (!order) return { sort_by: null, sort_order: null };
  const field = Array.isArray(s.field) ? s.field.join(".") : (s.field || s.columnKey || null);
  if (!field) return null;
  return {
    sort_by: String(field),
    sort_order: order === "ascend" ? "asc" : "desc",
  };
}

/**
 * Generic server-side paginated/filtered/sorted table hook.
 *
 * Compatible with backends that return either:
 *   - `{ data, page, page_size, total }` (flat shape), or
 *   - `{ data, pagination: { page, page_size, total } }` (nested shape).
 *
 * Sorting is wired through Ant Design Table's `onChange(pagination, _, sorter)`
 * callback — the sorter's column key/field maps to `sort_by` and the order to
 * `sort_order` (`asc`/`desc`). For columns to opt-in to server-side sorting,
 * set `sorter: true` (or `{ multiple: n }`) on the column definition.
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
  const [filters, setFilters] = useState<Filters>({ ...defaultFilters, ...initialFilters });
  const [sort, setSort] = useState<SortState>(
    initialSort || { sort_by: null, sort_order: null },
  );

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
        if (sort.sort_by) {
          params.sort_by = sort.sort_by;
          params.sort_order = sort.sort_order || "asc";
        }
        const result = await fetcher(params);

        const page = result.pagination?.page ?? result.page ?? Number(params.page);
        const pageSize =
          result.pagination?.page_size ?? result.page_size ?? Number(params.page_size);
        const total = result.pagination?.total ?? result.total ?? 0;

        setRows(result.data ?? []);
        setPagination((prev) => ({ ...prev, page, page_size: pageSize, total }));
      } catch (err) {
        const msg =
          err instanceof Error ? err.message : "Failed to load data";
        setError(msg);
        setRows([]);
      } finally {
        setLoading(false);
      }
    },
    [fetcher, pagination.page, pagination.page_size, filters, sort.sort_by, sort.sort_order],
  );

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pagination.page, pagination.page_size, filters, sort.sort_by, sort.sort_order]);

  function updateFilters(patch: Filters): void {
    setFilters((prev) => ({ ...prev, ...patch }));
    setPagination((prev) => ({ ...prev, page: 1 }));
  }

  function resetAllFilters(): void {
    setFilters({ ...defaultFilters, ...initialFilters });
    setSort({ sort_by: null, sort_order: null });
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
    if (next) {
      setSort(next);
    }
  }

  return {
    rows,
    loading,
    error,
    pagination,
    filters,
    sort,
    updateFilters,
    resetAllFilters,
    handleTableChange,
    loadData,
  };
}
