import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Upload,
  Database,
  Search,
  CheckCircle2,
  AlertCircle,
  FileSpreadsheet,
  Trash2,
  ArrowRight,
  ExternalLink,
  LayoutGrid,
  List,
  Layers,
  FileText,
  AlertTriangle,
} from 'lucide-react';
import { Button } from '../../components/common/Button';
import { Modal } from '../../components/common/Modal';
import { Stepper } from '../../components/common/Stepper';
import { Dataset, DatasetColumn } from '../../types';
import { StorageService } from '../../services/storageService';
import { DatasetApi } from '../../services/apiClient';
import { useAuth } from '../../context/AuthContext';
import { CsvParser } from '../../services/csvParser';
import { ExcelParser, ExcelWorkbookInfo } from '../../services/excelParser';
import { FileValidationService } from '../../services/fileValidationService';
import {
  inferColumnType,
  calculateColumnStats,
  detectDataQualityIssues,
} from '../../services/analyticsEngine';

export const DataStudio: React.FC = () => {
  const navigate = useNavigate();
  const auth = useAuth();
  const [datasets, setDatasets] = useState<Dataset[]>(StorageService.getDatasets());
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'ready' | 'warning' | 'processing'>('all');
  const [sortBy, setSortBy] = useState<'uploadedAt' | 'rowCount' | 'name'>('uploadedAt');
  const [viewMode, setViewMode] = useState<'list' | 'grid'>('list');

  // IndexedDB migration state
  const [unmigratedLocalCount, setUnmigratedLocalCount] = useState(0);
  const [isMigrating, setIsMigrating] = useState(false);
  const [migrationMessage, setMigrationMessage] = useState<string | null>(null);

  // Load datasets asynchronously from backend and IndexedDB
  const loadAllDatasets = async () => {
    let combined: Dataset[] = [];
    const local = await StorageService.getDatasetsAsync();

    const unmigrated = await StorageService.getUnmigratedLocalDatasets();
    setUnmigratedLocalCount(unmigrated.length);

    if (auth.currentWorkspace?.id) {
      try {
        const res = await DatasetApi.list(auth.currentWorkspace.id, { pageSize: 50 });
        if (res && res.items) {
          const backendDatasets: Dataset[] = res.items.map((item: any) => ({
            id: item.id,
            name: item.name,
            description: `Server-persisted dataset in ${auth.currentWorkspace?.name || 'Workspace'}.`,
            sourceFileName: item.original_filename,
            originalFileName: item.original_filename,
            fileType: item.file_type,
            fileSizeFormatted: 'Cloud Storage',
            rowCount: item.row_count,
            columnCount: item.column_count,
            uploadedAt: item.created_at,
            lastAnalyzedAt: item.updated_at,
            status: item.status === 'ready' ? 'ready' : 'analyzing',
            currentVersion: 'v1.0',
            versions: [],
            columns: [],
            qualityScore: 95,
            qualityIssues: [],
            previewRows: [],
            tags: ['Cloud', 'Parquet', item.file_type.toUpperCase()],
          }));

          const backendIds = new Set(backendDatasets.map((d) => d.id));
          const localOnly = local.filter((d) => !backendIds.has(d.id) && !StorageService.getMigratedBackendId(d.id));
          combined = [...backendDatasets, ...localOnly];
        }
      } catch (e) {
        console.warn('Backend datasets unavailable, showing local datasets:', e);
        combined = local;
      }
    } else {
      combined = local;
    }

    setDatasets(combined.length > 0 ? combined : local);
  };

  useEffect(() => {
    loadAllDatasets();
  }, [auth.currentWorkspace?.id]);

  // Upload Wizard State
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [uploadStep, setUploadStep] = useState(1);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  // Parsing & Excel Workbook State
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [validationWarnings, setValidationWarnings] = useState<string[]>([]);

  // Excel multi-sheet support
  const [excelWorkbook, setExcelWorkbook] = useState<any | null>(null);
  const [excelInfo, setExcelInfo] = useState<ExcelWorkbookInfo | null>(null);
  const [selectedSheetName, setSelectedSheetName] = useState<string>('');

  // Structured parsed data
  const [parsedHeaders, setParsedHeaders] = useState<string[]>([]);
  const [parsedAllRows, setParsedAllRows] = useState<Record<string, any>[]>([]);
  const [detectedColumns, setDetectedColumns] = useState<DatasetColumn[]>([]);
  const [auditResults, setAuditResults] = useState<{ qualityScore: number; issues: any[] } | null>(null);
  const [datasetName, setDatasetName] = useState('');

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Filter & Sort
  const filteredDatasets = datasets
    .filter((d) => {
      const matchSearch =
        d.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (d.tags && d.tags.some((t) => t.toLowerCase().includes(searchQuery.toLowerCase()))) ||
        (d.description && d.description.toLowerCase().includes(searchQuery.toLowerCase()));
      const matchStatus =
        statusFilter === 'all'
          ? true
          : statusFilter === 'ready'
          ? d.status === 'ready'
          : statusFilter === 'warning'
          ? d.qualityIssues && d.qualityIssues.length > 0
          : d.status === 'analyzing';
      return matchSearch && matchStatus;
    })
    .sort((a, b) => {
      if (sortBy === 'name') return a.name.localeCompare(b.name);
      if (sortBy === 'rowCount') return b.rowCount - a.rowCount;
      return new Date(b.uploadedAt).getTime() - new Date(a.uploadedAt).getTime();
    });

  // Process chosen file (CSV or Excel)
  const processSelectedFile = async (file: File) => {
    setValidationError(null);
    setValidationWarnings([]);
    setUploadedFile(file);
    setDatasetName(file.name.replace(/\.[^/.]+$/, ''));
    setIsAnalyzing(true);

    // 1. Pre-parsing Validation
    const validation = FileValidationService.validateFile(file);
    if (!validation.isValid) {
      setValidationError(validation.error || 'Invalid file format.');
      setIsAnalyzing(false);
      return;
    }

    if (validation.warnings) {
      setValidationWarnings(validation.warnings);
    }

    try {
      const detectedType = validation.detectedType;

      if (detectedType === 'csv') {
        // Parse CSV using PapaParse
        const parsed = await CsvParser.parse(file);
        handleParsedDataReady(parsed.headers, parsed.rows, file.name);
      } else if (detectedType === 'xlsx' || detectedType === 'xls') {
        // Read Excel binary workbook info
        const { workbook, info } = await ExcelParser.readWorkbookInfo(file);
        setExcelWorkbook(workbook);
        setExcelInfo(info);

        const initialSheet = info.sheetNames[0];
        setSelectedSheetName(initialSheet);

        // Parse default first sheet
        const parsedSheet = ExcelParser.parseWorksheet(workbook, initialSheet, {
          name: file.name,
          size: file.size,
        });

        handleParsedDataReady(parsedSheet.headers, parsedSheet.rows, file.name, initialSheet);
      }
    } catch (err: any) {
      console.error('File parsing error:', err);
      setValidationError(err?.message || 'Failed to parse file. Please verify file integrity.');
      setIsAnalyzing(false);
    }
  };

  // Change active Excel sheet
  const handleSheetChange = (sheetName: string) => {
    if (!excelWorkbook || !uploadedFile) return;
    setSelectedSheetName(sheetName);
    setIsAnalyzing(true);

    try {
      const parsedSheet = ExcelParser.parseWorksheet(excelWorkbook, sheetName, {
        name: uploadedFile.name,
        size: uploadedFile.size,
      });

      handleParsedDataReady(parsedSheet.headers, parsedSheet.rows, uploadedFile.name, sheetName);
    } catch (err: any) {
      setValidationError(err?.message || 'Failed to read worksheet.');
      setIsAnalyzing(false);
    }
  };

  // Common pipeline once rows & headers are available
  const handleParsedDataReady = (
    headers: string[],
    rows: Record<string, any>[],
    fileName: string,
    sheetName?: string
  ) => {
    // 2. Post-parsing structure validation
    const structVal = FileValidationService.validateParsedStructure(headers, rows);
    if (!structVal.isValid) {
      setValidationError(structVal.error || 'Parsed dataset is empty or invalid.');
      setIsAnalyzing(false);
      return;
    }

    if (structVal.warnings) {
      setValidationWarnings((prev) => [...prev, ...structVal.warnings!]);
    }

    setParsedHeaders(headers);
    setParsedAllRows(rows);

    // 3. Infer column types and calculate summary statistics
    const cols: DatasetColumn[] = headers.map((h, i) => {
      const values = rows.map((r) => r[h]);
      const type = inferColumnType(values);
      const stats = calculateColumnStats(h, rows, type);

      return {
        id: `col-${i}`,
        name: h,
        displayName: h.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()),
        type,
        missingCount: stats.missingCount,
        uniqueCount: stats.uniqueCount,
        sampleValues: values.filter((v) => v !== null && v !== undefined && v !== '').slice(0, 5),
        min: stats.min,
        max: stats.max,
        mean: stats.mean,
        isKey: i === 0,
      };
    });

    setDetectedColumns(cols);

    // 4. Run automated data-quality audit
    const audit = detectDataQualityIssues(cols, rows);
    setAuditResults(audit);

    setIsAnalyzing(false);
    setUploadStep(2);
  };

  // Input change
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      processSelectedFile(file);
    }
  };

  // Drag and drop handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) {
      processSelectedFile(file);
    }
  };

  // Step 4: Finish upload & save atomically into IndexedDB
  const handleFinishUpload = async () => {
    if (!uploadedFile || parsedAllRows.length === 0) return;
    setIsSaving(true);
    setValidationError(null);

    const isExcel = uploadedFile.name.toLowerCase().endsWith('.xlsx') || uploadedFile.name.toLowerCase().endsWith('.xls');

    const newDataset: Dataset = {
      id: `ds-${Date.now()}`,
      name: datasetName.trim() || uploadedFile.name,
      description: `Ingested ${isExcel ? 'Excel' : 'CSV'} dataset containing ${parsedAllRows.length.toLocaleString()} rows and ${parsedHeaders.length} columns.`,
      sourceFileName: uploadedFile.name,
      originalFileName: uploadedFile.name,
      fileType: uploadedFile.name.toLowerCase().endsWith('.xlsx')
        ? 'xlsx'
        : uploadedFile.name.toLowerCase().endsWith('.xls')
        ? 'xls'
        : 'csv',
      fileSizeBytes: uploadedFile.size,
      fileSizeFormatted: `${(uploadedFile.size / (1024 * 1024)).toFixed(1)} MB`,
      rowCount: parsedAllRows.length,
      columnCount: parsedHeaders.length,
      uploadedAt: new Date().toISOString(),
      lastAnalyzedAt: new Date().toISOString(),
      status: 'ready',
      currentVersion: 'v1.0',
      versions: [
        {
          versionId: `v-${Date.now()}`,
          versionNumber: 'v1.0',
          createdAt: new Date().toISOString(),
          createdBy: 'Harshal Sharma',
          changeSummary: `Complete ingestion of ${parsedAllRows.length.toLocaleString()} records into IndexedDB.`,
          rowCount: parsedAllRows.length,
          columnCount: parsedHeaders.length,
        },
      ],
      qualityScore: auditResults ? auditResults.qualityScore : 94,
      qualityIssues: auditResults ? auditResults.issues : [],
      columns: detectedColumns,
      previewRows: parsedAllRows.slice(0, 50),
      tags: [isExcel ? 'Excel' : 'CSV', 'Business', 'IndexedDB'],
      selectedWorksheet: isExcel ? selectedSheetName : undefined,
      availableWorksheets: excelInfo ? excelInfo.sheetNames : undefined,
    };

    // Save complete dataset (metadata + ALL rows) into IndexedDB
    const result = await StorageService.saveCompleteDatasetAsync(newDataset, parsedAllRows);

    if (!result.success) {
      setIsSaving(false);
      setValidationError(result.error || 'Failed to save dataset into IndexedDB.');
      return;
    }

    // Also upload to FastAPI Backend if authenticated in an active workspace
    if (auth.currentWorkspace?.id && uploadedFile) {
      try {
        const formData = new FormData();
        formData.append('file', uploadedFile);
        formData.append('name', datasetName.trim() || uploadedFile.name);
        if (selectedSheetName) formData.append('selected_worksheet', selectedSheetName);
        const backendRes = await DatasetApi.upload(auth.currentWorkspace.id, formData);
        if (backendRes && backendRes.id) {
          StorageService.markDatasetMigrated(newDataset.id, backendRes.id);
        }
      } catch (backendErr: any) {
        console.warn('Backend upload notice (persisted in IndexedDB):', backendErr);
      }
    }

    // Refresh dataset list
    await loadAllDatasets();

    setIsSaving(false);
    setIsUploadOpen(false);
    resetWizard();
    navigate(`/data/${newDataset.id}`);
  };

  const handleMigrateAll = async () => {
    if (!auth.currentWorkspace?.id) {
      alert('Please select or create an active workspace before migrating datasets.');
      return;
    }
    setIsMigrating(true);
    setMigrationMessage('Starting migration of local datasets to cloud workspace...');
    try {
      const unmigrated = await StorageService.getUnmigratedLocalDatasets();
      let migratedCount = 0;
      for (const ds of unmigrated) {
        setMigrationMessage(`Uploading "${ds.name}" (${migratedCount + 1}/${unmigrated.length})...`);
        const result = await StorageService.migrateLocalDatasetToBackend(ds.id, auth.currentWorkspace.id);
        if (result.success) {
          migratedCount++;
        }
      }
      setMigrationMessage(`Successfully migrated ${migratedCount} dataset(s) to ${auth.currentWorkspace.name}!`);
      setTimeout(() => setMigrationMessage(null), 4000);
      await loadAllDatasets();
    } catch (err: any) {
      setMigrationMessage(`Migration error: ${err.message || 'Failed'}`);
    } finally {
      setIsMigrating(false);
    }
  };

  const handleDeleteDataset = async (datasetId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.confirm('Are you sure you want to delete this dataset? All associated records will be removed.')) {
      if (auth.currentWorkspace?.id) {
        try {
          await DatasetApi.delete(auth.currentWorkspace.id, datasetId);
        } catch (err) {
          console.warn('Backend delete error (deleting local):', err);
        }
      }
      await StorageService.deleteDatasetAsync(datasetId);
      await loadAllDatasets();
    }
  };

  const resetWizard = () => {
    setUploadStep(1);
    setUploadedFile(null);
    setParsedHeaders([]);
    setParsedAllRows([]);
    setDetectedColumns([]);
    setAuditResults(null);
    setDatasetName('');
    setExcelWorkbook(null);
    setExcelInfo(null);
    setSelectedSheetName('');
    setValidationError(null);
    setValidationWarnings([]);
  };

  const uploadSteps = [
    { id: 1, label: 'Upload File', description: 'CSV or Excel' },
    { id: 2, label: 'Review Schema', description: 'Inferred Types' },
    { id: 3, label: 'Quality Audit', description: 'Check Warnings' },
    { id: 4, label: 'Confirm & Ingest', description: 'Save Complete' },
  ];

  return (
    <div className="space-y-6">
      {/* 1. Page Header matching reference */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-start gap-3.5">
          <div className="w-12 h-12 rounded-2xl bg-[#EDF7FA] border border-[#BBDCE8] flex items-center justify-center text-[#007D78] shrink-0 shadow-2xs">
            <Database className="w-6 h-6 text-[#009F98]" />
          </div>
          <div>
            <h1 className="text-2xl sm:text-3xl font-serif text-[#102C46] tracking-tight">
              Data Studio
            </h1>
            <p className="text-xs text-[#52616C] mt-1 font-medium">
              Manage data assets, inspect inferred schemas, review quality flags, and maintain version lineage.
            </p>
          </div>
        </div>

        <button
          onClick={() => {
            resetWizard();
            setIsUploadOpen(true);
          }}
          className="px-4 py-2.5 rounded-xl bg-[#009F98] hover:bg-[#007D78] text-white text-xs font-bold flex items-center gap-2 shadow-2xs cursor-pointer transition-all shrink-0"
        >
          <Upload className="w-4 h-4" />
          <span>Upload Dataset</span>
        </button>
      </div>

      {/* IndexedDB to Backend Workspace Migration Banner */}
      {unmigratedLocalCount > 0 && auth.currentWorkspace && (
        <div className="bg-[#EDF7FA] border border-[#BBDCE8] rounded-2xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-subtle animate-in fade-in-50">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-[#009F98] text-white flex items-center justify-center shrink-0">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs font-bold text-[#102C46]">
                Local IndexedDB Datasets Detected ({unmigratedLocalCount})
              </p>
              <p className="text-[11px] text-[#52616C] mt-0.5">
                Upload your local browser-stored datasets to <strong>{auth.currentWorkspace.name}</strong> for server-side Parquet persistence and workspace collaboration.
              </p>
              {migrationMessage && (
                <p className="text-[11px] text-[#007D78] font-bold mt-1 animate-pulse">
                  {migrationMessage}
                </p>
              )}
            </div>
          </div>
          <button
            onClick={handleMigrateAll}
            disabled={isMigrating}
            className="px-4 py-2 rounded-xl bg-[#009F98] hover:bg-[#007D78] text-white text-xs font-bold shrink-0 transition-colors cursor-pointer disabled:opacity-60 flex items-center gap-2"
          >
            {isMigrating && <div className="w-3.5 h-3.5 rounded-full border-2 border-white border-t-transparent animate-spin" />}
            <span>{isMigrating ? 'Migrating...' : 'Migrate to Cloud'}</span>
          </button>
        </div>
      )}

      {/* 2. Top Filter Bar & View Switcher */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
        {/* Left Status Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          <button
            onClick={() => setStatusFilter('all')}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer whitespace-nowrap ${
              statusFilter === 'all'
                ? 'bg-[#009F98] text-white shadow-2xs'
                : 'bg-[#EEF3F6] text-[#52616C] hover:bg-[#DDF0F5] hover:text-[#102C46]'
            }`}
          >
            All Datasets ({datasets.length})
          </button>
          <button
            onClick={() => setStatusFilter('ready')}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer whitespace-nowrap ${
              statusFilter === 'ready'
                ? 'bg-[#009F98] text-white shadow-2xs'
                : 'bg-[#EEF3F6] text-[#52616C] hover:bg-[#DDF0F5] hover:text-[#102C46]'
            }`}
          >
            Ready ({datasets.filter((d) => d.status === 'ready').length})
          </button>
          <button
            onClick={() => setStatusFilter('warning')}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer whitespace-nowrap ${
              statusFilter === 'warning'
                ? 'bg-[#009F98] text-white shadow-2xs'
                : 'bg-[#EEF3F6] text-[#52616C] hover:bg-[#DDF0F5] hover:text-[#102C46]'
            }`}
          >
            Warnings ({datasets.filter((d) => d.qualityIssues && d.qualityIssues.length > 0).length})
          </button>
        </div>

        {/* Right Sort selector & Grid/List switcher */}
        <div className="flex items-center gap-2.5">
          {/* Search Input */}
          <div className="relative w-48 sm:w-56">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[#52616C]" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search datasets..."
              className="w-full pl-8 pr-3 py-1.5 text-xs rounded-xl border border-[#DCE5EB] bg-[#F5F8FA] text-[#102C46] placeholder:text-[#52616C] focus:outline-none focus:ring-1 focus:ring-[#009F98]"
            />
          </div>

          {/* Sort By Dropdown */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="px-3 py-1.5 text-xs rounded-xl border border-[#DCE5EB] bg-white text-[#102C46] font-medium focus:outline-none focus:ring-1 focus:ring-[#009F98] cursor-pointer"
          >
            <option value="uploadedAt">Sort: Recently Uploaded</option>
            <option value="rowCount">Sort: Row Count</option>
            <option value="name">Sort: Name (A-Z)</option>
          </select>

          {/* View Toggle */}
          <div className="flex items-center gap-1 bg-[#EEF3F6] p-1 rounded-xl border border-[#DCE5EB]">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-1.5 rounded-lg transition-colors cursor-pointer ${
                viewMode === 'grid'
                  ? 'bg-[#009F98] text-white shadow-2xs'
                  : 'text-[#52616C] hover:text-[#102C46]'
              }`}
              title="Grid View"
            >
              <LayoutGrid className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-1.5 rounded-lg transition-colors cursor-pointer ${
                viewMode === 'list'
                  ? 'bg-[#009F98] text-white shadow-2xs'
                  : 'text-[#52616C] hover:text-[#102C46]'
              }`}
              title="List View"
            >
              <List className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* 3. Table View */}
      {viewMode === 'list' ? (
        <div className="bg-white rounded-2xl border border-[#DCE5EB] overflow-hidden shadow-subtle">
          <table className="w-full text-left text-xs border-collapse">
            <thead className="bg-[#F5F8FA] text-[#102C46] font-semibold border-b border-[#DCE5EB]">
              <tr>
                <th className="py-3.5 px-4">Dataset</th>
                <th className="py-3.5 px-3">Format</th>
                <th className="py-3.5 px-3">Version</th>
                <th className="py-3.5 px-3">Rows</th>
                <th className="py-3.5 px-3">Columns</th>
                <th className="py-3.5 px-3">Size</th>
                <th className="py-3.5 px-3">Quality Score</th>
                <th className="py-3.5 px-3">Updated</th>
                <th className="py-3.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#EEF3F6]">
              {filteredDatasets.map((ds) => (
                <tr
                  key={ds.id}
                  onClick={() => navigate(`/data/${ds.id}`)}
                  className="hover:bg-[#EDF7FA]/50 transition-colors cursor-pointer group"
                >
                  <td className="py-3.5 px-4">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-xl bg-[#EDF7FA] text-[#007D78] flex items-center justify-center shrink-0 border border-[#BBDCE8]">
                        <FileSpreadsheet className="w-4 h-4 text-[#009F98]" />
                      </div>
                      <div>
                        <span className="font-bold text-[#102C46] group-hover:text-[#009F98] transition-colors block">
                          {ds.name}
                        </span>
                        <span className="text-[11px] text-[#52616C] line-clamp-1">
                          {ds.description}
                        </span>
                      </div>
                    </div>
                  </td>

                  <td className="py-3.5 px-3">
                    <span className="px-2 py-0.5 rounded-full uppercase text-[10px] font-bold bg-[#EDF7FA] text-[#007D78] border border-[#BBDCE8]">
                      {ds.fileType || (ds.sourceFileName.endsWith('.xlsx') ? 'xlsx' : 'csv')}
                    </span>
                  </td>

                  <td className="py-3.5 px-3">
                    <span className="px-2 py-0.5 rounded-full bg-[#EEF3F6] text-[#102C46] text-[11px] font-semibold border border-[#DCE5EB]">
                      {ds.currentVersion || 'v1'}
                    </span>
                  </td>

                  <td className="py-3.5 px-3 font-semibold text-[#102C46]">
                    {ds.rowCount.toLocaleString()}
                  </td>

                  <td className="py-3.5 px-3 font-medium text-[#52616C]">
                    {ds.columnCount}
                  </td>

                  <td className="py-3.5 px-3 text-[#52616C]">
                    {ds.fileSizeFormatted}
                  </td>

                  <td className="py-3.5 px-3">
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-[#E4F3EC] text-[#216548] border border-[#C3E7D5]">
                      {ds.qualityScore}%
                    </span>
                  </td>

                  <td className="py-3.5 px-3 text-[#52616C] whitespace-nowrap">
                    {new Date(ds.uploadedAt).toLocaleDateString('en-GB', {
                      day: '2-digit',
                      month: 'short',
                      year: 'numeric',
                    })}
                  </td>

                  <td className="py-3.5 px-4 text-right">
                    <div className="flex items-center justify-end gap-2" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={(e) => handleDeleteDataset(ds.id, e)}
                        className="p-1.5 rounded-lg text-[#52616C] hover:text-[#A63838] hover:bg-[#FCE9E9] transition-colors cursor-pointer"
                        title="Delete dataset"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => navigate(`/data/${ds.id}`)}
                        className="p-1.5 rounded-lg text-[#52616C] hover:text-[#009F98] hover:bg-[#EEF3F6] transition-colors cursor-pointer"
                        title="View details"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        /* Grid View */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredDatasets.map((ds) => (
            <div
              key={ds.id}
              onClick={() => navigate(`/data/${ds.id}`)}
              className="bg-white rounded-2xl border border-[#DCE5EB] p-5 shadow-subtle hover:border-[#009F98] hover:shadow-elevated transition-all cursor-pointer group flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-[#EDF7FA] text-[#007D78] flex items-center justify-center shrink-0 border border-[#BBDCE8]">
                      <FileSpreadsheet className="w-5 h-5 text-[#009F98]" />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-[#102C46] group-hover:text-[#009F98] transition-colors">
                        {ds.name}
                      </h3>
                      <span className="text-[11px] text-[#52616C]">{ds.sourceFileName}</span>
                    </div>
                  </div>
                  <span className="px-2 py-0.5 rounded-full bg-[#E4F3EC] text-[#216548] text-[11px] font-bold">
                    {ds.qualityScore}% Quality
                  </span>
                </div>

                <p className="text-xs text-[#52616C] line-clamp-2 mt-2 leading-relaxed">
                  {ds.description}
                </p>

                <div className="grid grid-cols-3 gap-2 mt-4 pt-3 border-t border-[#EEF3F6] text-center">
                  <div className="bg-[#F5F8FA] p-2 rounded-xl">
                    <span className="text-[10px] text-[#52616C] block">Rows</span>
                    <span className="text-xs font-bold text-[#102C46]">
                      {ds.rowCount.toLocaleString()}
                    </span>
                  </div>
                  <div className="bg-[#F5F8FA] p-2 rounded-xl">
                    <span className="text-[10px] text-[#52616C] block">Cols</span>
                    <span className="text-xs font-bold text-[#102C46]">{ds.columnCount}</span>
                  </div>
                  <div className="bg-[#F5F8FA] p-2 rounded-xl">
                    <span className="text-[10px] text-[#52616C] block">Format</span>
                    <span className="text-xs font-bold text-[#102C46] uppercase">
                      {ds.fileType || 'csv'}
                    </span>
                  </div>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-[#EEF3F6] flex items-center justify-between text-xs text-[#52616C]">
                <span>
                  Updated {new Date(ds.uploadedAt).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })}
                </span>
                <span className="text-[#009F98] font-semibold flex items-center gap-1 group-hover:translate-x-0.5 transition-transform">
                  <span>Open Studio</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 4. Upload Dataset Wizard Modal (CSV & Excel) */}
      <Modal
        isOpen={isUploadOpen}
        onClose={() => {
          if (!isSaving) setIsUploadOpen(false);
        }}
        title="Upload Business Dataset"
        subtitle="Ingest CSV or Excel datasets, infer strict schemas, audit health, and store in IndexedDB."
        maxWidth="3xl"
      >
        <div className="space-y-6">
          <Stepper steps={uploadSteps} currentStep={uploadStep} />

          {/* Validation Error Banner */}
          {validationError && (
            <div className="p-3.5 rounded-xl bg-[#FCE9E9] border border-[#F7C9C5] text-xs text-[#A63838] flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-[#A63838]" />
              <div>
                <p className="font-bold">Validation Issue Detected</p>
                <p className="mt-0.5 leading-relaxed">{validationError}</p>
              </div>
            </div>
          )}

          {/* Validation Warnings Banner */}
          {validationWarnings.length > 0 && (
            <div className="p-3.5 rounded-xl bg-[#FFF3DF] border border-[#F9DFAC] text-xs text-[#98620D] flex items-start gap-2.5">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-[#98620D]" />
              <div className="space-y-1">
                <p className="font-bold">Notices</p>
                {validationWarnings.map((w, idx) => (
                  <p key={idx} className="leading-snug">{w}</p>
                ))}
              </div>
            </div>
          )}

          {/* Step 1: Upload Dropzone */}
          {uploadStep === 1 && (
            <div className="space-y-4">
              <div
                onClick={() => fileInputRef.current?.click()}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all ${
                  isDragging
                    ? 'border-[#009F98] bg-[#E0F5F3]'
                    : 'border-[#BBDCE8] hover:border-[#009F98] bg-[#F5F8FA] hover:bg-[#EDF7FA]'
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv,.xlsx,.xls,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel"
                  onChange={handleFileChange}
                  className="hidden"
                />
                <div className="w-12 h-12 rounded-2xl bg-[#EDF7FA] text-[#007D78] mx-auto flex items-center justify-center mb-3 shadow-2xs">
                  <Upload className="w-6 h-6 text-[#009F98]" />
                </div>
                <h4 className="text-sm font-bold text-[#102C46]">
                  Click or drag & drop CSV or Excel files
                </h4>
                <p className="text-xs text-[#52616C] mt-1">
                  Supports <b>.csv</b>, <b>.xlsx</b>, and <b>.xls</b> workbooks up to 50MB
                </p>
              </div>

              {isAnalyzing && (
                <div className="p-4 rounded-xl bg-[#EDF7FA] border border-[#BBDCE8] flex items-center gap-3">
                  <div className="w-4 h-4 rounded-full border-2 border-[#009F98] border-t-transparent animate-spin" />
                  <span className="text-xs font-semibold text-[#007D78]">
                    Parsing binary rows, inspecting sheets, and inferring column schemas...
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Step 2: Schema Review & Worksheet Selection */}
          {uploadStep === 2 && (
            <div className="space-y-4">
              {/* Dataset Name & Optional Worksheet Selector */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold text-[#102C46] block mb-1">Dataset Name</label>
                  <input
                    type="text"
                    value={datasetName}
                    onChange={(e) => setDatasetName(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-xl border border-[#DCE5EB] bg-white text-[#102C46] focus:outline-none focus:ring-2 focus:ring-[#009F98]"
                  />
                </div>

                {/* If Excel with multiple sheets, show interactive sheet switcher */}
                {excelInfo && excelInfo.sheetNames.length > 1 && (
                  <div>
                    <label className="text-xs font-bold text-[#102C46] block mb-1">
                      Select Worksheet ({excelInfo.sheetNames.length} available)
                    </label>
                    <select
                      value={selectedSheetName}
                      onChange={(e) => handleSheetChange(e.target.value)}
                      className="w-full px-3 py-2 text-xs rounded-xl border border-[#009F98] bg-[#EDF7FA] text-[#007D78] font-bold focus:outline-none focus:ring-2 focus:ring-[#009F98] cursor-pointer"
                    >
                      {excelInfo.sheetNames.map((name) => {
                        const ws = excelInfo.worksheets.find((w) => w.name === name);
                        return (
                          <option key={name} value={name}>
                            {name} {ws && ws.rowCount > 0 ? `(~${ws.rowCount} rows)` : ''}
                          </option>
                        );
                      })}
                    </select>
                  </div>
                )}
              </div>

              {/* Summary Stats Badges */}
              <div className="flex flex-wrap items-center gap-2 pt-1 text-xs">
                <span className="px-2.5 py-1 rounded-lg bg-[#F5F8FA] border border-[#DCE5EB] font-medium text-[#102C46]">
                  Total Records: <b>{parsedAllRows.length.toLocaleString()}</b>
                </span>
                <span className="px-2.5 py-1 rounded-lg bg-[#F5F8FA] border border-[#DCE5EB] font-medium text-[#102C46]">
                  Columns: <b>{detectedColumns.length}</b>
                </span>
                <span className="px-2.5 py-1 rounded-lg bg-[#F5F8FA] border border-[#DCE5EB] font-medium text-[#102C46]">
                  Format: <b>{uploadedFile?.name.split('.').pop()?.toUpperCase()}</b>
                </span>
                {selectedSheetName && (
                  <span className="px-2.5 py-1 rounded-lg bg-[#E0F5F3] border border-[#009F98]/30 font-medium text-[#007D78]">
                    Worksheet: <b>{selectedSheetName}</b>
                  </span>
                )}
              </div>

              {/* Inferred Schema Table */}
              <div>
                <h4 className="text-xs font-bold text-[#102C46] mb-2 uppercase tracking-wider">
                  Inferred Schema Attributes ({detectedColumns.length})
                </h4>
                <div className="max-h-56 overflow-y-auto border border-[#DCE5EB] rounded-xl">
                  <table className="w-full text-xs text-left">
                    <thead className="bg-[#F5F8FA] text-[#52616C] font-semibold border-b border-[#DCE5EB]">
                      <tr>
                        <th className="p-2.5">Column Name</th>
                        <th className="p-2.5">Inferred Type</th>
                        <th className="p-2.5">Distinct / Nulls</th>
                        <th className="p-2.5">Sample Values</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#EEF3F6]">
                      {detectedColumns.map((col) => (
                        <tr key={col.id}>
                          <td className="p-2.5 font-bold text-[#102C46]">{col.name}</td>
                          <td className="p-2.5">
                            <span className="px-2 py-0.5 rounded-full bg-[#EDF7FA] text-[#007D78] text-[10px] font-semibold">
                              {col.type}
                            </span>
                          </td>
                          <td className="p-2.5 text-[#52616C]">
                            {col.uniqueCount} unique · {col.missingCount} null
                          </td>
                          <td className="p-2.5 text-[#52616C] truncate max-w-xs">
                            {col.sampleValues && col.sampleValues.length > 0
                              ? col.sampleValues.slice(0, 3).join(', ')
                              : 'None'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-[#DCE5EB]">
                <Button variant="secondary" size="sm" onClick={() => setUploadStep(1)}>
                  Back
                </Button>
                <Button variant="primary" size="sm" onClick={() => setUploadStep(3)}>
                  Continue to Health Audit
                </Button>
              </div>
            </div>
          )}

          {/* Step 3: Quality Audit */}
          {uploadStep === 3 && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-[#E4F3EC] border border-[#C3E7D5] flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-bold text-[#216548]">
                    Data Quality Score: {auditResults?.qualityScore || 94}%
                  </h4>
                  <p className="text-xs text-[#216548] mt-0.5">
                    Automated deterministic audit on all {parsedAllRows.length.toLocaleString()} rows completed.
                  </p>
                </div>
                <CheckCircle2 className="w-6 h-6 text-[#216548]" />
              </div>

              {auditResults?.issues && auditResults.issues.length > 0 && (
                <div className="space-y-2">
                  <h5 className="text-xs font-bold text-[#102C46] uppercase tracking-wider">
                    Audit Observations ({auditResults.issues.length})
                  </h5>
                  <div className="max-h-48 overflow-y-auto space-y-1.5">
                    {auditResults.issues.map((iss: any) => (
                      <div
                        key={iss.id}
                        className="p-3 rounded-xl border border-[#DCE5EB] bg-[#F5F8FA] text-xs flex items-start justify-between"
                      >
                        <div>
                          <p className="font-semibold text-[#102C46]">{iss.title}</p>
                          <p className="text-[11px] text-[#52616C] mt-0.5">{iss.description}</p>
                        </div>
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${
                            iss.severity === 'high'
                              ? 'bg-[#FCE9E9] text-[#A63838]'
                              : 'bg-[#FFF3DF] text-[#98620D]'
                          }`}
                        >
                          {iss.severity}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex justify-end gap-2 pt-3 border-t border-[#DCE5EB]">
                <Button variant="secondary" size="sm" onClick={() => setUploadStep(2)}>
                  Back
                </Button>
                <Button variant="primary" size="sm" onClick={() => setUploadStep(4)}>
                  Confirm & Ingest
                </Button>
              </div>
            </div>
          )}

          {/* Step 4: Confirm & Store in IndexedDB */}
          {uploadStep === 4 && (
            <div className="space-y-4 text-center py-4">
              <div className="w-12 h-12 rounded-full bg-[#E4F3EC] text-[#216548] mx-auto flex items-center justify-center">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-[#102C46]">Dataset Ready for Ingestion</h3>
              <p className="text-xs text-[#52616C] max-w-md mx-auto leading-relaxed">
                All <b>{parsedAllRows.length.toLocaleString()}</b> records will be stored atomically in browser <b>IndexedDB</b>. Metadata and version lineage will be frozen as <b>v1.0</b>.
              </p>

              {isSaving && (
                <div className="p-3 rounded-xl bg-[#EDF7FA] border border-[#BBDCE8] flex items-center justify-center gap-2 max-w-sm mx-auto">
                  <div className="w-4 h-4 rounded-full border-2 border-[#009F98] border-t-transparent animate-spin" />
                  <span className="text-xs font-semibold text-[#007D78]">
                    Writing records to IndexedDB transaction...
                  </span>
                </div>
              )}

              <div className="flex justify-center gap-2 pt-4">
                <Button variant="secondary" size="sm" disabled={isSaving} onClick={() => setUploadStep(3)}>
                  Back
                </Button>
                <Button variant="primary" size="md" disabled={isSaving} onClick={handleFinishUpload}>
                  {isSaving ? 'Ingesting...' : 'Complete Ingestion'}
                </Button>
              </div>
            </div>
          )}
        </div>
      </Modal>
    </div>
  );
};
