import { useCallback, useEffect, useState } from "react";
import {
  fetchBuildPlans,
  fetchBuildPlanFilterOptions,
} from "@/features/buildplans/services/build_plan_service";

const DEFAULT_FILTERS = {
  search: "",
  family_code: "",
  form_factor: "",
  status: "",
  config_number: "",
  support_activity: "",
  build_description: "",
  build_notes: "",
  product_code: "",
  mm_number: "",
  ta_number: "",
  pba_number: "",
  as_number: "",
  my_plans: false,
};

const DEFAULT_FILTER_OPTIONS = {
  family_code: [],
  form_factor: [],
  support_activity: [
    "Integration",
    "Milestone",
    "ME DOE",
    "Material DOE",
    "HW DOE",
    "Factory Visit",
  ],
  build_description: [],
  build_notes: [],
  status: ["Plan", "Hold", "Done", "Cancelled", "New"],
};

const DEFAULT_SORTING = [{ field: "id", order: "desc" }];

function serializeSorting(sortArray) {
  const arr = sortArray && sortArray.length > 0 ? sortArray : DEFAULT_SORTING;
  return {
    sort_by: arr.map((s) => s.field).join(","),
    sort_order: arr.map((s) => s.order).join(","),
  };
}

export function useBuildPlanTable(initialFilterOverrides = {}) {
  const [rows, setRows] = useState([]);
  const [filterOptions, setFilterOptions] = useState(DEFAULT_FILTER_OPTIONS);

  const [pagination, setPagination] = useState({
    page: 1,
    page_size: 20,
    total: 0,
  });

  const [filters, setFilters] = useState({ ...DEFAULT_FILTERS, ...initialFilterOverrides });
  const [sorting, setSorting] = useState(DEFAULT_SORTING);

  const [loading, setLoading] = useState(false);

    async function loadFilterOptions() {
        try {
            const result = await fetchBuildPlanFilterOptions();

            setFilterOptions({
            ...DEFAULT_FILTER_OPTIONS,
            family_code: result?.family_code || [],
            form_factor: result?.form_factor || [],
            support_activity: result?.support_activity || DEFAULT_FILTER_OPTIONS.support_activity,
            build_description: result?.build_description || [],
            build_notes: result?.build_notes || [],
            });
        } catch (error) {
            console.error("Failed to load filter options:", error);

            setFilterOptions(DEFAULT_FILTER_OPTIONS);
        }
    }

  const loadData = useCallback(
    async (extra = {}) => {
      setLoading(true);

      try {
        const params = {
          page: pagination.page,
          page_size: pagination.page_size,
          ...filters,
          ...serializeSorting(sorting),
          ...extra,
        };

        const result = await fetchBuildPlans(params);

        setRows(result.data || []);

        setPagination({
          page: result.pagination.page,
          page_size: result.pagination.page_size,
          total: result.pagination.total,
        });
      } catch (error) {
        console.error("Failed to load build plans:", error);
      } finally {
        setLoading(false);
      }
    },
    [pagination.page, pagination.page_size, filters, sorting]
  );

  useEffect(() => {
    loadFilterOptions();
    loadData();
  }, []);

  function updateFilters(nextFilters) {
    const updated = {
      ...filters,
      ...nextFilters,
    };

    setFilters(updated);

    setPagination((prev) => ({
      ...prev,
      page: 1,
    }));

    loadData({
      ...updated,
      page: 1,
    });
  }

  function handleTableChange(nextPagination, tableFilters, sorter) {
    const nextPage = nextPagination.current;
    const nextPageSize = nextPagination.pageSize;

    const sorterArray = Array.isArray(sorter) ? sorter : sorter ? [sorter] : [];
    const activeSorters = sorterArray.filter((s) => s.field && s.order);

    // Ant Design's sorter array reflects click order, but for multi-column
    // sorting we want a deterministic priority based on `sorter.multiple`
    // declared on each column (lower number = higher priority). This ensures
    // e.g. Support Activity (multiple:3) is always primary over Status
    // (multiple:6) regardless of which column the user clicked first.
    const orderedSorters = [...activeSorters].sort((a, b) => {
      const aMul = a?.column?.sorter?.multiple ?? Number.MAX_SAFE_INTEGER;
      const bMul = b?.column?.sorter?.multiple ?? Number.MAX_SAFE_INTEGER;
      return aMul - bMul;
    });

    const nextSorting =
      orderedSorters.length > 0
        ? orderedSorters.map((s) => ({
            field: s.field,
            order: s.order === "ascend" ? "asc" : "desc",
          }))
        : DEFAULT_SORTING;

    setPagination({
      page: nextPage,
      page_size: nextPageSize,
      total: pagination.total,
    });

    setSorting(nextSorting);

    loadData({
      page: nextPage,
      page_size: nextPageSize,
      ...serializeSorting(nextSorting),
    });
  }

    function resetAllFilters() {
        const resetFilters = { ...DEFAULT_FILTERS, ...initialFilterOverrides };
        setFilters(resetFilters);
        setSorting(DEFAULT_SORTING);

        setPagination((prev) => ({
            ...prev,
            page: 1,
        }));

        loadData({
            ...resetFilters,
            ...serializeSorting(DEFAULT_SORTING),
            page: 1,
        });
    }

    return {
        rows,
        loading,
        pagination,
        filters,
        filterOptions,
        sorting,
        loadData,
        loadFilterOptions,
        updateFilters,
        resetAllFilters,
        handleTableChange,
    };
}