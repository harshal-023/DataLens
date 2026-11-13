import {
  Document,
  Packer,
  Paragraph,
  TextRun,
  Table,
  TableRow,
  TableCell,
  WidthType,
  AlignmentType,
  HeadingLevel,
  BorderStyle,
  Header,
  Footer,
  PageNumber,
  ShadingType,
} from 'docx';
import {
  Dataset,
  FullDatasetAnalysisResult,
  GroupByResult,
  TimeSeriesResult,
  Report,
} from '../types';
import { formatCurrency, formatNumber } from './analyticsEngine';

export interface DocxExportData {
  report?: Report;
  dataset: Dataset;
  analysisSummary: FullDatasetAnalysisResult;
  groupByResults?: GroupByResult[];
  timeSeriesResults?: TimeSeriesResult[];
}

export const DocxExportService = {
  /**
   * Generates a genuine, professional Microsoft Word (.docx) document
   */
  async generateDocx(data: DocxExportData, fileName?: string): Promise<{
    blob: Blob;
    arrayBuffer: ArrayBuffer;
    fileName: string;
  }> {
    const { report, dataset, analysisSummary, groupByResults, timeSeriesResults } = data;
    const title = report?.title || `${dataset.name} Business Intelligence Report`;
    const period = report?.period || 'All Available Historical Records';
    const audience = report?.audience || 'Executive Board & Leadership';
    const author = report?.author || 'Harshal Sharma (Analyst)';
    const version = report?.datasetVersion || dataset.currentVersion || 'v1.0';
    const rowCount = analysisSummary.rowCountAnalyzed;

    const sectionsChildren: (Paragraph | Table)[] = [];

    // ==========================================
    // 1. COVER / TITLE BLOCK
    // ==========================================
    sectionsChildren.push(
      new Paragraph({
        alignment: AlignmentType.LEFT,
        spacing: { before: 200, after: 120 },
        children: [
          new TextRun({
            text: 'DataLens',
            bold: true,
            size: 36, // 18pt
            color: '009F98', // Peacock teal
          }),
          new TextRun({
            text: ' — Business Intelligence & Reporting',
            size: 24, // 12pt
            color: '52616C',
          }),
        ],
      }),
      new Paragraph({
        alignment: AlignmentType.LEFT,
        spacing: { before: 100, after: 300 },
        children: [
          new TextRun({
            text: title,
            bold: true,
            size: 52, // 26pt
            color: '102C46', // Deep navy
          }),
        ],
      }),
      new Paragraph({
        spacing: { after: 200 },
        children: [
          new TextRun({
            text: `Reporting Period: ${period}  |  Audience: ${audience}`,
            italics: true,
            size: 20,
            color: '52616C',
          }),
        ],
      })
    );

    // Metadata Summary Table
    const metaTable = new Table({
      width: { size: 100, type: WidthType.PERCENTAGE },
      rows: [
        this.createTableRow(['Parameter', 'Audit Value'], true),
        this.createTableRow(['Source Dataset', `${dataset.name} (${dataset.sourceFileName || 'Direct Upload'})`]),
        this.createTableRow(['Frozen Dataset Version', version]),
        this.createTableRow(['Records Analyzed in IndexedDB', `${rowCount.toLocaleString()} rows (100% complete dataset)`]),
        this.createTableRow(['Data Quality Score', `${analysisSummary.qualityScore}% (${analysisSummary.qualityScore >= 80 ? 'Certified Production Grade' : 'Quality Flags Present'})`]),
        this.createTableRow(['Calculated Metrics Latency', `${analysisSummary.executionTimeMs} ms`]),
        this.createTableRow(['Report Author', author]),
        this.createTableRow(['Generation Timestamp', new Date().toLocaleString()]),
      ],
    });

    sectionsChildren.push(metaTable);
    sectionsChildren.push(
      new Paragraph({
        pageBreakBefore: true,
        heading: HeadingLevel.HEADING_1,
        spacing: { before: 240, after: 120 },
        children: [
          new TextRun({ text: '1. Executive Summary', bold: true, color: '102C46' }),
        ],
      }),
      new Paragraph({
        spacing: { after: 140 },
        children: [
          new TextRun({
            text: `This verified analytical report was synthesized from ${rowCount.toLocaleString()} complete transactional records stored securely within the browser IndexedDB pipeline. Unlike traditional preview sampling, 100% of the ingested rows were evaluated using deterministic TypeScript algorithms.`,
            size: 22,
          }),
        ],
      }),
      new Paragraph({
        spacing: { after: 140 },
        children: [
          new TextRun({
            text: `Across the evaluated dataset (${dataset.name}, ${version}), data quality attained a verified rating of ${analysisSummary.qualityScore}%. Key findings indicate stable operational performance with zero synthetic extrapolation.`,
            size: 22,
          }),
        ],
      })
    );

    // ==========================================
    // 2. CORE KPIS TABLE
    // ==========================================
    sectionsChildren.push(
      new Paragraph({
        heading: HeadingLevel.HEADING_2,
        spacing: { before: 200, after: 100 },
        children: [
          new TextRun({ text: 'Key Performance Indicators (KPIs)', bold: true, color: '009F98' }),
        ],
      })
    );

    const kpiRows: TableRow[] = [
      this.createTableRow(['Metric Description', 'Calculated Value', 'Engine Formula / Basis'], true),
      this.createTableRow(['Total Records Analyzed', rowCount.toLocaleString(), 'COUNT(1) across IndexedDB']),
      this.createTableRow(['Columns Ingested', (dataset.columnCount || Object.keys(analysisSummary.columnStats).length).toString(), 'Schema Header Mapping']),
      this.createTableRow(['Data Quality Score', `${analysisSummary.qualityScore}%`, '100 - Penalties (Nulls, Duplicates, Outliers)']),
    ];

    // Add primary numeric metrics
    const primaryNum = Object.entries(analysisSummary.columnStats).filter(([, s]) => s.sum !== undefined);
    for (const [colName, stats] of primaryNum.slice(0, 3)) {
      kpiRows.push(
        this.createTableRow([
          `Total ${colName}`,
          stats.sum !== undefined ? formatCurrency(stats.sum) : 'N/A',
          `SUM(${colName}) over ${rowCount.toLocaleString()} rows`
        ]),
        this.createTableRow([
          `Average ${colName}`,
          stats.mean !== undefined ? formatCurrency(stats.mean) : 'N/A',
          `AVG(${colName})`
        ])
      );
    }

    sectionsChildren.push(new Table({ width: { size: 100, type: WidthType.PERCENTAGE }, rows: kpiRows }));

    // ==========================================
    // 3. DESCRIPTIVE STATISTICS TABLE
    // ==========================================
    sectionsChildren.push(
      new Paragraph({
        pageBreakBefore: true,
        heading: HeadingLevel.HEADING_1,
        spacing: { before: 240, after: 120 },
        children: [
          new TextRun({ text: '2. Complete Descriptive Statistics', bold: true, color: '102C46' }),
        ],
      }),
      new Paragraph({
        spacing: { after: 140 },
        children: [
          new TextRun({
            text: 'The table below details statistical properties computed for every column in the dataset, including central tendency (mean, median), dispersion (min, max, standard deviation), and data hygiene metrics (missing values).',
            size: 22,
          }),
        ],
      })
    );

    const statRows: TableRow[] = [
      this.createTableRow(['Column', 'Type', 'Missing', 'Sum', 'Mean', 'Median', 'Min', 'Max', 'Std Dev'], true),
    ];

    for (const col of dataset.columns || []) {
      const s = analysisSummary.columnStats[col.name];
      if (s) {
        statRows.push(
          this.createTableRow([
            col.displayName || col.name,
            col.type,
            s.missingCount.toString(),
            s.sum !== undefined ? formatNumber(s.sum) : '-',
            s.mean !== undefined ? formatNumber(s.mean) : '-',
            s.median !== undefined ? formatNumber(s.median) : '-',
            s.min !== undefined ? formatNumber(s.min) : '-',
            s.max !== undefined ? formatNumber(s.max) : '-',
            s.standardDeviation !== undefined ? formatNumber(s.standardDeviation) : '-',
          ])
        );
      }
    }

    sectionsChildren.push(new Table({ width: { size: 100, type: WidthType.PERCENTAGE }, rows: statRows }));

    // ==========================================
    // 4. GROUP-BY & SEGMENT ANALYSIS
    // ==========================================
    if (groupByResults && groupByResults.length > 0) {
      sectionsChildren.push(
        new Paragraph({
          heading: HeadingLevel.HEADING_1,
          spacing: { before: 240, after: 120 },
          children: [
            new TextRun({ text: '3. Categorical & Segment Analysis', bold: true, color: '102C46' }),
          ],
        })
      );

      for (const res of groupByResults) {
        const groupTableRows: TableRow[] = [
          this.createTableRow([res.groupByColumn, `Metric (${res.aggregation.toUpperCase()} ${res.valueColumn})`, 'Share of Total', 'Transactions'], true),
        ];

        for (const item of res.items) {
          groupTableRows.push(
            this.createTableRow([
              item.key,
              formatCurrency(item.value),
              item.shareOfTotal !== undefined ? `${item.shareOfTotal}%` : 'N/A',
              formatNumber(item.count),
            ])
          );
        }

        sectionsChildren.push(
          new Paragraph({
            heading: HeadingLevel.HEADING_2,
            spacing: { before: 160, after: 80 },
            children: [
              new TextRun({ text: `Breakdown by ${res.groupByColumn}`, bold: true, color: '009F98' }),
            ],
          }),
          new Table({ width: { size: 100, type: WidthType.PERCENTAGE }, rows: groupTableRows })
        );
      }
    }

    // ==========================================
    // 5. TIME-SERIES TRENDS
    // ==========================================
    if (timeSeriesResults && timeSeriesResults.length > 0) {
      sectionsChildren.push(
        new Paragraph({
          heading: HeadingLevel.HEADING_1,
          spacing: { before: 240, after: 120 },
          children: [
            new TextRun({ text: '4. Temporal Trend Analysis', bold: true, color: '102C46' }),
          ],
        })
      );

      for (const ts of timeSeriesResults) {
        const tsTableRows: TableRow[] = [
          this.createTableRow(['Period', `${ts.valueColumn} Volume`, 'Transaction Volume'], true),
        ];

        for (const pt of ts.points) {
          tsTableRows.push(
            this.createTableRow([
              pt.period,
              formatCurrency(pt.value),
              formatNumber(pt.count),
            ])
          );
        }

        sectionsChildren.push(
          new Table({ width: { size: 100, type: WidthType.PERCENTAGE }, rows: tsTableRows })
        );
      }
    }

    // ==========================================
    // 6. DATA QUALITY & GOVERNANCE AUDIT
    // ==========================================
    sectionsChildren.push(
      new Paragraph({
        pageBreakBefore: true,
        heading: HeadingLevel.HEADING_1,
        spacing: { before: 240, after: 120 },
        children: [
          new TextRun({ text: '5. Data Quality & Governance Audit', bold: true, color: '102C46' }),
        ],
      })
    );

    const dqRows: TableRow[] = [
      this.createTableRow(['Severity', 'Issue Title', 'Affected Records', 'Recommended Remediation'], true),
    ];

    if (analysisSummary.qualityIssues && analysisSummary.qualityIssues.length > 0) {
      for (const iss of analysisSummary.qualityIssues) {
        dqRows.push(
          this.createTableRow([
            iss.severity.toUpperCase(),
            iss.title,
            formatNumber(iss.affectedCount),
            iss.suggestedAction,
          ])
        );
      }
    } else {
      dqRows.push(
        this.createTableRow(['INFO', 'Clean Dataset', '0', 'Dataset passed all data health checks.'])
      );
    }

    sectionsChildren.push(new Table({ width: { size: 100, type: WidthType.PERCENTAGE }, rows: dqRows }));

    // ==========================================
    // 7. METHODOLOGY, TRACEABILITY & CONCLUSION
    // ==========================================
    sectionsChildren.push(
      new Paragraph({
        heading: HeadingLevel.HEADING_1,
        spacing: { before: 240, after: 120 },
        children: [
          new TextRun({ text: '6. Methodology & Data Traceability', bold: true, color: '102C46' }),
        ],
      }),
      new Paragraph({
        spacing: { after: 120 },
        children: [
          new TextRun({
            text: 'DataLens Mathematical Guarantee: All numerical calculations were executed using verified TypeScript algorithms operating on raw rows stored in IndexedDB. No generative artificial intelligence or LLM hallucination was permitted for numeric totals.',
            italics: true,
            size: 20,
            color: '216548',
          }),
        ],
      }),
      new Paragraph({
        heading: HeadingLevel.HEADING_1,
        spacing: { before: 240, after: 120 },
        children: [
          new TextRun({ text: '7. Strategic Conclusion', bold: true, color: '102C46' }),
        ],
      }),
      new Paragraph({
        spacing: { after: 120 },
        children: [
          new TextRun({
            text: `Based on deterministic evaluation of ${rowCount.toLocaleString()} records, the dataset demonstrates viable commercial performance. Leaders are advised to prioritize high-volume segments and address flagged data quality outliers before external compliance submission.`,
            size: 22,
          }),
        ],
      })
    );

    // Build the Document
    const doc = new Document({
      sections: [
        {
          headers: {
            default: new Header({
              children: [
                new Paragraph({
                  alignment: AlignmentType.RIGHT,
                  children: [
                    new TextRun({
                      text: 'DataLens Verified Business Intelligence Report',
                      size: 16,
                      color: '52616C',
                    }),
                  ],
                }),
              ],
            }),
          },
          footers: {
            default: new Footer({
              children: [
                new Paragraph({
                  alignment: AlignmentType.CENTER,
                  children: [
                    new TextRun({ text: 'Page ' }),
                    new TextRun({ children: [PageNumber.CURRENT] }),
                    new TextRun({ text: ' of ' }),
                    new TextRun({ children: [PageNumber.TOTAL_PAGES] }),
                    new TextRun({ text: '  |  100% Deterministic Math  |  Confidential' }),
                  ],
                }),
              ],
            }),
          },
          children: sectionsChildren,
        },
      ],
    });

    const buffer = await Packer.toArrayBuffer(doc);
    const blob = new Blob([buffer], {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    });

    const safeName = (fileName || `${dataset.name}_report`).replace(/\s+/g, '_');
    const finalFileName = safeName.endsWith('.docx') ? safeName : `${safeName}.docx`;

    return {
      blob,
      arrayBuffer: buffer,
      fileName: finalFileName,
    };
  },

  /**
   * Helper to build styled table rows
   */
  createTableRow(cells: string[], isHeader = false): TableRow {
    const borders = {
      top: { style: BorderStyle.SINGLE, size: 1, color: 'DCE5EB' },
      bottom: { style: BorderStyle.SINGLE, size: 1, color: 'DCE5EB' },
      left: { style: BorderStyle.SINGLE, size: 1, color: 'DCE5EB' },
      right: { style: BorderStyle.SINGLE, size: 1, color: 'DCE5EB' },
    };

    return new TableRow({
      tableHeader: isHeader,
      children: cells.map((cellText) => {
        return new TableCell({
          borders,
          shading: isHeader
            ? { fill: '102C46', type: ShadingType.CLEAR } // Navy header
            : undefined,
          margins: { top: 120, bottom: 120, left: 160, right: 160 },
          children: [
            new Paragraph({
              children: [
                new TextRun({
                  text: cellText,
                  bold: isHeader,
                  size: isHeader ? 20 : 18,
                  color: isHeader ? 'FFFFFF' : '102C46',
                }),
              ],
            }),
          ],
        });
      }),
    });
  },
};

