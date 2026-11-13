import Papa from 'papaparse';
import { ParsedDataset, DatasetImportError } from '../types';

export interface CsvParseOptions {
  dynamicTyping?: boolean;
  encoding?: string;
  maxPreviewRows?: number;
}

export class CsvParser {
  /**
   * Parses a CSV File object asynchronously using PapaParse with full RFC-4180 compliance
   */
  static async parse(file: File, options: CsvParseOptions = {}): Promise<ParsedDataset> {
    return new Promise((resolve, reject) => {
      const errors: DatasetImportError[] = [];

      Papa.parse(file, {
        header: true,
        dynamicTyping: options.dynamicTyping ?? true,
        skipEmptyLines: 'greedy', // Removes completely blank rows
        transformHeader: (header: string, index: number) => {
          let cleaned = header.trim().replace(/^\uFEFF/, ''); // Strip UTF-8 Byte Order Mark (BOM)
          if (!cleaned) {
            cleaned = `Column_${index + 1}`;
          }
          return cleaned;
        },
        complete: (results) => {
          try {
            // Deduplicate headers if necessary
            const rawHeaders = results.meta.fields || [];
            const sanitizedHeaders: string[] = [];
            const headerCounts: Record<string, number> = {};

            rawHeaders.forEach((h, idx) => {
              const base = h.trim() || `Column_${idx + 1}`;
              if (headerCounts[base] !== undefined) {
                headerCounts[base]++;
                sanitizedHeaders.push(`${base}_${headerCounts[base]}`);
              } else {
                headerCounts[base] = 1;
                sanitizedHeaders.push(base);
              }
            });

            // Map rows and report parsing errors
            if (results.errors && results.errors.length > 0) {
              results.errors.forEach((err) => {
                errors.push({
                  type: 'syntax',
                  message: `${err.message} (Row: ${err.row ?? 'Unknown'})`,
                  row: err.row,
                  code: err.code,
                });
              });
            }

            const rows = (results.data as Record<string, any>[]).map((row, rowIdx) => {
              const mappedRow: Record<string, any> = {};
              sanitizedHeaders.forEach((header, colIdx) => {
                const originalKey = rawHeaders[colIdx] || header;
                let val = row[originalKey];
                // Clean null or undefined
                if (val === undefined || val === null || val === '') {
                  mappedRow[header] = null;
                } else {
                  mappedRow[header] = val;
                }
              });
              return mappedRow;
            });

            const parsed: ParsedDataset = {
              headers: sanitizedHeaders,
              rows,
              rowCount: rows.length,
              columnCount: sanitizedHeaders.length,
              errors,
              fileType: 'csv',
              fileSizeBytes: file.size,
              originalFileName: file.name,
            };

            resolve(parsed);
          } catch (err: any) {
            reject(new Error(`Failed to process parsed CSV data: ${err?.message || err}`));
          }
        },
        error: (error) => {
          reject(new Error(`CSV parsing error: ${error.message}`));
        },
      });
    });
  }

  /**
   * Parses raw CSV string data directly
   */
  static parseString(csvString: string, originalFileName = 'data.csv'): ParsedDataset {
    const errors: DatasetImportError[] = [];

    const results = Papa.parse(csvString, {
      header: true,
      dynamicTyping: true,
      skipEmptyLines: 'greedy',
      transformHeader: (header: string, index: number) => {
        let cleaned = header.trim().replace(/^\uFEFF/, '');
        return cleaned || `Column_${index + 1}`;
      },
    });

    const rawHeaders = results.meta.fields || [];
    const sanitizedHeaders: string[] = [];
    const headerCounts: Record<string, number> = {};

    rawHeaders.forEach((h, idx) => {
      const base = h.trim() || `Column_${idx + 1}`;
      if (headerCounts[base] !== undefined) {
        headerCounts[base]++;
        sanitizedHeaders.push(`${base}_${headerCounts[base]}`);
      } else {
        headerCounts[base] = 1;
        sanitizedHeaders.push(base);
      }
    });

    if (results.errors) {
      results.errors.forEach((err) => {
        errors.push({
          type: 'syntax',
          message: `${err.message} (Row: ${err.row ?? 'Unknown'})`,
          row: err.row,
          code: err.code,
        });
      });
    }

    const rows = (results.data as Record<string, any>[]).map((row) => {
      const mappedRow: Record<string, any> = {};
      sanitizedHeaders.forEach((header, colIdx) => {
        const originalKey = rawHeaders[colIdx] || header;
        const val = row[originalKey];
        mappedRow[header] = val === undefined || val === '' ? null : val;
      });
      return mappedRow;
    });

    return {
      headers: sanitizedHeaders,
      rows,
      rowCount: rows.length,
      columnCount: sanitizedHeaders.length,
      errors,
      fileType: 'csv',
      fileSizeBytes: new Blob([csvString]).size,
      originalFileName,
    };
  }
}

