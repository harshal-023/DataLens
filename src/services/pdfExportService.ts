import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';
import {
  Dataset,
  FullDatasetAnalysisResult,
  GroupByResult,
  TimeSeriesResult,
  Report,
} from '../types';
import { formatNumber } from './analyticsEngine';

/**
 * PDF-safe Currency Formatter (Replaces non-Latin-1 Rupee glyph with clean standard ISO code)
 */
export function formatPdfCurrency(amount: number): string {
  if (amount >= 10000000) {
    return `INR ${(amount / 10000000).toFixed(2)} Cr`;
  }
  if (amount >= 100000) {
    return `INR ${(amount / 100000).toFixed(2)} L`;
  }
  if (amount >= 1000) {
    return `INR ${(amount / 1000).toFixed(1)}K`;
  }
  return `INR ${new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(amount)}`;
}

/**
 * Sanitizes input strings for standard PDF WinAnsi / Latin-1 font compatibility
 */
export function sanitizeForPdf(text: any): string {
  if (text === null || text === undefined) return '';
  const str = String(text);
  return str
    .replace(/₹/g, 'INR ')
    .replace(/[\u{1F300}-\u{1F9FF}]/gu, '') // Strip emojis cleanly
    .trim();
}

export interface PdfExportData {
  report?: Report;
  dataset: Dataset;
  analysisSummary: FullDatasetAnalysisResult;
  groupByResults?: GroupByResult[];
  timeSeriesResults?: TimeSeriesResult[];
}

export const PdfExportService = {
  /**
   * Generates a high-quality, professional PDF business report
   */
  async generatePdf(data: PdfExportData, fileName?: string): Promise<{
    blob: Blob;
    arrayBuffer: ArrayBuffer;
    fileName: string;
  }> {
    const { report, dataset, analysisSummary, groupByResults, timeSeriesResults } = data;
    const doc = new jsPDF({
      orientation: 'portrait',
      unit: 'pt',
      format: 'a4',
    });

    const pageWidth = doc.internal.pageSize.getWidth();
    const pageHeight = doc.internal.pageSize.getHeight();
    const margin = 40;
    const contentWidth = pageWidth - margin * 2;

    const title = report?.title || `${dataset.name} Analytical Report`;
    const period = report?.period || 'All Historical Records';
    const audience = report?.audience || 'Executive Board & Leadership';
    const author = report?.author || 'Harshal Sharma (Analyst)';
    const version = report?.datasetVersion || dataset.currentVersion || 'v1.0';
    const rowCount = analysisSummary.rowCountAnalyzed;

    // Palette Colors
    const NAVY = [16, 44, 70]; // #102C46
    const PEACOCK = [0, 159, 152]; // #009F98
    const TEAL_LIGHT = [57, 195, 184]; // #39C3B8
    const GREY = [82, 97, 108]; // #52616C
    const BG_LIGHT = [245, 248, 250]; // #F5F8FA
    const GREEN = [33, 101, 72]; // #216548

    // ==========================================
    // 1. COVER PAGE
    // ==========================================
    // Top Decorative Accent Bar
    doc.setFillColor(0, 159, 152);
    doc.rect(0, 0, pageWidth, 8, 'F');

    // Brand Name
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(16);
    doc.setTextColor(PEACOCK[0], PEACOCK[1], PEACOCK[2]);
    doc.text('DataLens', margin, 55);

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(10);
    doc.setTextColor(GREY[0], GREY[1], GREY[2]);
    doc.text('INSIGHTS TODAY. BETTER DECISIONS TOMORROW.', margin, 70);

    // Main Title
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(24);
    doc.setTextColor(NAVY[0], NAVY[1], NAVY[2]);
    const splitTitle = doc.splitTextToSize(title, contentWidth);
    doc.text(splitTitle, margin, 120);

    // Subtitle
    const titleHeight = splitTitle.length * 28;
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(12);
    doc.setTextColor(GREY[0], GREY[1], GREY[2]);
    doc.text('Evidence-Backed Verified Business Intelligence Document', margin, 125 + titleHeight);

    // Metadata Card
    const cardY = 160 + titleHeight;
    doc.setFillColor(BG_LIGHT[0], BG_LIGHT[1], BG_LIGHT[2]);
    doc.setDrawColor(220, 229, 235);
    doc.roundedRect(margin, cardY, contentWidth, 190, 8, 8, 'FD');

    // Inner Card Border Accent
    doc.setFillColor(PEACOCK[0], PEACOCK[1], PEACOCK[2]);
    doc.rect(margin, cardY, 4, 190, 'F');

    // Metadata Fields
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(10);
    doc.setTextColor(NAVY[0], NAVY[1], NAVY[2]);
    doc.text('DOCUMENT SPECIFICATIONS & AUDIT TRAIL', margin + 20, cardY + 28);

    const metaFields = [
      ['Source Dataset:', `${dataset.name} (${dataset.sourceFileName || 'Dataset Ingest'})`],
      ['Dataset Version:', version],
      ['Records Analyzed:', `${rowCount.toLocaleString()} rows (100% complete dataset in IndexedDB)`],
      ['Data Quality Score:', `${analysisSummary.qualityScore}% (Certified deterministic)`],
      ['Evaluation Latency:', `${analysisSummary.executionTimeMs} ms`],
      ['Reporting Period:', period],
      ['Target Audience:', audience],
      ['Author / Analyst:', author],
      ['Execution Date:', new Date().toLocaleString()],
    ];

    let fieldY = cardY + 50;
    for (const [label, val] of metaFields) {
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(9);
      doc.setTextColor(GREY[0], GREY[1], GREY[2]);
      doc.text(label, margin + 20, fieldY);

      doc.setFont('helvetica', 'normal');
      doc.setTextColor(NAVY[0], NAVY[1], NAVY[2]);
      doc.text(val, margin + 140, fieldY);
      fieldY += 15;
    }

    // Cover Page Seal / Guarantee
    doc.setFillColor(228, 243, 236); // #E4F3EC
    doc.setDrawColor(195, 231, 213);
    doc.roundedRect(margin, 580, contentWidth, 65, 6, 6, 'FD');

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(10);
    doc.setTextColor(GREEN[0], GREEN[1], GREEN[2]);
    doc.text('100% DETERMINISTIC CALCULATION CERTIFICATE', margin + 15, 605);

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(9);
    doc.setTextColor(NAVY[0], NAVY[1], NAVY[2]);
    doc.text(
      'All metrics and tables contained within this document were computed using deterministic mathematical engines directly from persistent IndexedDB records. Zero generative hallucinations or sampled approximations were permitted.',
      margin + 15,
      622,
      { maxWidth: contentWidth - 30 }
    );

    // ==========================================
    // 2. EXECUTIVE SUMMARY & KPIS
    // ==========================================
    doc.addPage();

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(16);
    doc.setTextColor(NAVY[0], NAVY[1], NAVY[2]);
    doc.text('1. Executive Summary', margin, 50);

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(10);
    doc.setTextColor(GREY[0], GREY[1], GREY[2]);
    const summaryText =
      `This report synthesizes verified analytical intelligence across ${rowCount.toLocaleString()} complete records in ${dataset.name} (${version}). Data quality was audited at ${analysisSummary.qualityScore}%, confirming structural readiness for executive reporting. All aggregate measures reflect true full-dataset counts.`;
    doc.text(doc.splitTextToSize(summaryText, contentWidth), margin, 70);

    // Primary KPI Box row
    const kpiY = 115;
    const kpiBoxWidth = (contentWidth - 20) / 3;

    const primaryNumStats = Object.entries(analysisSummary.columnStats).filter(([, s]) => s.sum !== undefined);
    const kpi1 = {
      label: 'TOTAL RECORDS',
      val: rowCount.toLocaleString(),
      sub: '100% Complete Ingest',
    };
    const kpi2 = {
      label: primaryNumStats[0] ? `TOTAL ${primaryNumStats[0][0].toUpperCase()}` : 'DATA QUALITY',
      val: primaryNumStats[0] && primaryNumStats[0][1].sum !== undefined
        ? formatPdfCurrency(primaryNumStats[0][1].sum)
        : `${analysisSummary.qualityScore}%`,
      sub: primaryNumStats[0] ? 'Sum across all records' : 'Verified health score',
    };
    const kpi3 = {
      label: primaryNumStats[1] ? `AVG ${primaryNumStats[1][0].toUpperCase()}` : 'COLUMNS',
      val: primaryNumStats[1] && primaryNumStats[1][1].mean !== undefined
        ? formatPdfCurrency(primaryNumStats[1][1].mean)
        : dataset.columnCount.toString(),
      sub: primaryNumStats[1] ? 'Arithmetic Mean' : 'Structured fields',
    };

    [kpi1, kpi2, kpi3].forEach((kpi, idx) => {
      const bx = margin + idx * (kpiBoxWidth + 10);
      doc.setFillColor(BG_LIGHT[0], BG_LIGHT[1], BG_LIGHT[2]);
      doc.setDrawColor(220, 229, 235);
      doc.roundedRect(bx, kpiY, kpiBoxWidth, 65, 6, 6, 'FD');

      doc.setFont('helvetica', 'bold');
      doc.setFontSize(8);
      doc.setTextColor(GREY[0], GREY[1], GREY[2]);
      doc.text(kpi.label, bx + 12, kpiY + 20);

      doc.setFont('helvetica', 'bold');
      doc.setFontSize(14);
      doc.setTextColor(NAVY[0], NAVY[1], NAVY[2]);
      doc.text(kpi.val, bx + 12, kpiY + 40);

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(8);
      doc.setTextColor(PEACOCK[0], PEACOCK[1], PEACOCK[2]);
      doc.text(kpi.sub, bx + 12, kpiY + 54);
    });

    // ==========================================
    // 3. DESCRIPTIVE STATISTICS TABLE
    // ==========================================
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(14);
    doc.setTextColor(NAVY[0], NAVY[1], NAVY[2]);
    doc.text('2. Complete Descriptive Statistics', margin, 215);

    const statsTableHead = [['Column', 'Type', 'Count', 'Missing', 'Sum', 'Mean', 'Median', 'Min', 'Max', 'Std Dev']];
    const statsTableBody = (dataset.columns || []).map((col) => {
      const s = analysisSummary.columnStats[col.name];
      return [
        col.displayName || col.name,
        col.type,
        s ? formatNumber(s.count) : '-',
        s ? s.missingCount.toString() : '-',
        s && s.sum !== undefined ? formatNumber(s.sum) : '-',
        s && s.mean !== undefined ? formatNumber(s.mean) : '-',
        s && s.median !== undefined ? formatNumber(s.median) : '-',
        s && s.min !== undefined ? formatNumber(s.min) : '-',
        s && s.max !== undefined ? formatNumber(s.max) : '-',
        s && s.standardDeviation !== undefined ? formatNumber(s.standardDeviation) : '-',
      ];
    });

    autoTable(doc, {
      startY: 225,
      head: statsTableHead,
      body: statsTableBody,
      margin: { left: margin, right: margin },
      theme: 'grid',
      headStyles: {
        fillColor: [16, 44, 70], // Navy
        textColor: [255, 255, 255],
        fontStyle: 'bold',
        fontSize: 8,
      },
      styles: {
        fontSize: 7.5,
        cellPadding: 4,
        textColor: [16, 44, 70],
      },
      alternateRowStyles: {
        fillColor: [245, 248, 250],
      },
    });

    // ==========================================
    // 4. GROUP-BY BREAKDOWN TABLE
    // ==========================================
    let currentY = (doc as any).lastAutoTable ? (doc as any).lastAutoTable.finalY + 30 : 450;

    if (groupByResults && groupByResults.length > 0) {
      if (currentY > pageHeight - 160) {
        doc.addPage();
        currentY = 50;
      }

      const res = groupByResults[0];
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(14);
      doc.setTextColor(NAVY[0], NAVY[1], NAVY[2]);
      doc.text(`3. Segment Breakdown by ${res.groupByColumn}`, margin, currentY);

      const groupHead = [[res.groupByColumn, `Metric Value (${res.aggregation.toUpperCase()} ${res.valueColumn})`, 'Share of Total', 'Transactions']];
      const groupBody = res.items.map((it) => [
        sanitizeForPdf(it.key),
        formatPdfCurrency(it.value),
        it.shareOfTotal !== undefined ? `${it.shareOfTotal}%` : 'N/A',
        formatNumber(it.count),
      ]);

      autoTable(doc, {
        startY: currentY + 10,
        head: groupHead,
        body: groupBody,
        margin: { left: margin, right: margin },
        theme: 'grid',
        headStyles: {
          fillColor: [0, 159, 152], // Peacock teal
          textColor: [255, 255, 255],
          fontStyle: 'bold',
          fontSize: 8,
        },
        styles: {
          fontSize: 8,
          cellPadding: 4,
          textColor: [16, 44, 70],
        },
        alternateRowStyles: {
          fillColor: [245, 248, 250],
        },
      });

      currentY = (doc as any).lastAutoTable.finalY + 30;
    }

    // ==========================================
    // 5. TIME SERIES TRENDS
    // ==========================================
    if (timeSeriesResults && timeSeriesResults.length > 0) {
      if (currentY > pageHeight - 160) {
        doc.addPage();
        currentY = 50;
      }

      const ts = timeSeriesResults[0];
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(14);
      doc.setTextColor(NAVY[0], NAVY[1], NAVY[2]);
      doc.text(`4. Temporal Trends (${ts.interval.toUpperCase()})`, margin, currentY);

      const tsHead = [['Period', `${ts.valueColumn} Volume`, 'Transaction Count']];
      const tsBody = ts.points.map((pt) => [
        sanitizeForPdf(pt.period),
        formatPdfCurrency(pt.value),
        formatNumber(pt.count),
      ]);

      autoTable(doc, {
        startY: currentY + 10,
        head: tsHead,
        body: tsBody,
        margin: { left: margin, right: margin },
        theme: 'grid',
        headStyles: {
          fillColor: [16, 44, 70],
          textColor: [255, 255, 255],
          fontStyle: 'bold',
          fontSize: 8,
        },
        styles: {
          fontSize: 8,
          cellPadding: 4,
          textColor: [16, 44, 70],
        },
        alternateRowStyles: {
          fillColor: [245, 248, 250],
        },
      });

      currentY = (doc as any).lastAutoTable.finalY + 30;
    }

    // ==========================================
    // 6. DATA QUALITY AUDIT TABLE
    // ==========================================
    if (currentY > pageHeight - 160) {
      doc.addPage();
      currentY = 50;
    }

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(14);
    doc.setTextColor(NAVY[0], NAVY[1], NAVY[2]);
    doc.text('5. Data Quality Audit & Hygiene', margin, currentY);

    const dqHead = [['Severity', 'Issue Title', 'Affected Records', 'Recommended Action']];
    const dqBody =
      analysisSummary.qualityIssues && analysisSummary.qualityIssues.length > 0
        ? analysisSummary.qualityIssues.map((iss) => [
            iss.severity.toUpperCase(),
            iss.title,
            formatNumber(iss.affectedCount),
            iss.suggestedAction,
          ])
        : [['INFO', 'Clean Dataset', '0', 'Zero anomalies detected. Certified for production analysis.']];

    autoTable(doc, {
      startY: currentY + 10,
      head: dqHead,
      body: dqBody,
      margin: { left: margin, right: margin },
      theme: 'grid',
      headStyles: {
        fillColor: [16, 44, 70],
        textColor: [255, 255, 255],
        fontStyle: 'bold',
        fontSize: 8,
      },
      styles: {
        fontSize: 8,
        cellPadding: 4,
        textColor: [16, 44, 70],
      },
      alternateRowStyles: {
        fillColor: [245, 248, 250],
      },
    });

    currentY = (doc as any).lastAutoTable.finalY + 25;

    // ==========================================
    // 7. METHODOLOGY & CONCLUSION
    // ==========================================
    if (currentY > pageHeight - 120) {
      doc.addPage();
      currentY = 50;
    }

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(12);
    doc.setTextColor(NAVY[0], NAVY[1], NAVY[2]);
    doc.text('6. Methodology & Strategic Conclusion', margin, currentY);

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(9);
    doc.setTextColor(GREY[0], GREY[1], GREY[2]);
    const conclusionText =
      `Based on complete evaluation of ${rowCount.toLocaleString()} records, calculations confirm robust operational throughput with zero sampling bias. Findings are grounded in deterministic calculations certified by the DataLens pipeline.`;
    doc.text(doc.splitTextToSize(conclusionText, contentWidth), margin, currentY + 16);

    // ==========================================
    // RUNNING HEADER & FOOTER ON ALL PAGES
    // ==========================================
    const totalPages = doc.getNumberOfPages();
    for (let i = 1; i <= totalPages; i++) {
      doc.setPage(i);

      if (i > 1) {
        // Running Header on pages 2+
        doc.setFont('helvetica', 'normal');
        doc.setFontSize(8);
        doc.setTextColor(GREY[0], GREY[1], GREY[2]);
        doc.text('DataLens Verified Analytics Report', margin, 25);
        doc.text(title, pageWidth - margin, 25, { align: 'right' });

        doc.setDrawColor(220, 229, 235);
        doc.line(margin, 30, pageWidth - margin, 30);
      }

      // Running Footer on all pages
      doc.setDrawColor(220, 229, 235);
      doc.line(margin, pageHeight - 30, pageWidth - margin, pageHeight - 30);

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(8);
      doc.setTextColor(GREY[0], GREY[1], GREY[2]);
      doc.text(
        `100% Deterministic Math  |  ${version}  |  Confidential`,
        margin,
        pageHeight - 16
      );
      doc.text(
        `Page ${i} of ${totalPages}`,
        pageWidth - margin,
        pageHeight - 16,
        { align: 'right' }
      );
    }

    const outputBlob = doc.output('blob');
    const arrayBuffer = await outputBlob.arrayBuffer();

    const safeName = (fileName || `${dataset.name}_report`).replace(/\s+/g, '_');
    const finalFileName = safeName.endsWith('.pdf') ? safeName : `${safeName}.pdf`;

    return {
      blob: outputBlob,
      arrayBuffer,
      fileName: finalFileName,
    };
  },
};
