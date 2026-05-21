import { fetchBuildRequests } from "@/features/orders/services/build_request_service";
import { usePaginatedTable } from "@/shared/hooks/usePaginatedTable";

const DEFAULT_FILTERS = {
  search: "",
  status: "",
  family: "",
  form_factor: "",
  requestor: "",
  my_orders: false,
  my_plans: false,
};

export function useBuildRequestTable(initialFilters = {}) {
  return usePaginatedTable({
    fetcher: fetchBuildRequests,
    defaultFilters: DEFAULT_FILTERS,
    initialFilters,
  });
}
