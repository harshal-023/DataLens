import { DatasetImportError } from '../types';

export interface FileValidationOptions {
  maxFileSizeBytes?: number;
  maxColumns?: number;
  allowedExtensions?: string[];
}

export interface FileValidationResult {
  isValid: boolean;
  error?: string;
  warnings?: string[];
  errors?: DatasetImportError[];
  detectedType?: 'csv' | 'xlsx' | 'xls';
}

export const DEFAULT_VALIDATION_OPTIONS: Required<FileValidationOptions> = {
  maxFileSizeBytes: 50 * 1024 * 1024, // 50MB browser processing threshold
  maxColumns: 250,
  allowedExtensions: ['.csv', '.xlsx', '.xls'],
};

export class FileValidationService {
  /**
   * Pre-parsing validation: Validates raw File object metadata (extension, size, empty file)
   */
  static validateFile(
    file: File,
    options: FileValidationOptions = {}
  ): FileValidationResult {
    const opts = { ...DEFAULT_VALIDATION_OPTIONS, ...options };
    const warnings: string[] = [];

    if (!file) {
      return {
        isValid: false,
        error: 'No file provided for upload.',
        errors: [{ type: 'validation', message: 'No file provided.' }],
      };
    }

    // 1. Check empty file (size === 0)
    if (file.size === 0) {
      return {
        isValid: false,
        error: 'The uploaded file is empty (0 bytes). Please upload a valid dataset.',
        errors: [{ type: 'empty', message: 'File is 0 bytes.' }],
      };
    }

    // 2. Check file extension
    const fileName = file.name.toLowerCase();
    const matchedExt = opts.allowedExtensions.find((ext) => fileName.endsWith(ext));

    if (!matchedExt) {
      return {
        isValid: false,
        error: `Unsupported file format. Please upload a CSV (.csv) or Excel (.xlsx, .xls) file.`,
        errors: [
          {
            type: 'format',
            message: `Unsupported extension for "${file.name}". Allowed: ${opts.allowedExtensions.join(', ')}`,
          },
        ],
      };
    }

    const detectedType = matchedExt.replace('.', '') as 'csv' | 'xlsx' | 'xls';

    // 3. Check file size against threshold
    if (file.size > opts.maxFileSizeBytes) {
      const maxMb = Math.round(opts.maxFileSizeBytes / (1024 * 1024));
      const actualMb = (file.size / (1024 * 1024)).toFixed(1);
      return {
        isValid: false,
        error: `File size (${actualMb} MB) exceeds maximum allowed browser upload limit of ${maxMb} MB.`,
        errors: [
          {
            type: 'quota',
            message: `File size ${actualMb}MB exceeds ${maxMb}MB threshold.`,
          },
        ],
      };
    }

    if (file.size > 25 * 1024 * 1024) {
      warnings.push('Large file detected (>25MB). Processing may take several seconds in browser memory.');
    }

    return {
      isValid: true,
      warnings,
      detectedType,
    };
  }

  /**
   * Post-parsing validation: Validates parsed tabular structure (headers, row counts, columns)
   */
  static validateParsedStructure(
    headers: string[],
    rows: Record<string, any>[],
    options: FileValidationOptions = {}
  ): FileValidationResult {
    const opts = { ...DEFAULT_VALIDATION_OPTIONS, ...options };
    const warnings: string[] = [];
    const errors: DatasetImportError[] = [];

    // 1. Check for empty headers
    if (!headers || headers.length === 0) {
      return {
        isValid: false,
        error: 'Dataset does not contain any column headers.',
        errors: [{ type: 'header', message: 'No column headers detected in source.' }],
      };
    }

    // 2. Check for duplicate headers
    const seenHeaders = new Set<string>();
    const duplicateHeaders: string[] = [];
    headers.forEach((h) => {
      const normalized = h.trim().toLowerCase();
      if (seenHeaders.has(normalized)) {
        duplicateHeaders.push(h);
      } else {
        seenHeaders.add(normalized);
      }
    });

    if (duplicateHeaders.length > 0) {
      warnings.push(
        `Duplicate column header(s) detected: "${duplicateHeaders.join(', ')}". Columns were automatically suffixed to prevent collision.`
      );
    }

    // 3. Check excessive column count
    if (headers.length > opts.maxColumns) {
      return {
        isValid: false,
        error: `Dataset has ${headers.length} columns, exceeding the maximum supported limit of ${opts.maxColumns} columns.`,
        errors: [
          {
            type: 'validation',
            message: `Too many columns (${headers.length} > ${opts.maxColumns}).`,
          },
        ],
      };
    }

    // 4. Check empty rows
    if (!rows || rows.length === 0) {
      return {
        isValid: false,
        error: 'The dataset has headers but contains zero data rows.',
        errors: [{ type: 'empty', message: 'Dataset contains 0 data rows.' }],
      };
    }

    return {
      isValid: errors.length === 0,
      errors: errors.length > 0 ? errors : undefined,
      warnings,
    };
  }
}

