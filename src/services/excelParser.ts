import * as XLSX from 'xlsx';
import { ParsedDataset, WorksheetMetadata, DatasetImportError } from '../types';

export interface ExcelWorkbookInfo {
  sheetNames: string[];
  worksheets: WorksheetMetadata[];
  originalFileName: string;
  fileSizeBytes: number;
}

export class ExcelParser {
  /**
   * Reads an Excel workbook binary file and extracts worksheet metadata and structure
   */
  static async readWorkbookInfo(file: File): Promise<{
    workbook: XLSX.WorkBook;
    info: ExcelWorkbookInfo;
  }> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();

      reader.onload = (e) => {
        try {
          const data = new Uint8Array(e.target?.result as ArrayBuffer);
          // Parse binary workbook with dates and cached formula results enabled
          const workbook = XLSX.read(data, {
            type: 'array',
            cellDates: true, // Auto-convert Excel serial numbers into JS Date objects
            cellFormula: true, // Retain formula expressions in cell.f
          });

          if (!workbook.SheetNames || workbook.SheetNames.length === 0) {
            throw new Error('Workbook contains no worksheets.');
          }

          const worksheets: WorksheetMetadata[] = workbook.SheetNames.map((name) => {
            const worksheet = workbook.Sheets[name];
            // Read range to compute dimensions
            const range = XLSX.utils.decode_range(worksheet['!ref'] || 'A1:A1');
            const rowCount = Math.max(0, range.e.r - range.s.r); // Excludes header row
            const columnCount = range.e.c - range.s.c + 1;

            // Generate header preview
            const jsonRows = XLSX.utils.sheet_to_json<Record<string, any>>(worksheet, {
              header: 1,
              defval: null,
              blankrows: false,
            }) as any[][];

            const headers = (jsonRows[0] || []).map((h, i) =>
              String(h || `Column_${i + 1}`).trim()
            );

            // Preview first 5 rows
            const previewRows = XLSX.utils.sheet_to_json<Record<string, any>>(worksheet, {
              defval: null,
              blankrows: false,
            }).slice(0, 5);

            return {
              name,
              rowCount,
              columnCount: headers.length || columnCount,
              headers,
              previewRows,
            };
          });

          const info: ExcelWorkbookInfo = {
            sheetNames: workbook.SheetNames,
            worksheets,
            originalFileName: file.name,
            fileSizeBytes: file.size,
          };

          resolve({ workbook, info });
        } catch (err: any) {
          reject(new Error(`Failed to parse Excel workbook: ${err?.message || 'Invalid or corrupted file.'}`));
        }
      };

      reader.onerror = () => {
        reject(new Error('Failed to read Excel binary file.'));
      };

      reader.readAsArrayBuffer(file);
    });
  }

  /**
   * Parses a specific worksheet from the Excel workbook into a standard ParsedDataset
   *
   * FORMULA NOTE:
   * Values read from Excel cells reflect the cached formula results stored in the workbook (cell.v).
   * Live formula calculation is not re-computed unless evaluated by an active Excel calculation engine.
   */
  static parseWorksheet(
    workbook: XLSX.WorkBook,
    sheetName: string,
    fileMetadata: { name: string; size: number }
  ): ParsedDataset {
    const worksheet = workbook.Sheets[sheetName];
    if (!worksheet) {
      throw new Error(`Worksheet "${sheetName}" not found in workbook.`);
    }

    const errors: DatasetImportError[] = [];

    // 1. Extract raw 2D array to inspect headers
    const rawMatrix = XLSX.utils.sheet_to_json<any[]>(worksheet, {
      header: 1,
      defval: null,
      blankrows: false,
    });

    if (rawMatrix.length === 0) {
      return {
        headers: [],
        rows: [],
        rowCount: 0,
        columnCount: 0,
        errors: [{ type: 'empty', message: `Worksheet "${sheetName}" is empty.` }],
        fileType: fileMetadata.name.toLowerCase().endsWith('.xls') ? 'xls' : 'xlsx',
        fileSizeBytes: fileMetadata.size,
        originalFileName: fileMetadata.name,
        selectedWorksheet: sheetName,
      };
    }

    // 2. Sanitize and deduplicate headers from the first row
    const rawHeaders: string[] = (rawMatrix[0] || []).map((h, idx) => {
      const val = h !== null && h !== undefined ? String(h).trim() : '';
      return val || `Column_${idx + 1}`;
    });

    const sanitizedHeaders: string[] = [];
    const headerCounts: Record<string, number> = {};

    rawHeaders.forEach((h, idx) => {
      const base = h || `Column_${idx + 1}`;
      if (headerCounts[base] !== undefined) {
        headerCounts[base]++;
        sanitizedHeaders.push(`${base}_${headerCounts[base]}`);
      } else {
        headerCounts[base] = 1;
        sanitizedHeaders.push(base);
      }
    });

    // 3. Extract row objects mapping to sanitized headers
    const rawRows = XLSX.utils.sheet_to_json<Record<string, any>>(worksheet, {
      defval: null,
      blankrows: false,
      raw: false, // Formats values according to cell number formats
    });

    const rows = rawRows.map((row) => {
      const cleanRow: Record<string, any> = {};
      sanitizedHeaders.forEach((h, colIdx) => {
        const originalKey = rawHeaders[colIdx] || h;
        let val = row[originalKey];

        // Format Date objects or clean strings
        if (val instanceof Date) {
          cleanRow[h] = val.toISOString().split('T')[0];
        } else if (val === undefined || val === '') {
          cleanRow[h] = null;
        } else {
          // Attempt numeric conversion if applicable
          if (typeof val === 'string' && val.trim() !== '' && !isNaN(Number(val.replace(/[$,]/g, '')))) {
            const cleanNum = Number(val.replace(/[$,]/g, ''));
            cleanRow[h] = isNaN(cleanNum) ? val : cleanNum;
          } else {
            cleanRow[h] = val;
          }
        }
      });
      return cleanRow;
    });

    return {
      headers: sanitizedHeaders,
      rows,
      rowCount: rows.length,
      columnCount: sanitizedHeaders.length,
      errors,
      fileType: fileMetadata.name.toLowerCase().endsWith('.xls') ? 'xls' : 'xlsx',
      fileSizeBytes: fileMetadata.size,
      originalFileName: fileMetadata.name,
      selectedWorksheet: sheetName,
      worksheets: workbook.SheetNames.map((name) => ({
        name,
        rowCount: 0,
        columnCount: 0,
        headers: [],
        previewRows: [],
      })),
    };
  }

  /**
   * Helper to parse an Excel File directly using the first worksheet
   */
  static async parse(file: File, selectedSheet?: string): Promise<ParsedDataset> {
    const { workbook, info } = await this.readWorkbookInfo(file);
    const targetSheet = selectedSheet || info.sheetNames[0];
    const parsed = this.parseWorksheet(workbook, targetSheet, {
      name: file.name,
      size: file.size,
    });
    parsed.worksheets = info.worksheets;
    return parsed;
  }
}

