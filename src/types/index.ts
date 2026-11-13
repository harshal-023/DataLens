// DataLens Domain Models and Types

export type UserRole = 'Admin' | 'Analyst' | 'Viewer';

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  avatarUrl?: string;
  workspaceId: string;
}

export interface Workspace {
  id: string;
  name: string;
  tier: 'Enterprise' | 'Professional' | 'Starter';
  datasetCount: number;
  reportCount: number;
  storageUsedMb: number;
  storageLimitMb: number;
}

export type DataType = 'string' | 'number' | 'date' | 'boolean' | 'currency' | 'percentage';

export interface DatasetColumn {
  id: string;
  name: string;
  displayName: string;
  type: DataType;
  missingCount: number;
  uniqueCount: number;
  sampleValues: (string | number | boolean | null)[];
  mean?: number;
  min?: number;
  max?: number;
  isKey?: boolean;
}

export type QualityIssueSeverity = 'high' | 'medium' | 'low' | 'info';

export interface DataQualityIssue {
  id: string;
  column?: string;
  type: 'missing_values' | 'duplicate_rows' | 'type_mismatch' | 'outlier' | 'suspicious_negative' | 'format_inconsistency';
  title: string;
  description: string;
  affectedCount: number;
  severity: QualityIssueSeverity;
  suggestedAction: string;
  resolved?: boolean;
}

export interface DatasetVersion {
  versionId: string;
  versionNumber: string;
  createdAt: string;
  createdBy: string;
  changeSummary: string;
  rowCount: number;
  columnCount: number;
}

export interface Dataset {
  id: string;
  name: string;
  description: string;
  sourceFileName: string;
  originalFileName?: string;
  fileType?: 'csv' | 'xlsx' | 'xls';
  fileSizeBytes?: number;
  fileSizeFormatted: string;
  rowCount: number;
  columnCount: number;
  uploadedAt: string;
  updatedAt?: string;
  lastAnalyzedAt: string;
  status: 'ready' | 'analyzing' | 'warning' | 'error';
  currentVersion: string;
  versions: DatasetVersion[];
  columns: DatasetColumn[];
  qualityScore: number; // 0 - 100
  qualityIssues: DataQualityIssue[];
  previewRows: Record<string, any>[];
  tags: string[];
  selectedWorksheet?: string;
  availableWorksheets?: string[];
}

// Phase 1A Data Ingestion & Storage Models
export interface DatasetRow {
  rowId: string;
  datasetId: string;
  rowIndex: number;
  data: Record<string, any>;
}

export interface WorksheetMetadata {
  name: string;
  rowCount: number;
  columnCount: number;
  headers: string[];
  previewRows: Record<string, any>[];
}

export interface DatasetImportError {
  type: 'syntax' | 'header' | 'empty' | 'quota' | 'format' | 'validation';
  message: string;
  row?: number;
  column?: string;
  code?: string;
}

export interface ParsedDataset {
  headers: string[];
  rows: Record<string, any>[];
  rowCount: number;
  columnCount: number;
  errors: DatasetImportError[];
  fileType: 'csv' | 'xlsx' | 'xls';
  fileSizeBytes: number;
  originalFileName: string;
  worksheets?: WorksheetMetadata[];
  selectedWorksheet?: string;
}

export interface DatasetImportResult {
  success: boolean;
  dataset?: Dataset;
  parsedData?: ParsedDataset;
  error?: string;
  errors?: DatasetImportError[];
  warnings?: string[];
  totalRowsImported?: number;
}

export interface DatasetStorageMetadata {
  id: string;
  name: string;
  originalFileName: string;
  fileType: string;
  fileSize: number;
  fileSizeFormatted: string;
  uploadedAt: string;
  updatedAt: string;
  rowCount: number;
  columnCount: number;
  columns: DatasetColumn[];
  dataQualityScore: number;
  selectedWorksheet?: string;
  versionId: string;
  processingStatus: 'ready' | 'analyzing' | 'warning' | 'error';
}

// ==========================================
// PHASE 1B: ANALYTICAL ENGINE TYPED INTERFACES
// ==========================================

export type FilterOperator =
  | 'eq'
  | 'neq'
  | 'gt'
  | 'gte'
  | 'lt'
  | 'lte'
  | 'between'
  | 'contains'
  | 'startsWith'
  | 'in';

export interface FilterCondition {
  column: string;
  operator: FilterOperator;
  value: any;
  secondValue?: any; // For 'between'
}

export type AggregationType =
  | 'sum'
  | 'avg'
  | 'min'
  | 'max'
  | 'median'
  | 'count'
  | 'stddev'
  | 'variance';

export interface GroupByRequest {
  groupByColumn: string;
  valueColumn: string;
  aggregation: AggregationType;
  limit?: number;
  sortOrder?: 'asc' | 'desc';
  filters?: FilterCondition[];
}

export interface GroupByItem {
  key: string;
  value: number;
  formattedValue?: string;
  count: number;
  shareOfTotal?: number;
}

export interface GroupByResult {
  groupByColumn: string;
  valueColumn: string;
  aggregation: AggregationType;
  items: GroupByItem[];
  total: number;
  rowCountAnalyzed: number;
}

export type TimeSeriesInterval = 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'yearly';

export interface TimeSeriesPoint {
  period: string;
  timestamp?: number;
  value: number;
  formattedValue?: string;
  count: number;
}

export interface TimeSeriesResult {
  dateColumn: string;
  valueColumn: string;
  interval: TimeSeriesInterval;
  points: TimeSeriesPoint[];
  total: number;
  rowCountAnalyzed: number;
}

export interface DescriptiveStatistics {
  column: string;
  count: number;
  missingCount: number;
  uniqueCount: number;
  sum?: number;
  mean?: number;
  median?: number;
  min?: number;
  max?: number;
  variance?: number;
  standardDeviation?: number;
  range?: number;
  q1?: number;
  q3?: number;
  iqr?: number;
}

export interface ComparativeResult {
  baselineValue: number;
  targetValue: number;
  absoluteDifference: number;
  percentageDifference: number | null; // null if baseline is 0
  formattedDelta: string;
  isIncrease: boolean;
}

export interface AnalysisEvidenceTrace {
  datasetId: string;
  datasetName: string;
  datasetVersionId: string;
  rowCountAnalyzed: number;
  executionTimeMs: number;
  calculationFormula: string;
  columnsUsed: string[];
  filtersApplied?: FilterCondition[];
  aggregationUsed?: AggregationType | string;
  deterministicVerification: boolean;
}

export interface FullDatasetAnalysisResult {
  datasetId: string;
  datasetVersionId: string;
  rowCountAnalyzed: number;
  columnCount: number;
  executionTimeMs: number;
  columnStats: Record<string, DescriptiveStatistics>;
  qualityScore: number;
  qualityIssues: DataQualityIssue[];
  summary: string;
}

export interface StorageOperationResult<T = void> {
  success: boolean;
  data?: T;
  error?: string;
  code?: 'QUOTA_EXCEEDED' | 'NOT_FOUND' | 'TRANSACTION_ERROR' | 'UNKNOWN';
}

export interface AnalysisRun {
  id: string;
  datasetId: string;
  datasetVersion: string;
  runDate: string;
  triggeredBy: string;
  status: 'completed' | 'failed' | 'running';
  metricsCalculated: number;
  insightsGenerated: number;
  durationMs: number;
  summary: string;
}

// Ask Your Data Types
export interface EvidenceItem {
  id: string;
  title: string;
  sourceColumn: string;
  calculationType: 'Sum' | 'Average' | 'Median' | 'Count' | 'Growth' | 'Distribution' | 'Filter & Sort';
  formulaOrQuery: string;
  rawResult: string | number;
  formattedResult: string;
  confidence: number; // 0 - 1
  verifiedByEngine: boolean;
  datasetVersionId?: string;
  rowCountAnalyzed?: number;
  executionTimeMs?: number;
}

export interface AskMessage {
  id: string;
  sender: 'user' | 'assistant';
  timestamp: string;
  content: string;
  directAnswer?: string;
  metrics?: { label: string; value: string; trend?: string; isPositive?: boolean }[];
  chartData?: {
    type: 'bar' | 'line' | 'pie';
    title: string;
    labels: string[];
    values: number[];
    unit?: string;
  };
  tableData?: {
    headers: string[];
    rows: (string | number)[][];
  };
  interpretation?: string;
  evidence?: EvidenceItem[];
  warnings?: string[];
  suggestedFollowUps?: string[];
  needsClarification?: boolean;
  clarificationPrompt?: string;
  clarificationOptions?: {
    key: string;
    label: string;
    explanation: string;
    filter_value?: string;
    metric_name?: string;
  }[];
  rawSql?: string;
  executionTimeMs?: number;
  rowCount?: number;
  businessInferences?: string[];
  recommendations?: string[];
  backendSessionId?: string;
  backendMessageId?: string;
}

export interface ConversationSession {
  id: string;
  title: string;
  datasetId: string;
  datasetName: string;
  updatedAt: string;
  messageCount: number;
  messages: AskMessage[];
}

// Prompt Lab Types
export type PromptVariantStrategy = 'baseline' | 'structured' | 'few_shot' | 'custom';

export interface PromptVariant {
  id: string;
  strategy: PromptVariantStrategy;
  title: string;
  description: string;
  systemPrompt: string;
  userPromptTemplate: string;
  temperature: number;
  model: string;
  isBest?: boolean;
}

export interface EvaluationCriterion {
  id: string;
  name: string;
  category: 'deterministic' | 'model_based';
  description: string;
  weight: number; // 0 - 1
}

export interface CriterionScore {
  criterionId: string;
  score: number; // 0 - 100
  feedback: string;
  verifiedFactChecksPassed?: number;
  totalChecks?: number;
}

export interface VariantOutputResult {
  variantId: string;
  outputRaw: string;
  latencyMs: number;
  inputTokens: number;
  outputTokens: number;
  costUsd: number;
  scores: Record<string, CriterionScore>;
  overallScore: number;
  hasSchemaError?: boolean;
  groundedFactsCount: number;
  unverifiedClaimsCount: number;
}

export interface TestCase {
  id: string;
  name: string;
  businessQuestion: string;
  expectedKeyFact: string;
  groundTruthCalculation: string;
}

export interface PromptExperiment {
  id: string;
  title: string;
  objective: string;
  businessTask: string;
  datasetId: string;
  datasetName: string;
  createdAt: string;
  updatedAt: string;
  status: 'draft' | 'running' | 'completed';
  criteria: EvaluationCriterion[];
  testCases: TestCase[];
  variants: PromptVariant[];
  resultsByTestCase: Record<string, Record<string, VariantOutputResult>>; // testCaseId -> variantId -> result
  bestVariantId?: string;
  summaryObservation?: string;
}

// Reports Types
export type ReportType = 
  | 'Executive Summary' 
  | 'Sales & Revenue Analysis' 
  | 'Operations & Performance' 
  | 'Data Quality Audit' 
  | 'Custom Analytical Brief'
  | (string & {});

export type ExportFormat = 'pdf' | 'docx' | 'xlsx' | 'csv';

export interface ReportExportOptions {
  format: ExportFormat;
  includeRawData?: boolean;
  includeCharts?: boolean;
  selectedSections?: Record<string, boolean>;
  filters?: FilterCondition[];
}

export interface StoredReportFile {
  id: string;
  reportId: string;
  fileName: string;
  format: ExportFormat;
  mimeType: string;
  fileSizeBytes: number;
  createdAt: string;
  blob?: Blob;
  data?: ArrayBuffer;
}

export interface ReportGenerationResult {
  success: boolean;
  report: Report;
  fileBlob: Blob;
  fileName: string;
  format: ExportFormat;
  fileSizeBytes: number;
  fileSizeFormatted: string;
  rowCountAnalyzed: number;
  error?: string;
}

export interface ReportSection {
  id: string;
  title: string;
  type: 'executive_summary' | 'kpis' | 'chart' | 'table' | 'insights' | 'recommendations' | 'methodology';
  contentMarkdown?: string;
  included: boolean;
  verifiedCalculationSnippet?: string;
  chartConfig?: {
    type: 'bar' | 'line' | 'pie';
    title: string;
    labels: string[];
    values: number[];
  };
  tableData?: {
    headers: string[];
    rows: (string | number)[][];
  };
}

export interface Report {
  id: string;
  title: string;
  type: ReportType;
  datasetId: string;
  datasetName: string;
  datasetVersion: string;
  analysisRunId: string;
  createdAt: string;
  updatedAt: string;
  period: string;
  audience: 'Executive Board' | 'Department Leads' | 'Investors' | 'General Operations' | 'Operations Team' | 'Leadership';
  language: string;
  detailLevel: 'Concise' | 'Standard' | 'In-Depth';
  status: 'Approved' | 'Draft' | 'Published' | 'Archived' | (string & {});
  author: string;
  isFavorite?: boolean;
  isSharedWithMe?: boolean;
  sections: ReportSection[];
  format?: ExportFormat;
  fileName?: string;
  fileSizeBytes?: number;
  fileSizeFormatted?: string;
  rowCountAnalyzed?: number;
  hasStoredFile?: boolean;
  shareConfig: {
    shareId: string;
    isActive: boolean;
    expiresAt?: string;
    accessCount: number;
    allowExport: boolean;
  };
}

export interface NotificationItem {
  id: string;
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  type: 'info' | 'success' | 'warning';
  linkTo?: string;
}

