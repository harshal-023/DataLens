/**
 * DataLens CSV Export Service (RFC-4180 Compliant with UTF-8 BOM)
 */

export interface CsvExportOptions {
  fileName?: string;
  headers?: string[];
  includeBom?: boolean;
}

export const CsvExportService = {
  /**
   * Escapes a single cell value according to RFC-4180
   */
  escapeCell(value: any): string {
    if (value === null || value === undefined) {
      return '';
    }

    const str = String(value);

    // If cell contains comma, quote, or newline, escape quotes and wrap in quotes
    if (/[",\r\n]/.test(str)) {
      return `"${str.replace(/"/g, '""')}"`;
    }

    return str;
  },

  /**
   * Generates a CSV string from an array of object records
   */
  generateCsvFromRows(rows: Record<string, any>[], explicitHeaders?: string[]): string {
    if (rows.length === 0) {
      if (explicitHeaders && explicitHeaders.length > 0) {
        return explicitHeaders.map((h) => this.escapeCell(h)).join(',') + '\r\n';
      }
      return '';
    }

    const headers = explicitHeaders && explicitHeaders.length > 0
      ? explicitHeaders
      : Object.keys(rows[0]);

    const headerLine = headers.map((h) => this.escapeCell(h)).join(',');
    const dataLines = rows.map((row) =>
      headers.map((h) => this.escapeCell(row[h])).join(',')
    );

    return [headerLine, ...dataLines].join('\r\n') + '\r\n';
  },

  /**
   * Generates a CSV string from a 2D array of cells (header row + rows)
   */
  generateCsvFromGrid(headers: string[], rows: (string | number | boolean | null | undefined)[][]): string {
    const headerLine = headers.map((h) => this.escapeCell(h)).join(',');
    const dataLines = rows.map((row) =>
      row.map((cell) => this.escapeCell(cell)).join(',')
    );

    return [headerLine, ...dataLines].join('\r\n') + '\r\n';
  },

  /**
   * Creates a downloadable CSV Blob with UTF-8 BOM
   */
  createCsvBlob(csvText: string): Blob {
    // UTF-8 BOM (\uFEFF) ensures Excel and external tools detect UTF-8 characters reliably
    const bom = new Uint8Array([0xef, 0xbb, 0xbf]);
    return new Blob([bom, csvText], { type: 'text/csv;charset=utf-8;' });
  },

  /**
   * Exports an array of records to a CSV file and triggers download
   */
  exportRows(
    rows: Record<string, any>[],
    fileName = 'export.csv',
    explicitHeaders?: string[]
  ): { blob: Blob; fileName: string; rowCount: number } {
    const csvText = this.generateCsvFromRows(rows, explicitHeaders);
    const blob = this.createCsvBlob(csvText);
    return {
      blob,
      fileName: fileName.endsWith('.csv') ? fileName : `${fileName}.csv`,
      rowCount: rows.length,
    };
  },

  /**
   * Exports an analytical table (headers + rows) to CSV
   */
  exportGrid(
    headers: string[],
    rows: (string | number | boolean | null | undefined)[][],
    fileName = 'analytics_export.csv'
  ): { blob: Blob; fileName: string; rowCount: number } {
    const csvText = this.generateCsvFromGrid(headers, rows);
    const blob = this.createCsvBlob(csvText);
    return {
      blob,
      fileName: fileName.endsWith('.csv') ? fileName : `${fileName}.csv`,
      rowCount: rows.length,
    };
  },
};

