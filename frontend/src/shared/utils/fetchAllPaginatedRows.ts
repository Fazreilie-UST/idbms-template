/**
 * Walk a paginated endpoint until all rows are collected.
 *
 * `fetchPageFn(page, pageSize)` must return `{ items, total }`.
 *
 * The first page is fetched serially so we can learn the total row count;
 * remaining pages are fetched in parallel batches (default concurrency 6)
 * to avoid the sequential-waterfall slowdown when exporting large datasets.
 */
export async function fetchAllPaginatedRows<T = unknown>(
  fetchPageFn: (page: number, batchSize: number) => Promise<{ items?: T[]; total?: number | string }>,
  batchSize = 500,
  concurrency = 6,
): Promise<T[]> {
  // Hard cap to prevent runaway loops on misbehaving endpoints.
  const MAX_PAGES = 10_000;

  const firstRes = await fetchPageFn(1, batchSize);
  const firstItems = firstRes?.items ?? [];
  const total = Number(firstRes?.total ?? 0);

  if (firstItems.length === 0) return [];

  const totalPages = total > 0
    ? Math.min(Math.ceil(total / batchSize), MAX_PAGES)
    : MAX_PAGES;

  // Single page or unknown total but exhausted on first call.
  if (totalPages <= 1 || firstItems.length < batchSize) {
    if (total > 0 && firstItems.length >= total) return firstItems;
    if (firstItems.length < batchSize) return firstItems;
  }

  const allRows: T[] = [...firstItems];
  // Allocate slots so completed batches are inserted in stable order.
  const pageResults: T[][] = [];

  let nextPage = 2;
  let stop = false;

  while (!stop && nextPage <= totalPages) {
    const windowStart = nextPage;
    const windowEnd = Math.min(nextPage + concurrency - 1, totalPages);
    const batch: Promise<{ index: number; items: T[] }>[] = [];
    for (let p = windowStart; p <= windowEnd; p += 1) {
      const idx = p - windowStart;
      batch.push(
        fetchPageFn(p, batchSize).then((res) => ({
          index: idx,
          items: res?.items ?? [],
        })),
      );
    }
    const settled = await Promise.all(batch);
    settled.sort((a, b) => a.index - b.index);
    for (const r of settled) {
      pageResults.push(r.items);
      if (r.items.length === 0 || r.items.length < batchSize) {
        stop = true;
      }
    }
    nextPage = windowEnd + 1;
    if (total > 0 && allRows.length + pageResults.reduce((n, arr) => n + arr.length, 0) >= total) {
      stop = true;
    }
  }

  for (const arr of pageResults) allRows.push(...arr);
  return total > 0 ? allRows.slice(0, total) : allRows;
}
