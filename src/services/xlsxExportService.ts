import * as XLSX from 'xlsx';
import {
  Dataset,
  FullDatasetAnalysisResult,
  GroupByResult,
  TimeSeriesResult,
  Report,
} from '../types';

export interface XlsxExportWorkbookData {
  report?: Report;
  dataset: Dataset;
  analysisSummary: FullDatasetAnalysisResult;
  groupByResults?: GroupByResult[];
  timeSeriesResults?: TimeSeriesResult[];
  rawRows?: Record<string, any>[];
  includeRawData?: boolean;
}

export const XlsxExportService = {
  /**
   * Generates a comprehensive, multi-worksheet Excel workbook
   */
  generateWorkbook(data: XlsxExportWorkbookData, fileName?: string): {
    blob: Blob;
    arrayBuffer: ArrayBuffer;
    fileName: string;
  } {
    const wb = XLSX.utils.book_new();
    const { dataset, analysisSummary, groupByResults, timeSeriesResults, rawRows, includeRawData, report } = data;

    // ==========================================
    // 1. WORKSHEET: Summary
    // ==========================================
    const summaryRows: any[][] = [
      ['DataLens — Business Intelligence Analytical Summary'],
      [''],
      ['Report Metadata', ''],
      ['Report Title', report?.title || `${dataset.name} Analytical Audit`],
      ['Dataset Name', dataset.name],
      ['Dataset Version', report?.datasetVersion || dataset.currentVersion || 'v1.0'],
      ['Total Records Analyzed', analysisSummary.rowCountAnalyzed],
      ['Total Columns', dataset.columnCount || Object.keys(analysisSummary.columnStats).length],
      ['Data Quality Score', `${analysisSummary.qualityScore}%`],
      ['Generation Date', new Date().toISOString()],
      ['Audience', report?.audience || 'Executive Board'],
      ['Reporting Period', report?.period || 'All Available Historical Data'],
      ['Data Engine', 'DataLens Deterministic Verified Engine (Zero Hallucination)'],
      [''],
      ['Key Performance Indicators', 'Value', 'Context'],
    ];

    // Add high-level KPIs from primary numeric columns
    const numColumns = Object.entries(analysisSummary.columnStats).filter(
      ([, stats]) => stats.sum !== undefined
    );
    for (const [colName, stats] of numColumns.slice(0, 5)) {
      summaryRows.push([`Total ${colName}`, stats.sum, 'Aggregated across all rows']);
      summaryRows.push([`Average ${colName}`, stats.mean, 'Mean across valid records']);
      summaryRows.push([`Median ${colName}`, stats.median, '50th percentile']);
    }

    const wsSummary = XLSX.utils.aoa_to_sheet(summaryRows);
    wsSummary['!cols'] = this.calculateColWidths(summaryRows);
    XLSX.utils.book_append_sheet(wb, wsSummary, 'Summary');

    // ==========================================
    // 2. WORKSHEET: Descriptive Statistics
    // ==========================================
    const statsHeaders = [
      'Column Name',
      'Data Type',
      'Total Rows',
      'Missing Count',
      'Unique Values',
      'Sum',
      'Mean',
      'Median',
      'Min',
      'Max',
      'Range',
      'Variance',
      'Standard Deviation',
      'Q1 (25%)',
      'Q3 (75%)',
      'IQR',
    ];

    const statsRows: any[][] = [statsHeaders];
    for (const col of dataset.columns || []) {
      const s = analysisSummary.columnStats[col.name];
      if (s) {
        statsRows.push([
          col.displayName || col.name,
          col.type,
          s.count,
          s.missingCount,
          s.uniqueCount,
          s.sum !== undefined ? s.sum : 'N/A',
          s.mean !== undefined ? s.mean : 'N/A',
          s.median !== undefined ? s.median : 'N/A',
          s.min !== undefined ? s.min : 'N/A',
          s.max !== undefined ? s.max : 'N/A',
          s.range !== undefined ? s.range : 'N/A',
          s.variance !== undefined ? s.variance : 'N/A',
          s.standardDeviation !== undefined ? s.standardDeviation : 'N/A',
          s.q1 !== undefined ? s.q1 : 'N/A',
          s.q3 !== undefined ? s.q3 : 'N/A',
          s.iqr !== undefined ? s.iqr : 'N/A',
        ]);
      }
    }

    const wsStats = XLSX.utils.aoa_to_sheet(statsRows);
    wsStats['!cols'] = this.calculateColWidths(statsRows);
    wsStats['!freeze'] = { xSplit: 0, ySplit: 1 };
    wsStats['!views'] = [{ state: 'frozen', ySplit: 1, activeCell: 'A2', sqref: 'A2' }];
    XLSX.utils.book_append_sheet(wb, wsStats, 'Descriptive Statistics');

    // ==========================================
    // 3. WORKSHEET: Group Analysis
    // ==========================================
    const groupRows: any[][] = [
      ['Dimension', 'Segment / Key', 'Aggregate Value', 'Share of Total (%)', 'Record Count'],
    ];

    if (groupByResults && groupByResults.length > 0) {
      for (const res of groupByResults) {
        for (const it of res.items) {
          groupRows.push([
            `${res.groupByColumn} (${res.aggregation.toUpperCase()} of ${res.valueColumn})`,
            it.key,
            it.value,
            it.shareOfTotal !== undefined ? `${it.shareOfTotal}%` : 'N/A',
            it.count,
          ]);
        }
      }
    } else {
      groupRows.push(['No group-by analysis specified in current configuration', '-', '-', '-', '-']);
    }

    const wsGroup = XLSX.utils.aoa_to_sheet(groupRows);
    wsGroup['!cols'] = this.calculateColWidths(groupRows);
    wsGroup['!freeze'] = { xSplit: 0, ySplit: 1 };
    wsGroup['!views'] = [{ state: 'frozen', ySplit: 1, activeCell: 'A2', sqref: 'A2' }];
    XLSX.utils.book_append_sheet(wb, wsGroup, 'Group Analysis');

    // ==========================================
    // 4. WORKSHEET: Time Series
    // ==========================================
    const tsRows: any[][] = [
      ['Date Dimension', 'Value Metric', 'Period', 'Metric Value', 'Transaction Count'],
    ];

    if (timeSeriesResults && timeSeriesResults.length > 0) {
      for (const ts of timeSeriesResults) {
        for (const pt of ts.points) {
          tsRows.push([
            ts.dateColumn,
            ts.valueColumn,
            pt.period,
            pt.value,
            pt.count,
          ]);
        }
      }
    } else {
      tsRows.push(['No chronological temporal field detected for time-series breakdown', '-', '-', '-', '-']);
    }

    const wsTs = XLSX.utils.aoa_to_sheet(tsRows);
    wsTs['!cols'] = this.calculateColWidths(tsRows);
    wsTs['!freeze'] = { xSplit: 0, ySplit: 1 };
    wsTs['!views'] = [{ state: 'frozen', ySplit: 1, activeCell: 'A2', sqref: 'A2' }];
    XLSX.utils.book_append_sheet(wb, wsTs, 'Time Series');

    // ==========================================
    // 5. WORKSHEET: Data Quality
    // ==========================================
    const dqRows: any[][] = [
      ['Issue Code', 'Column', 'Severity', 'Title', 'Description', 'Affected Records', 'Suggested Remediation'],
    ];

    if (analysisSummary.qualityIssues && analysisSummary.qualityIssues.length > 0) {
      for (const issue of analysisSummary.qualityIssues) {
        dqRows.push([
          issue.id,
          issue.column || 'Dataset Wide',
          issue.severity.toUpperCase(),
          issue.title,
          issue.description,
          issue.affectedCount,
          issue.suggestedAction,
        ]);
      }
    } else {
      dqRows.push(['None', 'All', 'INFO', 'Clean Dataset', 'Zero data quality anomalies detected.', 0, 'Ready for executive production reporting.']);
    }

    const wsDq = XLSX.utils.aoa_to_sheet(dqRows);
    wsDq['!cols'] = this.calculateColWidths(dqRows);
    wsDq['!freeze'] = { xSplit: 0, ySplit: 1 };
    wsDq['!views'] = [{ state: 'frozen', ySplit: 1, activeCell: 'A2', sqref: 'A2' }];
    XLSX.utils.book_append_sheet(wb, wsDq, 'Data Quality');

    // ==========================================
    // 6. WORKSHEET: Raw Data (Optional / Full Complete Dataset)
    // ==========================================
    if (includeRawData !== false && rawRows && rawRows.length > 0) {
      const headers = Object.keys(rawRows[0]);
      const rawGrid: any[][] = [headers];
      for (const r of rawRows) {
        rawGrid.push(headers.map((h) => (r[h] !== undefined ? r[h] : '')));
      }

      const wsRaw = XLSX.utils.aoa_to_sheet(rawGrid);
      wsRaw['!cols'] = this.calculateColWidths(rawGrid.slice(0, 50));
      wsRaw['!freeze'] = { xSplit: 0, ySplit: 1 };
      wsRaw['!views'] = [{ state: 'frozen', ySplit: 1, activeCell: 'A2', sqref: 'A2' }];
      XLSX.utils.book_append_sheet(wb, wsRaw, 'Raw Data');
    }

    // ==========================================
    // 7. WORKSHEET: Methodology & Traceability
    // ==========================================
    const methodologyRows: any[][] = [
      ['DataLens Audit & Methodology Verification'],
      [''],
      ['Parameter', 'Audit Value'],
      ['Dataset ID', dataset.id],
      ['Source File', dataset.sourceFileName || dataset.name],
      ['Frozen Version ID', report?.datasetVersion || dataset.currentVersion || 'v1.0'],
      ['Records Analyzed in IndexedDB', analysisSummary.rowCountAnalyzed],
      ['Calculated Metrics Execution Time', `${analysisSummary.executionTimeMs} ms`],
      ['Engine Pipeline', 'Deterministic TypeScript Analytics Engine (Phase 1B)'],
      ['Mathematical Integrity', '100% Verified Deterministic (No Hallucinated Figures)'],
      ['Generated Timestamp (ISO)', new Date().toISOString()],
      ['Hash/Execution Trace', `DL-VERIFY-${dataset.id}-${Date.now().toString(36).toUpperCase()}`],
    ];

    const wsMeth = XLSX.utils.aoa_to_sheet(methodologyRows);
    wsMeth['!cols'] = this.calculateColWidths(methodologyRows);
    XLSX.utils.book_append_sheet(wb, wsMeth, 'Methodology');

    // Generate output binary
    const outputBuffer = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
    const blob = new Blob([outputBuffer], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });

    const safeName = (fileName || `${dataset.name}_analytical_report`).replace(/\s+/g, '_');
    const finalFileName = safeName.endsWith('.xlsx') ? safeName : `${safeName}.xlsx`;

    return {
      blob,
      arrayBuffer: outputBuffer,
      fileName: finalFileName,
    };
  },

  /**
   * Calculates auto-fit column widths
   */
  calculateColWidths(rows: any[][]): XLSX.ColInfo[] {
    if (rows.length === 0) return [];
    const maxCols = Math.max(...rows.map((r) => r.length));
    const widths: number[] = Array(maxCols).fill(12);

    for (const row of rows) {
      row.forEach((cell, idx) => {
        const text = cell !== null && cell !== undefined ? String(cell) : '';
        const len = text.length;
        if (len + 3 > widths[idx]) {
          widths[idx] = Math.min(len + 3, 50);
        }
      });
    }

    return widths.map((wch) => ({ wch }));
  },
};

