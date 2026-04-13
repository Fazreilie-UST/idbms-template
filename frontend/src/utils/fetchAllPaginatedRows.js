export async function fetchAllPaginatedRows(fetchPageFn, batchSize = 500) {
  let page = 1;
  let total = 0;
  const allRows = [];

  while (true) {
    const res = await fetchPageFn(page, batchSize);
    const items = res?.items || [];
    total = Number(res?.total || 0);

    allRows.push(...items);

    if (items.length === 0 || allRows.length >= total) {
      break;
    }

    page += 1;
  }

  return allRows;
}