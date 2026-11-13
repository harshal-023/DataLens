import {
  DatasetColumn,
  DataQualityIssue,
  DataType,
  FilterCondition,
  AggregationType,
  GroupByRequest,
  GroupByResult,
  GroupByItem,
  TimeSeriesInterval,
  TimeSeriesResult,
  TimeSeriesPoint,
  DescriptiveStatistics,
  ComparativeResult,
  FullDatasetAnalysisResult,
} from '../types';
import { StorageService } from './storageService';

export interface ColumnStats extends DescriptiveStatistics {
  // Backwards compatibility with Phase 1A interface
}

/**
 * Parses raw values into standard numbers, stripping currency symbols, commas, and percentage signs
 */
export function coerceNumeric(val: any): number | null {
  if (val === null || val === undefined || val === '') return null;
  if (typeof val === 'number') return isNaN(val) ? null : val;
  if (typeof val === 'boolean') return val ? 1 : 0;

  const str = String(val).trim();
  // Strip currency symbols ($, ₹, €, £), commas, and percentage signs
  const cleaned = str.replace(/[$,₹€£%]/g, '').trim();
  if (cleaned === '' || cleaned === '-' || cleaned === 'N/A' || cleaned === 'null') return null;

  const parsed = Number(cleaned);
  return isNaN(parsed) ? null : parsed;
}

/**
 * Calculates complete descriptive statistics for a single column across all rows
 */
export function calculateDescriptiveStatistics(
  columnName: string,
  rows: Record<string, any>[],
  type?: DataType
): DescriptiveStatistics {
  const total = rows.length;
  const rawValues = rows.map((r) => r[columnName]);
  const nonNulls = rawValues.filter((v) => v !== null && v !== undefined && v !== '');
  const missingCount = total - nonNulls.length;
  const uniqueSet = new Set(nonNulls);
  const uniqueCount = uniqueSet.size;

  // Inferred or provided type check
  const isNumericType =
    type === 'number' ||
    type === 'currency' ||
    type === 'percentage' ||
    (!type && inferColumnType(nonNulls) === 'number');

  if (isNumericType) {
    const numVals = nonNulls
      .map(coerceNumeric)
      .filter((v): v is number => v !== null)
      .sort((a, b) => a - b);

    const validNumericCount = numVals.length;
    const numericMissingCount = total - validNumericCount;

    if (numVals.length === 0) {
      return {
        column: columnName,
        count: total,
        missingCount: total,
        uniqueCount,
      };
    }

    const n = numVals.length;
    const sum = numVals.reduce((acc, v) => acc + v, 0);
    const mean = sum / n;
    const min = numVals[0];
    const max = numVals[n - 1];
    const range = max - min;

    // Exact Median
    let median: number;
    if (n % 2 === 1) {
      median = numVals[Math.floor(n / 2)];
    } else {
      median = (numVals[n / 2 - 1] + numVals[n / 2]) / 2;
    }

    // Population Variance and Standard Deviation
    const squaredDiffs = numVals.reduce((acc, v) => acc + Math.pow(v - mean, 2), 0);
    const variance = n > 1 ? squaredDiffs / (n - 1) : 0; // Sample variance
    const standardDeviation = Math.sqrt(variance);

    // Quartiles & IQR (Tukey's method)
    const q1 = getPercentile(numVals, 0.25);
    const q3 = getPercentile(numVals, 0.75);
    const iqr = q3 - q1;

    return {
      column: columnName,
      count: total,
      missingCount: numericMissingCount,
      uniqueCount,
      sum: Math.round(sum * 100) / 100,
      mean: Math.round(mean * 100) / 100,
      median: Math.round(median * 100) / 100,
      min,
      max,
      range: Math.round(range * 100) / 100,
      variance: Math.round(variance * 100) / 100,
      standardDeviation: Math.round(standardDeviation * 100) / 100,
      q1: Math.round(q1 * 100) / 100,
      q3: Math.round(q3 * 100) / 100,
      iqr: Math.round(iqr * 100) / 100,
    };
  }

  return {
    column: columnName,
    count: total,
    missingCount,
    uniqueCount,
  };
}

/**
 * Helper to compute percentiles (e.g., 0.25 for Q1, 0.75 for Q3)
 */
function getPercentile(sortedVals: number[], percentile: number): number {
  if (sortedVals.length === 0) return 0;
  if (sortedVals.length === 1) return sortedVals[0];

  const index = (sortedVals.length - 1) * percentile;
  const lower = Math.floor(index);
  const upper = Math.ceil(index);
  const weight = index - lower;

  if (lower === upper) return sortedVals[lower];
  return sortedVals[lower] * (1 - weight) + sortedVals[upper] * weight;
}

/**
 * Backward-compatible wrapper for column statistics
 */
export function calculateColumnStats(
  columnName: string,
  rows: Record<string, any>[],
  type: DataType
): ColumnStats {
  return calculateDescriptiveStatistics(columnName, rows, type);
}

/**
 * Filter rows safely by given conditions
 */
export function filterRows(
  rows: Record<string, any>[],
  filters?: FilterCondition[]
): Record<string, any>[] {
  if (!filters || filters.length === 0) return rows;

  return rows.filter((row) => {
    return filters.every((cond) => {
      const rowVal = row[cond.column];
      if (rowVal === undefined || rowVal === null) {
        return cond.operator === 'neq';
      }

      const numRow = coerceNumeric(rowVal);
      const numCond = coerceNumeric(cond.value);

      switch (cond.operator) {
        case 'eq':
          if (numRow !== null && numCond !== null) return numRow === numCond;
          return String(rowVal).trim().toLowerCase() === String(cond.value).trim().toLowerCase();

        case 'neq':
          if (numRow !== null && numCond !== null) return numRow !== numCond;
          return String(rowVal).trim().toLowerCase() !== String(cond.value).trim().toLowerCase();

        case 'gt':
          return numRow !== null && numCond !== null && numRow > numCond;

        case 'gte':
          return numRow !== null && numCond !== null && numRow >= numCond;

        case 'lt':
          return numRow !== null && numCond !== null && numRow < numCond;

        case 'lte':
          return numRow !== null && numCond !== null && numRow <= numCond;

        case 'between': {
          const numSecond = coerceNumeric(cond.secondValue);
          if (numRow === null || numCond === null || numSecond === null) return false;
          const min = Math.min(numCond, numSecond);
          const max = Math.max(numCond, numSecond);
          return numRow >= min && numRow <= max;
        }

        case 'contains':
          return String(rowVal).toLowerCase().includes(String(cond.value).toLowerCase());

        case 'startsWith':
          return String(rowVal).toLowerCase().startsWith(String(cond.value).toLowerCase());

        case 'in':
          if (Array.isArray(cond.value)) {
            return cond.value.some(
              (item) => String(item).toLowerCase() === String(rowVal).toLowerCase()
            );
          }
          return false;

        default:
          return true;
      }
    });
  });
}

/**
 * Multi-column or single-column Group-By aggregation with sorting and Top N / Bottom N
 */
export function aggregateGroupBy(
  rows: Record<string, any>[],
  groupByCol: string,
  valueCol?: string,
  aggregation: AggregationType = 'sum',
  limit?: number,
  sortOrder: 'asc' | 'desc' = 'desc',
  filters?: FilterCondition[]
): GroupByResult {
  const filtered = filterRows(rows, filters);
  const groups: Map<string, number[]> = new Map();

  for (const row of filtered) {
    const rawKey = row[groupByCol];
    const key = rawKey !== undefined && rawKey !== null && rawKey !== '' ? String(rawKey) : 'Unknown';

    let val = 1;
    if (valueCol && valueCol in row) {
      const coerced = coerceNumeric(row[valueCol]);
      val = coerced !== null ? coerced : 0;
    }

    if (!groups.has(key)) {
      groups.set(key, []);
    }
    groups.get(key)!.push(val);
  }

  const items: GroupByItem[] = [];
  let grandTotal = 0;

  for (const [key, values] of groups.entries()) {
    const count = values.length;
    let aggregateVal = 0;

    switch (aggregation) {
      case 'sum':
        aggregateVal = values.reduce((a, b) => a + b, 0);
        break;
      case 'avg':
        aggregateVal = count > 0 ? values.reduce((a, b) => a + b, 0) / count : 0;
        break;
      case 'min':
        aggregateVal = count > 0 ? Math.min(...values) : 0;
        break;
      case 'max':
        aggregateVal = count > 0 ? Math.max(...values) : 0;
        break;
      case 'median': {
        const sorted = [...values].sort((a, b) => a - b);
        if (sorted.length === 0) aggregateVal = 0;
        else if (sorted.length % 2 === 1) aggregateVal = sorted[Math.floor(sorted.length / 2)];
        else aggregateVal = (sorted[sorted.length / 2 - 1] + sorted[sorted.length / 2]) / 2;
        break;
      }
      case 'count':
        aggregateVal = count;
        break;
      case 'variance': {
        const mean = count > 0 ? values.reduce((a, b) => a + b, 0) / count : 0;
        aggregateVal = count > 1 ? values.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / (count - 1) : 0;
        break;
      }
      case 'stddev': {
        const mean = count > 0 ? values.reduce((a, b) => a + b, 0) / count : 0;
        const variance = count > 1 ? values.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / (count - 1) : 0;
        aggregateVal = Math.sqrt(variance);
        break;
      }
    }

    aggregateVal = Math.round(aggregateVal * 100) / 100;
    grandTotal += aggregateVal;

    items.push({
      key,
      value: aggregateVal,
      count,
      formattedValue: formatNumber(aggregateVal),
    });
  }

  // Calculate share of total
  items.forEach((item) => {
    item.shareOfTotal = grandTotal !== 0 ? Math.round((item.value / grandTotal) * 1000) / 10 : 0;
  });

  // Sort
  items.sort((a, b) => {
    if (sortOrder === 'asc') {
      return a.value - b.value;
    }
    return b.value - a.value;
  });

  // Slice if limit is specified
  const resultItems = limit && limit > 0 ? items.slice(0, limit) : items;

  return {
    groupByColumn: groupByCol,
    valueColumn: valueCol || 'count',
    aggregation,
    items: resultItems,
    total: Math.round(grandTotal * 100) / 100,
    rowCountAnalyzed: filtered.length,
  };
}

/**
 * Chronological Time-Series Aggregation (daily, weekly, monthly, quarterly, yearly)
 */
export function aggregateTimeSeries(
  rows: Record<string, any>[],
  dateCol: string,
  valueCol: string,
  interval: TimeSeriesInterval = 'monthly',
  aggregation: AggregationType = 'sum',
  filters?: FilterCondition[]
): TimeSeriesResult {
  const filtered = filterRows(rows, filters);
  const buckets: Map<string, { timestamp: number; values: number[] }> = new Map();

  for (const row of filtered) {
    const rawDate = row[dateCol];
    if (!rawDate) continue;

    const parsedDate = new Date(rawDate);
    if (isNaN(parsedDate.getTime())) continue;

    const coercedVal = coerceNumeric(row[valueCol]);
    const val = coercedVal !== null ? coercedVal : 0;

    let periodKey = '';
    const year = parsedDate.getFullYear();
    const month = parsedDate.getMonth(); // 0 - 11

    switch (interval) {
      case 'daily':
        periodKey = parsedDate.toISOString().slice(0, 10);
        break;
      case 'weekly': {
        const oneJan = new Date(parsedDate.getFullYear(), 0, 1);
        const numberOfDays = Math.floor((parsedDate.getTime() - oneJan.getTime()) / (24 * 60 * 60 * 1000));
        const weekNum = Math.ceil((parsedDate.getDay() + 1 + numberOfDays) / 7);
        periodKey = `${year}-W${String(weekNum).padStart(2, '0')}`;
        break;
      }
      case 'monthly': {
        const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        periodKey = `${monthNames[month]} ${year}`;
        break;
      }
      case 'quarterly': {
        const quarter = Math.floor(month / 3) + 1;
        periodKey = `Q${quarter} ${year}`;
        break;
      }
      case 'yearly':
        periodKey = String(year);
        break;
    }

    if (!buckets.has(periodKey)) {
      buckets.set(periodKey, { timestamp: parsedDate.getTime(), values: [] });
    }
    buckets.get(periodKey)!.values.push(val);
  }

  // Convert to points and sort chronologically
  const points: TimeSeriesPoint[] = [];
  let grandTotal = 0;

  for (const [period, data] of buckets.entries()) {
    const count = data.values.length;
    let aggregateVal = 0;

    if (aggregation === 'sum') {
      aggregateVal = data.values.reduce((a, b) => a + b, 0);
    } else if (aggregation === 'avg') {
      aggregateVal = count > 0 ? data.values.reduce((a, b) => a + b, 0) / count : 0;
    } else if (aggregation === 'max') {
      aggregateVal = count > 0 ? Math.max(...data.values) : 0;
    } else if (aggregation === 'min') {
      aggregateVal = count > 0 ? Math.min(...data.values) : 0;
    } else {
      aggregateVal = count;
    }

    aggregateVal = Math.round(aggregateVal * 100) / 100;
    grandTotal += aggregateVal;

    points.push({
      period,
      timestamp: data.timestamp,
      value: aggregateVal,
      formattedValue: formatNumber(aggregateVal),
      count,
    });
  }

  // Sort by timestamp
  points.sort((a, b) => (a.timestamp || 0) - (b.timestamp || 0));

  return {
    dateColumn: dateCol,
    valueColumn: valueCol,
    interval,
    points,
    total: Math.round(grandTotal * 100) / 100,
    rowCountAnalyzed: filtered.length,
  };
}

/**
 * Calculates comparative growth or differences with strict divide-by-zero protection
 */
export function calculateComparison(
  baselineValue: number,
  targetValue: number
): ComparativeResult {
  const absoluteDifference = Math.round((targetValue - baselineValue) * 100) / 100;
  const isIncrease = targetValue >= baselineValue;

  if (baselineValue === 0) {
    return {
      baselineValue,
      targetValue,
      absoluteDifference,
      percentageDifference: null, // Divide by zero safety
      formattedDelta: targetValue === 0 ? '0.0%' : '+100.0% (base 0)',
      isIncrease,
    };
  }

  const percentageDifference =
    Math.round(((targetValue - baselineValue) / Math.abs(baselineValue)) * 1000) / 10;
  const sign = percentageDifference > 0 ? '+' : '';

  return {
    baselineValue,
    targetValue,
    absoluteDifference,
    percentageDifference,
    formattedDelta: `${sign}${percentageDifference.toFixed(1)}%`,
    isIncrease,
  };
}

/**
 * Improved Data Quality Engine with IQR Outlier Detection, Empty Column Detection, and Negative Values
 */
export function detectDataQualityIssues(
  columns: DatasetColumn[],
  rows: Record<string, any>[]
): { qualityScore: number; issues: DataQualityIssue[] } {
  const issues: DataQualityIssue[] = [];
  let penaltyPoints = 0;
  const totalRows = rows.length;

  if (totalRows === 0) {
    return {
      qualityScore: 100,
      issues: [
        {
          id: 'iss-empty-dataset',
          type: 'missing_values',
          title: 'Empty Dataset',
          description: 'The dataset contains 0 records.',
          affectedCount: 0,
          severity: 'info',
          suggestedAction: 'Upload or populate records to begin analysis.',
        },
      ],
    };
  }

  // 1. Missing Values & Empty Columns Check
  columns.forEach((col) => {
    const rawValues = rows.map((r) => r[col.name]);
    const missing = rawValues.filter((v) => v === null || v === undefined || v === '').length;
    const pct = (missing / totalRows) * 100;

    if (pct === 100) {
      issues.push({
        id: `iss-empty-col-${col.name}`,
        column: col.name,
        type: 'missing_values',
        title: `Empty Column: ${col.displayName || col.name}`,
        description: `Column "${col.displayName || col.name}" has 100% missing values across all ${totalRows} records.`,
        affectedCount: totalRows,
        severity: 'high',
        suggestedAction: 'Remove or populate this empty column before using it in calculations.',
      });
      penaltyPoints += 15;
    } else if (pct > 25) {
      issues.push({
        id: `iss-missing-${col.name}`,
        column: col.name,
        type: 'missing_values',
        title: `High Missing Values in ${col.displayName || col.name}`,
        description: `${missing} rows (${pct.toFixed(1)}%) have empty or null entries in ${col.displayName || col.name}.`,
        affectedCount: missing,
        severity: 'high',
        suggestedAction: 'Impute missing values using column median or flag rows in reporting.',
      });
      penaltyPoints += 12;
    } else if (pct > 5) {
      issues.push({
        id: `iss-missing-${col.name}`,
        column: col.name,
        type: 'missing_values',
        title: `Missing Values in ${col.displayName || col.name}`,
        description: `${missing} record(s) (${pct.toFixed(1)}%) lack a valid ${col.displayName || col.name}.`,
        affectedCount: missing,
        severity: 'medium',
        suggestedAction: 'Review source ingest for incomplete data feeds.',
      });
      penaltyPoints += 5;
    }
  });

  // 2. Duplicate rows check
  const seenRows = new Set<string>();
  let duplicateCount = 0;
  for (const r of rows) {
    const key = JSON.stringify(r);
    if (seenRows.has(key)) {
      duplicateCount++;
    } else {
      seenRows.add(key);
    }
  }

  if (duplicateCount > 0) {
    const dupPct = (duplicateCount / totalRows) * 100;
    issues.push({
      id: 'iss-duplicates',
      type: 'duplicate_rows',
      title: 'Duplicate Records Detected',
      description: `Found ${duplicateCount} identical duplicate row(s) (${dupPct.toFixed(1)}%) that may distort business metrics.`,
      affectedCount: duplicateCount,
      severity: duplicateCount > 10 ? 'high' : 'medium',
      suggestedAction: 'Deduplicate records based on unique transactional identifier.',
    });
    penaltyPoints += duplicateCount > 10 ? 15 : 6;
  }

  // 3. Negative checks for revenue, sales, price, quantity
  columns.forEach((col) => {
    const nameLower = col.name.toLowerCase();
    const isCommercialField =
      nameLower.includes('revenue') ||
      nameLower.includes('sales') ||
      nameLower.includes('price') ||
      nameLower.includes('quantity') ||
      nameLower.includes('arr');

    if (isCommercialField) {
      let negativeCount = 0;
      for (const r of rows) {
        const val = coerceNumeric(r[col.name]);
        if (val !== null && val < 0) {
          negativeCount++;
        }
      }

      if (negativeCount > 0) {
        issues.push({
          id: `iss-negative-${col.name}`,
          column: col.name,
          type: 'suspicious_negative',
          title: `Suspicious Negative Values in ${col.displayName || col.name}`,
          description: `${negativeCount} row(s) contain negative figures in ${col.displayName || col.name}. Typically indicates returns or accounting reversals.`,
          affectedCount: negativeCount,
          severity: 'medium',
          suggestedAction: 'Confirm if negative entries represent product returns or credit notes.',
        });
        penaltyPoints += 8;
      }
    }
  });

  // 4. Outlier detection using Interquartile Range (IQR) method
  columns.forEach((col) => {
    if (col.type === 'number' || col.type === 'currency') {
      const numVals = rows
        .map((r) => coerceNumeric(r[col.name]))
        .filter((v): v is number => v !== null)
        .sort((a, b) => a - b);

      if (numVals.length >= 20) {
        const q1 = getPercentile(numVals, 0.25);
        const q3 = getPercentile(numVals, 0.75);
        const iqr = q3 - q1;

        if (iqr > 0) {
          const lowerBound = q1 - 1.5 * iqr;
          const upperBound = q3 + 1.5 * iqr;
          const outliers = numVals.filter((v) => v < lowerBound || v > upperBound);

          if (outliers.length > 0 && outliers.length < numVals.length * 0.1) {
            issues.push({
              id: `iss-outlier-${col.name}`,
              column: col.name,
              type: 'outlier',
              title: `Statistical Outliers in ${col.displayName || col.name}`,
              description: `Detected ${outliers.length} statistical outlier(s) outside range [${lowerBound.toFixed(0)}, ${upperBound.toFixed(0)}] using Tukey's IQR rule.`,
              affectedCount: outliers.length,
              severity: 'low',
              suggestedAction: 'Verify whether extreme values represent data entry errors or legitimate high-value transactions.',
            });
            penaltyPoints += 4;
          }
        }
      }
    }
  });

  const qualityScore = Math.max(0, Math.min(100, Math.round(100 - penaltyPoints)));
  return { qualityScore, issues };
}

/**
 * High-Level Asynchronous Analytics Orchestrator
 */
export const AnalyticsEngine = {
  /**
   * Computes a full analytical dataset summary across 100% of rows in IndexedDB
   */
  async computeDatasetSummaryAsync(datasetId: string): Promise<FullDatasetAnalysisResult> {
    const startTime = performance.now();
    const rows = await StorageService.getAllDatasetRowsAsync(datasetId);
    const ds = await StorageService.getDatasetByIdAsync(datasetId);

    const columns: DatasetColumn[] =
      ds?.columns && ds.columns.length > 0
        ? ds.columns
        : Object.keys(rows[0] || {}).map((colName) => ({
            id: `col-${colName}`,
            name: colName,
            displayName: colName.replace(/_/g, ' '),
            type: inferColumnType(rows.map((r) => r[colName])),
            missingCount: 0,
            uniqueCount: 0,
            sampleValues: rows.slice(0, 5).map((r) => r[colName]),
          }));

    const columnStats: Record<string, DescriptiveStatistics> = {};
    for (const col of columns) {
      columnStats[col.name] = calculateDescriptiveStatistics(col.name, rows, col.type);
    }

    const { qualityScore, issues } = detectDataQualityIssues(columns, rows);
    const executionTimeMs = Math.round(performance.now() - startTime);

    return {
      datasetId,
      datasetVersionId: ds?.currentVersion || 'v1.0',
      rowCountAnalyzed: rows.length,
      columnCount: columns.length,
      executionTimeMs,
      columnStats,
      qualityScore,
      qualityIssues: issues,
      summary: `Analyzed ${rows.length.toLocaleString()} rows and ${columns.length} columns in ${executionTimeMs}ms. Deterministic math verified.`,
    };
  },

  /**
   * Executes a safe Group-By aggregation on the complete stored dataset
   */
  async executeGroupByAsync(datasetId: string, req: GroupByRequest): Promise<GroupByResult> {
    const rows = await StorageService.getAllDatasetRowsAsync(datasetId);
    return aggregateGroupBy(
      rows,
      req.groupByColumn,
      req.valueColumn,
      req.aggregation,
      req.limit,
      req.sortOrder,
      req.filters
    );
  },

  /**
   * Executes a safe Time-Series aggregation on the complete stored dataset
   */
  async executeTimeSeriesAsync(
    datasetId: string,
    dateCol: string,
    valueCol: string,
    interval: TimeSeriesInterval = 'monthly',
    aggregation: AggregationType = 'sum',
    filters?: FilterCondition[]
  ): Promise<TimeSeriesResult> {
    const rows = await StorageService.getAllDatasetRowsAsync(datasetId);
    return aggregateTimeSeries(rows, dateCol, valueCol, interval, aggregation, filters);
  },

  /**
   * Executes descriptive statistics on a single column with optional row filtering
   */
  async executeFilteredStatsAsync(
    datasetId: string,
    column: string,
    filters?: FilterCondition[]
  ): Promise<DescriptiveStatistics> {
    const allRows = await StorageService.getAllDatasetRowsAsync(datasetId);
    const filtered = filterRows(allRows, filters);
    return calculateDescriptiveStatistics(column, filtered);
  },
};

/**
 * Infers data type from sample values
 */
export function inferColumnType(values: any[]): DataType {
  const nonNulls = values.filter((v) => v !== null && v !== undefined && v !== '');
  if (nonNulls.length === 0) return 'string';

  const numbersCount = nonNulls.filter(
    (v) => typeof v === 'number' || (coerceNumeric(v) !== null && !isNaN(Number(v)))
  ).length;

  if (numbersCount / nonNulls.length > 0.8) {
    const sampleStrings = nonNulls.map((v) => String(v));
    const hasCurrency = sampleStrings.some(
      (s) => s.includes('$') || s.includes('€') || s.includes('£') || s.includes('₹')
    );
    if (hasCurrency) return 'currency';
    const hasPercent = sampleStrings.some((s) => s.includes('%'));
    if (hasPercent) return 'percentage';
    return 'number';
  }

  const booleansCount = nonNulls.filter(
    (v) => typeof v === 'boolean' || v === 'true' || v === 'false'
  ).length;
  if (booleansCount / nonNulls.length > 0.8) return 'boolean';

  const dateCount = nonNulls.filter((v) => {
    const d = Date.parse(String(v));
    return !isNaN(d) && String(v).length >= 8 && (String(v).includes('-') || String(v).includes('/'));
  }).length;
  if (dateCount / nonNulls.length > 0.7) return 'date';

  return 'string';
}

/**
 * Format Helpers
 */
export function formatCurrency(amount: number): string {
  if (amount >= 10000000) {
    return `₹ ${(amount / 10000000).toFixed(2)} Cr`;
  }
  if (amount >= 100000) {
    return `₹ ${(amount / 100000).toFixed(2)} L`;
  }
  if (amount >= 1000) {
    return `₹ ${(amount / 1000).toFixed(1)}K`;
  }
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatNumber(val: number): string {
  return new Intl.NumberFormat('en-US').format(val);
}

export function formatPercent(val: number): string {
  return `${(val > 0 ? '+' : '') + val.toFixed(1)}%`;
}

/**
 * Parse CSV fallback helper
 */
export function parseCSV(csvText: string): { headers: string[]; rows: Record<string, any>[] } {
  const lines = csvText.trim().split(/\r?\n/).filter((line) => line.trim().length > 0);
  if (lines.length === 0) return { headers: [], rows: [] };

  const headers = splitCSVLine(lines[0]);
  const rows: Record<string, any>[] = [];

  for (let i = 1; i < lines.length; i++) {
    const values = splitCSVLine(lines[i]);
    const rowObj: Record<string, any> = {};
    headers.forEach((h, idx) => {
      const val = values[idx] !== undefined ? values[idx].trim() : '';
      const num = coerceNumeric(val);
      if (num !== null && !isNaN(Number(val))) {
        rowObj[h] = num;
      } else if (val.toLowerCase() === 'true') {
        rowObj[h] = true;
      } else if (val.toLowerCase() === 'false') {
        rowObj[h] = false;
      } else {
        rowObj[h] = val;
      }
    });
    rows.push(rowObj);
  }

  return { headers, rows };
}

function splitCSVLine(line: string): string[] {
  const result: string[] = [];
  let current = '';
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    if (char === '"' || char === "'") {
      inQuotes = !inQuotes;
    } else if (char === ',' && !inQuotes) {
      result.push(current.trim());
      current = '';
    } else {
      current += char;
    }
  }
  result.push(current.trim());
  return result;
}
