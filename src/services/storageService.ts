import {
  Dataset,
  AnalysisRun,
  PromptExperiment,
  Report,
  ConversationSession,
  User,
  Workspace,
  NotificationItem,
  StorageOperationResult,
  StoredReportFile,
} from '../types';
import {
  currentUser,
  currentWorkspace,
  initialDatasets,
  initialAnalysisRuns,
  initialPromptExperiments,
  initialConversations,
  initialReports,
  notificationsList,
} from './mockData';
import { IndexedDbService } from './indexedDbService';

const KEYS = {
  USER: 'datalens_user',
  WORKSPACE: 'datalens_workspace',
  DATASETS: 'datalens_datasets',
  RUNS: 'datalens_runs',
  EXPERIMENTS: 'datalens_experiments',
  CONVERSATIONS: 'datalens_conversations',
  REPORTS: 'datalens_reports',
  NOTIFICATIONS: 'datalens_notifications',
  IDB_MIGRATED: 'datalens_idb_migrated_v1',
};

function getStored<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch (e) {
    console.warn(`Storage get error for ${key}:`, e);
    return fallback;
  }
}

function setStored<T>(key: string, data: T): void {
  try {
    localStorage.setItem(key, JSON.stringify(data));
  } catch (e) {
    console.warn(`Storage set error for ${key}:`, e);
  }
}

export const StorageService = {
  // ==========================================
  // USER & WORKSPACE
  // ==========================================
  getUser(): User {
    return getStored<User>(KEYS.USER, currentUser);
  },
  setUser(user: User): void {
    setStored(KEYS.USER, user);
  },

  getWorkspace(): Workspace {
    return getStored<Workspace>(KEYS.WORKSPACE, currentWorkspace);
  },
  setWorkspace(ws: Workspace): void {
    setStored(KEYS.WORKSPACE, ws);
  },

  // ==========================================
  // DATASETS (Synchronous Metadata Cache)
  // ==========================================
  getDatasets(): Dataset[] {
    const data = getStored<Dataset[]>(KEYS.DATASETS, initialDatasets);
    if (!data || data.length === 0 || !data.some((d) => d.id === 'ds-sales-2025')) {
      return initialDatasets;
    }
    return data;
  },

  getDatasetById(id: string): Dataset | undefined {
    return this.getDatasets().find((d) => d.id === id);
  },

  saveDataset(dataset: Dataset): void {
    const list = this.getDatasets();
    const idx = list.findIndex((d) => d.id === dataset.id);
    if (idx >= 0) {
      list[idx] = dataset;
    } else {
      list.unshift(dataset);
    }
    setStored(KEYS.DATASETS, list);
    // Also sync metadata to IndexedDB asynchronously
    IndexedDbService.updateDataset(dataset).catch((e) =>
      console.warn('Background sync to IndexedDB failed:', e)
    );
  },

  deleteDataset(id: string): void {
    const list = this.getDatasets().filter((d) => d.id !== id);
    setStored(KEYS.DATASETS, list);
    // Also delete from IndexedDB
    IndexedDbService.deleteDataset(id).catch((e) =>
      console.warn('Background delete from IndexedDB failed:', e)
    );
  },

  // ==========================================
  // PHASE 1A: ASYNCHRONOUS INDEXEDDB INTEGRATION
  // ==========================================

  /**
   * Initializes IndexedDB and safely runs one-time migration from localStorage
   */
  async init(): Promise<void> {
    try {
      await IndexedDbService.getDB();
      await this.migrateLocalStorageToIndexedDB();
    } catch (err) {
      console.error('StorageService init failed:', err);
    }
  },

  /**
   * Migrates existing seed datasets and localStorage entries into IndexedDB
   */
  async migrateLocalStorageToIndexedDB(): Promise<void> {
    try {
      const alreadyMigrated = localStorage.getItem(KEYS.IDB_MIGRATED);
      const existingInIdb = await IndexedDbService.getAllDatasets();

      if (alreadyMigrated && existingInIdb.length > 0) {
        return;
      }

      // Gather datasets to migrate
      const storedDatasets = this.getDatasets();
      for (const ds of storedDatasets) {
        const rows = ds.previewRows && ds.previewRows.length > 0 ? ds.previewRows : [];
        await IndexedDbService.saveCompleteDataset(ds, rows);
      }

      localStorage.setItem(KEYS.IDB_MIGRATED, 'true');
    } catch (err) {
      console.warn('One-time migration to IndexedDB encountered an error:', err);
    }
  },

  /**
   * Asynchronously retrieves all datasets directly from IndexedDB (falling back to cache)
   */
  async getDatasetsAsync(): Promise<Dataset[]> {
    try {
      const fromIdb = await IndexedDbService.getAllDatasets();
      if (fromIdb.length > 0) {
        // Keep localStorage metadata in sync
        setStored(KEYS.DATASETS, fromIdb);
        return fromIdb;
      }
    } catch (e) {
      console.warn('Falling back to localStorage datasets:', e);
    }
    return this.getDatasets();
  },

  /**
   * Asynchronously retrieves a dataset by ID from IndexedDB
   */
  async getDatasetByIdAsync(id: string): Promise<Dataset | undefined> {
    try {
      const ds = await IndexedDbService.getDatasetById(id);
      if (ds) return ds;
    } catch (e) {
      console.warn('Falling back to synchronous dataset lookup:', e);
    }
    return this.getDatasetById(id);
  },

  /**
   * Saves complete dataset metadata and all records to IndexedDB in an atomic transaction
   */
  async saveCompleteDatasetAsync(
    dataset: Dataset,
    rows: Record<string, any>[]
  ): Promise<StorageOperationResult<Dataset>> {
    // 1. Save to IndexedDB
    const result = await IndexedDbService.saveCompleteDataset(dataset, rows);

    if (result.success && result.data) {
      // 2. Update metadata in localStorage cache (previewRows contains first 50 rows)
      this.saveDataset(result.data);
    }

    return result;
  },

  /**
   * Retrieves paginated rows for a dataset from IndexedDB
   */
  async getDatasetRowsAsync(
    datasetId: string,
    offset = 0,
    limit = 50
  ): Promise<{ rows: Record<string, any>[]; total: number }> {
    try {
      const result = await IndexedDbService.getDatasetRows(datasetId, offset, limit);
      if (result.total > 0) {
        return result;
      }
    } catch (e) {
      console.warn('Failed to retrieve rows from IndexedDB:', e);
    }

    // Fallback: Use previewRows from dataset metadata
    const ds = this.getDatasetById(datasetId);
    if (ds && ds.previewRows) {
      return {
        rows: ds.previewRows.slice(offset, offset + limit),
        total: ds.previewRows.length,
      };
    }

    return { rows: [], total: 0 };
  },

  /**
   * Retrieves all rows for full analytical computation (Phase 1B & 2C compatibility)
   */
  async getAllDatasetRowsAsync(datasetId: string, workspaceId?: string): Promise<Record<string, any>[]> {
    // If workspaceId is provided, try retrieving complete dataset from backend first
    if (workspaceId) {
      try {
        const { DatasetApi } = await import('./apiClient');
        const res = await DatasetApi.getRows(workspaceId, datasetId, { page: 1, pageSize: 50000 });
        if (res && res.rows && res.rows.length > 0) {
          return res.rows;
        }
      } catch (e) {
        console.warn('Backend row retrieval failed, falling back to local storage:', e);
      }
    }

    try {
      const rows = await IndexedDbService.getAllDatasetRows(datasetId);
      if (rows.length > 0) {
        return rows;
      }
    } catch (e) {
      console.warn('Failed to retrieve all rows from IndexedDB:', e);
    }

    const ds = this.getDatasetById(datasetId);
    return ds ? ds.previewRows || [] : [];
  },

  // ==========================================
  // PHASE 2C: INDEXEDDB TO BACKEND MIGRATION HELPERS
  // ==========================================
  getMigratedBackendId(localId: string): string | null {
    return localStorage.getItem(`datalens_migrated_${localId}`);
  },

  markDatasetMigrated(localId: string, backendId: string): void {
    localStorage.setItem(`datalens_migrated_${localId}`, backendId);
  },

  async getUnmigratedLocalDatasets(): Promise<Dataset[]> {
    const all = await this.getDatasetsAsync();
    return all.filter((d) => !this.getMigratedBackendId(d.id));
  },

  async migrateLocalDatasetToBackend(
    localId: string,
    workspaceId: string
  ): Promise<{ success: boolean; backendId?: string; error?: string }> {
    try {
      const { DatasetApi } = await import('./apiClient');
      const ds = await this.getDatasetByIdAsync(localId);
      if (!ds) {
        return { success: false, error: 'Local dataset not found' };
      }

      const rows = await this.getAllDatasetRowsAsync(localId);
      if (!rows || rows.length === 0) {
        return { success: false, error: 'Local dataset has no rows to migrate' };
      }

      // Convert rows to CSV blob
      const headers = Object.keys(rows[0]);
      const csvLines = [headers.join(',')];
      for (const r of rows) {
        const rowVals = headers.map((h) => {
          const val = r[h];
          if (val === null || val === undefined) return '';
          const str = String(val);
          return str.includes(',') || str.includes('\n') || str.includes('"')
            ? `"${str.replace(/"/g, '""')}"`
            : str;
        });
        csvLines.push(rowVals.join(','));
      }
      const csvContent = csvLines.join('\n');
      const blob = new Blob([csvContent], { type: 'text/csv' });
      const file = new File([blob], `${ds.name || 'migrated_data'}.csv`, { type: 'text/csv' });

      const formData = new FormData();
      formData.append('file', file);
      formData.append('name', ds.name || 'Migrated Dataset');

      const backendResp = await DatasetApi.upload(workspaceId, formData);
      if (backendResp && backendResp.id) {
        this.markDatasetMigrated(localId, backendResp.id);
        return { success: true, backendId: backendResp.id };
      }
      return { success: false, error: 'Server did not return a dataset ID' };
    } catch (err: any) {
      console.error('Migration error:', err);
      return { success: false, error: err?.message || 'Migration failed' };
    }
  },

  /**
   * Deletes a dataset from both IndexedDB and localStorage
   */
  async deleteDatasetAsync(id: string): Promise<StorageOperationResult> {
    const result = await IndexedDbService.deleteDataset(id);
    this.deleteDataset(id);
    return result;
  },

  // ==========================================
  // ANALYSIS RUNS, EXPERIMENTS, CONVERSATIONS, REPORTS
  // ==========================================
  getAnalysisRuns(): AnalysisRun[] {
    return getStored<AnalysisRun[]>(KEYS.RUNS, initialAnalysisRuns);
  },
  addAnalysisRun(run: AnalysisRun): void {
    const list = this.getAnalysisRuns();
    list.unshift(run);
    setStored(KEYS.RUNS, list);
  },

  getExperiments(): PromptExperiment[] {
    const list = getStored<PromptExperiment[]>(KEYS.EXPERIMENTS, initialPromptExperiments);
    if (!list || list.length === 0 || !list.some((e) => e.id === 'exp-101')) {
      return initialPromptExperiments;
    }
    return list;
  },
  getExperimentById(id: string): PromptExperiment | undefined {
    return this.getExperiments().find((e) => e.id === id);
  },
  saveExperiment(exp: PromptExperiment): void {
    const list = this.getExperiments();
    const idx = list.findIndex((e) => e.id === exp.id);
    if (idx >= 0) {
      list[idx] = exp;
    } else {
      list.unshift(exp);
    }
    setStored(KEYS.EXPERIMENTS, list);
  },

  getConversations(): ConversationSession[] {
    const list = getStored<ConversationSession[]>(KEYS.CONVERSATIONS, initialConversations);
    if (!list || list.length === 0 || !list.some((c) => c.id === 'conv-1')) {
      return initialConversations;
    }
    return list;
  },
  getConversationById(id: string): ConversationSession | undefined {
    return this.getConversations().find((c) => c.id === id);
  },
  saveConversation(conv: ConversationSession): void {
    const list = this.getConversations();
    const idx = list.findIndex((c) => c.id === conv.id);
    if (idx >= 0) {
      list[idx] = conv;
    } else {
      list.unshift(conv);
    }
    setStored(KEYS.CONVERSATIONS, list);
  },

  getReports(): Report[] {
    const list = getStored<Report[]>(KEYS.REPORTS, initialReports);
    if (!list || list.length === 0 || !list.some((r) => r.id === 'rep-sales-2025')) {
      return initialReports;
    }
    return list;
  },
  getReportById(id: string): Report | undefined {
    return this.getReports().find((r) => r.id === id);
  },
  saveReport(rep: Report): void {
    const list = this.getReports();
    const idx = list.findIndex((r) => r.id === rep.id);
    if (idx >= 0) {
      list[idx] = rep;
    } else {
      list.unshift(rep);
    }
    setStored(KEYS.REPORTS, list);
    // Background sync to IndexedDB
    IndexedDbService.saveReport(rep).catch((e) => console.warn('Sync report to IDB failed:', e));
  },
  toggleFavoriteReport(id: string): Report[] {
    const list = this.getReports().map((r) => {
      if (r.id === id) {
        return { ...r, isFavorite: !r.isFavorite };
      }
      return r;
    });
    setStored(KEYS.REPORTS, list);
    const updated = list.find((r) => r.id === id);
    if (updated) {
      IndexedDbService.saveReport(updated).catch((e) => console.warn('Sync fav report to IDB failed:', e));
    }
    return list;
  },
  deleteReport(id: string): void {
    const list = this.getReports().filter((r) => r.id !== id);
    setStored(KEYS.REPORTS, list);
    IndexedDbService.deleteReport(id).catch((e) => console.warn('Delete report from IDB failed:', e));
  },

  // ==========================================
  // PHASE 1C: ASYNCHRONOUS REPORTS & EXPORTS
  // ==========================================

  async getReportsAsync(): Promise<Report[]> {
    try {
      const fromIdb = await IndexedDbService.getAllReports();
      if (fromIdb && fromIdb.length > 0) {
        setStored(KEYS.REPORTS, fromIdb);
        return fromIdb;
      }
    } catch (e) {
      console.warn('Falling back to localStorage reports:', e);
    }
    const current = this.getReports();
    // Seed to IndexedDB
    for (const r of current) {
      await IndexedDbService.saveReport(r).catch(() => {});
    }
    return current;
  },

  async getReportByIdAsync(id: string): Promise<Report | undefined> {
    try {
      const fromIdb = await IndexedDbService.getReportById(id);
      if (fromIdb) return fromIdb;
    } catch (e) {
      console.warn('Falling back to sync getReportById:', e);
    }
    return this.getReportById(id);
  },

  async saveReportAsync(report: Report, file?: StoredReportFile): Promise<void> {
    this.saveReport(report);
    await IndexedDbService.saveReport(report, file);
  },

  async deleteReportAsync(id: string): Promise<void> {
    this.deleteReport(id);
    await IndexedDbService.deleteReport(id);
  },

  async getReportFileAsync(reportId: string): Promise<StoredReportFile | undefined> {
    return await IndexedDbService.getReportFile(reportId);
  },

  getNotifications(): NotificationItem[] {
    return getStored<NotificationItem[]>(KEYS.NOTIFICATIONS, notificationsList);
  },
  markNotificationRead(id: string): void {
    const list = this.getNotifications().map((n) => (n.id === id ? { ...n, read: true } : n));
    setStored(KEYS.NOTIFICATIONS, list);
  },

  async resetToDefaultData(): Promise<void> {
    localStorage.clear();
    await IndexedDbService.clearAll();
  },
};

// Initialize StorageService and trigger one-time migration
StorageService.init().catch((e) => console.warn('StorageService auto-init error:', e));
