import { useCallback, useEffect, useState } from "react";

export interface ServerTablePage<TRow> {
  items: TRow[];
  total: number;
}

export type ServerTableFetcher<TRow> = (
  page: number,
  pageSize: number,
  /** Token is kept on the call signature for legacy fetchers; ignored. */
  token: string | null | undefined,
  sortBy: string | null,
  sortOrder: "asc" | "desc" | null,
) => Promise<ServerTablePage<TRow>>;

interface AntdSorter {
  order?: "ascend" | "descend";
  field?: string;
  columnKey?: string;
}

interface AntdPagination {
  current?: number;
  pageSize?: number;
}

export interface ServerTableState<TRow> {
  data: TRow[];
  total: number;
  loading: boolean;
  page: number;
  pageSize: number;
  sortBy: string | null;
  sortOrder: "asc" | "desc" | null;
  handleTableChange: (
    pagination: AntdPagination,
    filters: unknown,
    sorter: AntdSorter | AntdSorter[],
  ) => void;
  reload: (
    nextPage?: number,
    nextPageSize?: number,
    nextSortBy?: string | null,
    nextSortOrder?: "asc" | "desc" | null,
  ) => Promise<void>;
}

export default function useServerTable<TRow = unknown>(
  fetcher: ServerTableFetcher<TRow>,
  initialPageSize = 10,
): ServerTableState<TRow> {
  // Auth token is now stored in an httpOnly cookie; nothing to pull from the
  // store. We still pass `null` so legacy fetcher signatures keep working.
  const token = null;

  const [data, setData] = useState<TRow[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(initialPageSize);

  const [sortBy, setSortBy] = useState<string | null>(null);
  const [sortOrder, setSortOrder] = useState<"asc" | "desc" | null>(null);

  const load = useCallback(
    async (
      nextPage = page,
      nextPageSize = pageSize,
      nextSortBy: string | null = sortBy,
      nextSortOrder: "asc" | "desc" | null = sortOrder,
    ) => {
      try {
        setLoading(true);

        const res = await fetcher(
          nextPage,
          nextPageSize,
          token,
          nextSortBy,
          nextSortOrder,
        );

        setData(res.items ?? []);
        setTotal(res.total ?? 0);
      } finally {
        setLoading(false);
      }
    },
    [fetcher, page, pageSize, sortBy, sortOrder],
  );

  useEffect(() => {
    load(page, pageSize, sortBy, sortOrder);
  }, [load, page, pageSize, sortBy, sortOrder]);

  const handleTableChange: ServerTableState<TRow>["handleTableChange"] = (
    pagination,
    _filters,
    sorter,
  ) => {
    const nextPage = pagination?.current ?? 1;
    const nextPageSize = pagination?.pageSize ?? initialPageSize;

    let resolvedSortBy: string | null = null;
    let resolvedSortOrder: "asc" | "desc" | null = null;

    if (Array.isArray(sorter)) {
      const activeSorter = sorter.find((item) => item?.order);
      if (activeSorter) {
        resolvedSortBy = activeSorter.field ?? activeSorter.columnKey ?? null;
        resolvedSortOrder = activeSorter.order === "ascend" ? "asc" : "desc";
      }
    } else if (sorter?.order) {
      resolvedSortBy = sorter.field ?? sorter.columnKey ?? null;
      resolvedSortOrder = sorter.order === "ascend" ? "asc" : "desc";
    }

    setPage(nextPage);
    setPageSize(nextPageSize);
    setSortBy(resolvedSortBy);
    setSortOrder(resolvedSortOrder);
  };

  const reload: ServerTableState<TRow>["reload"] = async (
    nextPage = page,
    nextPageSize = pageSize,
    nextSortBy = sortBy,
    nextSortOrder = sortOrder,
  ) => {
    await load(nextPage, nextPageSize, nextSortBy, nextSortOrder);
  };

  return {
    data,
    total,
    loading,
    page,
    pageSize,
    sortBy,
    sortOrder,
    handleTableChange,
    reload,
  };
}
