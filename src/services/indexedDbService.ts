import { openDB, DBSchema, IDBPDatabase } from 'idb';
import {
  Dataset,
  DatasetRow,
  DatasetVersion,
  StorageOperationResult,
  Report,
  StoredReportFile,
} from '../types';

export interface DataLensDBSchema extends DBSchema {
  datasets: {
    key: string;
    value: Dataset;
    indexes: {
      by_name: string;
      by_uploadedAt: string;
    };
  };
  datasetRows: {
    key: string;
    value: DatasetRow;
    indexes: {
      by_datasetId: string;
      by_rowIndex: number;
      by_dataset_and_row: [string, number];
    };
  };
  datasetVersions: {
    key: string;
    value: DatasetVersion & { datasetId: string };
    indexes: {
      by_datasetId: string;
    };
  };
  reports: {
    key: string;
    value: Report;
    indexes: {
      by_datasetId: string;
      by_createdAt: string;
    };
  };
  reportFiles: {
    key: string;
    value: StoredReportFile;
    indexes: {
      by_reportId: string;
      by_format: string;
    };
  };
}

const DB_NAME = 'datalens_db';
const DB_VERSION = 2;

let dbPromise: Promise<IDBPDatabase<DataLensDBSchema>> | null = null;

export class IndexedDbService {
  /**
   * Initializes and opens the IndexedDB instance with version management and store indexes
   */
  static getDB(): Promise<IDBPDatabase<DataLensDBSchema>> {
    if (!dbPromise) {
      dbPromise = openDB<DataLensDBSchema>(DB_NAME, DB_VERSION, {
        upgrade(db, oldVersion, newVersion) {
          // 1. Store: datasets (Metadata only, preview rows truncated to 50 for fast listing)
          if (!db.objectStoreNames.contains('datasets')) {
            const datasetStore = db.createObjectStore('datasets', { keyPath: 'id' });
            datasetStore.createIndex('by_name', 'name', { unique: false });
            datasetStore.createIndex('by_uploadedAt', 'uploadedAt', { unique: false });
          }

          // 2. Store: datasetRows (Full tabular records, separate from metadata)
          if (!db.objectStoreNames.contains('datasetRows')) {
            const rowsStore = db.createObjectStore('datasetRows', { keyPath: 'rowId' });
            rowsStore.createIndex('by_datasetId', 'datasetId', { unique: false });
            rowsStore.createIndex('by_rowIndex', 'rowIndex', { unique: false });
            rowsStore.createIndex('by_dataset_and_row', ['datasetId', 'rowIndex'], { unique: true });
          }

          // 3. Store: datasetVersions
          if (!db.objectStoreNames.contains('datasetVersions')) {
            const versionStore = db.createObjectStore('datasetVersions', { keyPath: 'versionId' });
            versionStore.createIndex('by_datasetId', 'datasetId', { unique: false });
          }

          // 4. Store: reports (Phase 1C Reports persistence)
          if (!db.objectStoreNames.contains('reports')) {
            const reportStore = db.createObjectStore('reports', { keyPath: 'id' });
            reportStore.createIndex('by_datasetId', 'datasetId', { unique: false });
            reportStore.createIndex('by_createdAt', 'createdAt', { unique: false });
          }

          // 5. Store: reportFiles (Phase 1C Genuine Export binary blobs and data)
          if (!db.objectStoreNames.contains('reportFiles')) {
            const fileStore = db.createObjectStore('reportFiles', { keyPath: 'id' });
            fileStore.createIndex('by_reportId', 'reportId', { unique: false });
            fileStore.createIndex('by_format', 'format', { unique: false });
          }
        },
        blocked() {
          console.warn('DataLens IndexedDB open request was blocked by an older open connection.');
        },
        blocking() {
          console.warn('DataLens IndexedDB is blocking a newer version request.');
        },
        terminated() {
          console.error('DataLens IndexedDB connection unexpectedly terminated.');
          dbPromise = null;
        },
      });
    }
    return dbPromise;
  }

  /**
   * Saves dataset metadata and full rows atomically within a single transaction
   * Ensures incomplete uploads do not leave dangling records.
   */
  static async saveCompleteDataset(
    dataset: Dataset,
    rows: Record<string, any>[]
  ): Promise<StorageOperationResult<Dataset>> {
    try {
      const db = await this.getDB();
      const tx = db.transaction(['datasets', 'datasetRows', 'datasetVersions'], 'readwrite');

      // 1. Write metadata (with previewRows containing first 50 rows for fast library previews)
      const metadataToSave: Dataset = {
        ...dataset,
        rowCount: rows.length,
        previewRows: rows.slice(0, 50),
      };

      await tx.objectStore('datasets').put(metadataToSave);

      // 2. Write versions if available
      if (dataset.versions && dataset.versions.length > 0) {
        for (const v of dataset.versions) {
          await tx.objectStore('datasetVersions').put({
            ...v,
            datasetId: dataset.id,
          });
        }
      }

      // 3. Write all rows in batch chunks
      const rowsStore = tx.objectStore('datasetRows');
      for (let i = 0; i < rows.length; i++) {
        const rowObj: DatasetRow = {
          rowId: `${dataset.id}_r${i}`,
          datasetId: dataset.id,
          rowIndex: i,
          data: rows[i],
        };
        await rowsStore.put(rowObj);
      }

      await tx.done;

      return {
        success: true,
        data: metadataToSave,
      };
    } catch (err: any) {
      console.error('Failed to save complete dataset to IndexedDB:', err);
      const isQuota =
        err?.name === 'QuotaExceededError' ||
        err?.message?.toLowerCase().includes('quota') ||
        err?.code === 22;

      return {
        success: false,
        error: isQuota
          ? 'Browser storage quota exceeded. Please free up disk space or remove unused datasets.'
          : err?.message || 'Transaction failed while saving dataset.',
        code: isQuota ? 'QUOTA_EXCEEDED' : 'TRANSACTION_ERROR',
      };
    }
  }

  /**
   * Retrieves all dataset metadata entries sorted by uploadedAt descending
   */
  static async getAllDatasets(): Promise<Dataset[]> {
    try {
      const db = await this.getDB();
      const datasets = await db.getAllFromIndex('datasets', 'by_uploadedAt');
      return datasets.reverse(); // Most recent first
    } catch (err) {
      console.error('Failed to retrieve datasets from IndexedDB:', err);
      return [];
    }
  }

  /**
   * Retrieves single dataset metadata by ID
   */
  static async getDatasetById(id: string): Promise<Dataset | undefined> {
    try {
      const db = await this.getDB();
      return await db.get('datasets', id);
    } catch (err) {
      console.error(`Failed to get dataset ${id} from IndexedDB:`, err);
      return undefined;
    }
  }

  /**
   * Retrieves paginated rows for a specific dataset
   */
  static async getDatasetRows(
    datasetId: string,
    offset = 0,
    limit = 50
  ): Promise<{ rows: Record<string, any>[]; total: number }> {
    try {
      const db = await this.getDB();
      const tx = db.transaction('datasetRows', 'readonly');
      const index = tx.store.index('by_datasetId');

      // Get total count of rows for this dataset
      const total = await index.count(IDBKeyRange.only(datasetId));

      if (total === 0) {
        return { rows: [], total: 0 };
      }

      // Cursor-based pagination for high performance with 10k+ rows
      const rows: Record<string, any>[] = [];
      let cursor = await index.openCursor(IDBKeyRange.only(datasetId));
      let advanced = false;

      if (offset > 0 && cursor) {
        // Advance cursor to offset
        await cursor.advance(offset);
        advanced = true;
      }

      while (cursor && rows.length < limit) {
        rows.push(cursor.value.data);
        cursor = await cursor.continue();
      }

      return { rows, total };
    } catch (err) {
      console.error(`Failed to get rows for dataset ${datasetId}:`, err);
      return { rows: [], total: 0 };
    }
  }

  /**
   * Retrieves all rows for analytics processing
   */
  static async getAllDatasetRows(datasetId: string): Promise<Record<string, any>[]> {
    try {
      const db = await this.getDB();
      const allRows = await db.getAllFromIndex('datasetRows', 'by_datasetId', datasetId);
      return allRows.map((r) => r.data);
    } catch (err) {
      console.error(`Failed to get all rows for ${datasetId}:`, err);
      return [];
    }
  }

  /**
   * Deletes dataset metadata, associated versions, and all data rows in a single transaction
   */
  static async deleteDataset(datasetId: string): Promise<StorageOperationResult> {
    try {
      const db = await this.getDB();
      const tx = db.transaction(['datasets', 'datasetRows', 'datasetVersions'], 'readwrite');

      // 1. Delete metadata
      await tx.objectStore('datasets').delete(datasetId);

      // 2. Delete all rows matching datasetId
      const rowsIndex = tx.objectStore('datasetRows').index('by_datasetId');
      let rowCursor = await rowsIndex.openCursor(IDBKeyRange.only(datasetId));
      while (rowCursor) {
        await rowCursor.delete();
        rowCursor = await rowCursor.continue();
      }

      // 3. Delete versions
      const versionsIndex = tx.objectStore('datasetVersions').index('by_datasetId');
      let verCursor = await versionsIndex.openCursor(IDBKeyRange.only(datasetId));
      while (verCursor) {
        await verCursor.delete();
        verCursor = await verCursor.continue();
      }

      await tx.done;

      return { success: true };
    } catch (err: any) {
      console.error(`Failed to delete dataset ${datasetId}:`, err);
      return {
        success: false,
        error: err?.message || 'Failed to delete dataset.',
        code: 'TRANSACTION_ERROR',
      };
    }
  }

  /**
   * Updates existing dataset metadata
   */
  static async updateDataset(dataset: Dataset): Promise<StorageOperationResult> {
    try {
      const db = await this.getDB();
      await db.put('datasets', dataset);
      return { success: true };
    } catch (err: any) {
      return {
        success: false,
        error: err?.message || 'Failed to update dataset metadata.',
      };
    }
  }

  /**
   * Clears the entire database (for reset/testing)
   */
  static async clearAll(): Promise<void> {
    const db = await this.getDB();
    await db.clear('datasets');
    await db.clear('datasetRows');
    await db.clear('datasetVersions');
    await db.clear('reports');
    await db.clear('reportFiles');
  }

  // ==========================================
  // PHASE 1C: REPORTS & FILE PERSISTENCE
  // ==========================================

  /**
   * Saves a report and optional binary export file atomically to IndexedDB
   */
  static async saveReport(
    report: Report,
    file?: StoredReportFile
  ): Promise<StorageOperationResult<Report>> {
    try {
      const db = await this.getDB();
      const stores: ('reports' | 'reportFiles')[] = file ? ['reports', 'reportFiles'] : ['reports'];
      const tx = db.transaction(stores, 'readwrite');

      await tx.objectStore('reports').put(report);
      if (file) {
        await tx.objectStore('reportFiles').put(file);
      }
      await tx.done;

      return { success: true, data: report };
    } catch (err: any) {
      console.error('Failed to save report to IndexedDB:', err);
      return {
        success: false,
        error: err?.message || 'Failed to save report to IndexedDB.',
      };
    }
  }

  /**
   * Retrieves all reports from IndexedDB
   */
  static async getAllReports(): Promise<Report[]> {
    try {
      const db = await this.getDB();
      return await db.getAll('reports');
    } catch (err) {
      console.warn('Failed to get reports from IndexedDB:', err);
      return [];
    }
  }

  /**
   * Retrieves a single report by ID from IndexedDB
   */
  static async getReportById(id: string): Promise<Report | undefined> {
    try {
      const db = await this.getDB();
      return await db.get('reports', id);
    } catch (err) {
      console.warn(`Failed to get report ${id} from IndexedDB:`, err);
      return undefined;
    }
  }

  /**
   * Retrieves a stored export file (binary blob/data) for a report
   */
  static async getReportFile(reportId: string): Promise<StoredReportFile | undefined> {
    try {
      const db = await this.getDB();
      // First try key lookup
      const direct = await db.get('reportFiles', reportId);
      if (direct) return direct;

      // Or search index by_reportId
      const index = db.transaction('reportFiles', 'readonly').objectStore('reportFiles').index('by_reportId');
      return await index.get(reportId);
    } catch (err) {
      console.warn(`Failed to get report file for ${reportId} from IndexedDB:`, err);
      return undefined;
    }
  }

  /**
   * Deletes a report and its associated export file from IndexedDB
   */
  static async deleteReport(id: string): Promise<StorageOperationResult> {
    try {
      const db = await this.getDB();
      const tx = db.transaction(['reports', 'reportFiles'], 'readwrite');

      await tx.objectStore('reports').delete(id);

      // Delete associated file if present
      const fileStore = tx.objectStore('reportFiles');
      await fileStore.delete(id);

      // Also clean up by index if key was different
      const index = fileStore.index('by_reportId');
      let cursor = await index.openCursor(IDBKeyRange.only(id));
      while (cursor) {
        await cursor.delete();
        cursor = await cursor.continue();
      }

      await tx.done;
      return { success: true };
    } catch (err: any) {
      console.error(`Failed to delete report ${id}:`, err);
      return {
        success: false,
        error: err?.message || 'Failed to delete report from IndexedDB.',
      };
    }
  }
}

