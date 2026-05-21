import { create } from "zustand";

import {
  getBuildPlanCounts,
  streamProcessBuildPlanImport,
} from "@/features/buildplans/services/build_plan_import_service";

/**
 * Global, page-independent store for the build plan import batch run.
 *
 * Why global? The processing loop is long-running (many seconds per file) and
 * the user may navigate away from the import page mid-batch. Keeping the run
 * state in component-local React state would lose the progress bar on unmount
 * and there'd be no way to reattach when the user returned.
 *
 * Lifecycle:
 *   startRun({ ids, files })           -> kick off a background batch
 *   subscribe to `progress`/`processing` -> render the bar from anywhere
 *   `rowOverrides[id]`                  -> partial row patches the import page
 *                                          merges into its server-fetched list
 *   `lastRunCompletedAt`                -> bumped when a run finishes; the
 *                                          import page watches this to refresh
 *                                          the table from the server
 */
export const useBuildPlanImportStore = create((set, get) => ({
  processing: false,
  progress: null,
  // Map of file id -> partial row data ({ status, error_message, ...record }).
  // Used by the BuildPlanImport page to reflect in-flight changes on top of
  // the rows it loaded from the server.
  rowOverrides: {},
  // Files in the most-recently-started batch (so the checklist UI can mirror
  // them even after the user navigates away and comes back).
  activeIds: [],
  lastRunCompletedAt: 0,

  /** Cancel-aware no-op while a run is in flight. */
  isRunning: () => get().processing,

  /**
   * Start (or queue) a background batch run.
   * @param {{ids: number[], files: {id:number, original_filename:string}[]}} args
   * @returns {Promise<void>} resolves when the batch finishes (or fails to start).
   */
  startRun: async ({ ids, files, mode = "process" }) => {
    if (get().processing) return;
    if (!ids?.length) return;

    set({
      processing: true,
      activeIds: ids,
      rowOverrides: {},
      progress: {
        mode,
        totalPlans: 0,
        donePlans: 0,
        files: ids.length,
        fileIndex: 0,
        currentId: null,
        currentName: "Estimating…",
        currentTotal: 0,
        currentDone: 0,
        succeededFiles: 0,
        failedFiles: 0,
        skippedFiles: 0,
        notFoundFiles: 0,
        lastConfig: null,
      },
    });

    const fileNameById = new Map(
      (files || []).map((f) => [f.id, f.original_filename || `#${f.id}`]),
    );
    let succeededFiles = 0;
    let failedFiles = 0;
    let skippedFiles = 0;
    let notFoundFiles = 0;

    // ---- 1. Pre-count.
    let countsResp;
    try {
      countsResp = await getBuildPlanCounts(ids);
    } catch (err) {
      set({ processing: false, progress: null, activeIds: [] });
      throw err;
    }

    const counts = countsResp.counts || {};
    const preSkipped = countsResp.skipped || [];
    const preNotFound = countsResp.not_found || [];
    skippedFiles += preSkipped.length;
    notFoundFiles += preNotFound.length;

    const processableIds = ids.filter(
      (id) => !preSkipped.includes(id) && !preNotFound.includes(id),
    );
    const totalPlans = processableIds.reduce(
      (acc, id) => acc + (counts[id] || 0),
      0,
    );

    set({ activeIds: processableIds });

    if (!processableIds.length) {
      set({
        processing: false,
        progress: null,
        lastRunCompletedAt: Date.now(),
      });
      return;
    }

    set({
      progress: {
        mode,
        totalPlans,
        donePlans: 0,
        files: processableIds.length,
        fileIndex: 0,
        currentId: null,
        currentName: null,
        currentTotal: 0,
        currentDone: 0,
        succeededFiles: 0,
        failedFiles: 0,
        skippedFiles,
        notFoundFiles,
        lastConfig: null,
      },
    });

    let donePlans = 0;

    const patchProgress = (patch) =>
      set((state) => ({
        progress: state.progress ? { ...state.progress, ...patch } : state.progress,
      }));

    const patchRow = (id, patch) =>
      set((state) => ({
        rowOverrides: {
          ...state.rowOverrides,
          [id]: { ...(state.rowOverrides[id] || {}), ...patch },
        },
      }));

    try {
      for (let i = 0; i < processableIds.length; i += 1) {
        const id = processableIds[i];
        const currentName = fileNameById.get(id) || `#${id}`;
        const fileTotal = counts[id] || 0;

        patchRow(id, { status: "processing" });
        patchProgress({
          fileIndex: i + 1,
          currentId: id,
          currentName,
          currentTotal: fileTotal,
          currentDone: 0,
          lastConfig: null,
        });

        let fileFailed = false;
        let finalRecord = null;

        try {
          await streamProcessBuildPlanImport(id, (evt) => {
            if (evt.event === "init") {
              const serverTotal = evt.total || 0;
              if (serverTotal !== fileTotal) {
                const delta = serverTotal - fileTotal;
                set((state) => ({
                  progress: state.progress
                    ? {
                        ...state.progress,
                        totalPlans: state.progress.totalPlans + delta,
                        currentTotal: serverTotal,
                      }
                    : state.progress,
                }));
              }
            } else if (
              evt.event === "plan_done" ||
              evt.event === "plan_skipped"
            ) {
              donePlans += 1;
              set((state) => ({
                progress: state.progress
                  ? {
                      ...state.progress,
                      donePlans,
                      currentDone: evt.processed,
                      lastConfig:
                        evt.event === "plan_done"
                          ? evt.config_number || null
                          : state.progress.lastConfig,
                    }
                  : state.progress,
              }));
            } else if (evt.event === "sheet_skipped") {
              const skipped = evt.columns || 0;
              donePlans += skipped;
              patchProgress({ donePlans, currentDone: evt.processed });
            } else if (evt.event === "complete") {
              finalRecord = evt.record || null;
            } else if (evt.event === "error") {
              fileFailed = true;
              throw new Error(evt.message || "Processing failed");
            }
          });
        } catch (err) {
          fileFailed = true;
          patchRow(id, { status: "failed", error_message: err.message });
        }

        if (finalRecord) {
          patchRow(id, finalRecord);
          if (finalRecord.status === "failed") failedFiles += 1;
          else succeededFiles += 1;
        } else if (fileFailed) {
          failedFiles += 1;
        }

        const expectedAfter = processableIds
          .slice(0, i + 1)
          .reduce((acc, fid) => acc + (counts[fid] || 0), 0);
        if (donePlans < expectedAfter) donePlans = expectedAfter;
        patchProgress({ donePlans, succeededFiles, failedFiles });
      }
    } finally {
      set({
        processing: false,
        progress: null,
        lastRunCompletedAt: Date.now(),
      });
    }
  },

  /** Clear stale row overrides after the page has refreshed from the server. */
  clearOverrides: () => set({ rowOverrides: {}, activeIds: [] }),
}));
