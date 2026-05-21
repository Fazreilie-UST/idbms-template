import { fetchShippings } from "@/features/shipments/services/shipping_service";
import { usePaginatedTable } from "@/shared/hooks/usePaginatedTable";

const DEFAULT_FILTERS = {
  search: "",
  status: "",
};

export function useShippingTable(initialFilters = {}) {
  return usePaginatedTable({
    fetcher: fetchShippings,
    defaultFilters: DEFAULT_FILTERS,
    initialFilters,
  });
}
