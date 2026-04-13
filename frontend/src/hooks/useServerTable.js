import { useCallback, useEffect, useState } from "react";
import { useAuthStore } from "../store/useAuthStore";

export default function useServerTable(fetcher, initialPageSize = 10) {
  const token = useAuthStore((state) => state.token);

  const [data, setData] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(initialPageSize);

  const [sortBy, setSortBy] = useState(null);
  const [sortOrder, setSortOrder] = useState(null);

  const load = useCallback(
    async (
      nextPage = page,
      nextPageSize = pageSize,
      nextSortBy = sortBy,
      nextSortOrder = sortOrder
    ) => {
      try {
        setLoading(true);

        const res = await fetcher(
          nextPage,
          nextPageSize,
          token,
          nextSortBy,
          nextSortOrder
        );

        setData(res.items || []);
        setTotal(res.total || 0);
      } finally {
        setLoading(false);
      }
    },
    [fetcher, token, page, pageSize, sortBy, sortOrder]
  );

  useEffect(() => {
    load(page, pageSize, sortBy, sortOrder);
  }, [load, page, pageSize, sortBy, sortOrder]);

  const handleTableChange = (pagination, filters, sorter) => {
    const nextPage = pagination?.current || 1;
    const nextPageSize = pagination?.pageSize || initialPageSize;

    let resolvedSortBy = null;
    let resolvedSortOrder = null;

    if (Array.isArray(sorter)) {
      const activeSorter = sorter.find((item) => item?.order);
      if (activeSorter) {
        resolvedSortBy = activeSorter.field || activeSorter.columnKey;
        resolvedSortOrder =
          activeSorter.order === "ascend" ? "asc" : "desc";
      }
    } else if (sorter?.order) {
      resolvedSortBy = sorter.field || sorter.columnKey;
      resolvedSortOrder = sorter.order === "ascend" ? "asc" : "desc";
    }

    setPage(nextPage);
    setPageSize(nextPageSize);
    setSortBy(resolvedSortBy);
    setSortOrder(resolvedSortOrder);
  };

  const reload = async (
    nextPage = page,
    nextPageSize = pageSize,
    nextSortBy = sortBy,
    nextSortOrder = sortOrder
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