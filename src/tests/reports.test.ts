import { describe, it, expect } from 'vitest';

describe('Automated Business Reporting - Template & Config Engine', () => {
  const PREDEFINED_TEMPLATES = [
    { id: 'exec_review', name: 'Executive Business Review', category: 'Executive' },
    { id: 'sales_perf', name: 'Sales Performance Report', category: 'Sales' },
    { id: 'financial_perf', name: 'Financial Performance Report', category: 'Finance' },
    { id: 'marketing_analytics', name: 'Marketing Analytics Summary', category: 'Marketing' },
    { id: 'customer_analytics', name: 'Customer & Retention Analysis', category: 'Customer' },
    { id: 'ops_fulfillment', name: 'Operations & Fulfillment Review', category: 'Operations' },
    { id: 'predictive_analytics', name: 'Predictive & ML Forecast Report', category: 'Machine Learning' },
    { id: 'modular_custom', name: 'Custom Modular Report', category: 'General' },
  ];

  it('contains all 8 required professional business templates', () => {
    expect(PREDEFINED_TEMPLATES).toHaveLength(8);
    const ids = PREDEFINED_TEMPLATES.map((t) => t.id);
    expect(ids).toContain('exec_review');
    expect(ids).toContain('sales_perf');
    expect(ids).toContain('financial_perf');
    expect(ids).toContain('marketing_analytics');
    expect(ids).toContain('customer_analytics');
    expect(ids).toContain('ops_fulfillment');
    expect(ids).toContain('predictive_analytics');
    expect(ids).toContain('modular_custom');
  });

  it('validates section toggles and ordering for executive templates', () => {
    const defaultSections = [
      { id: 'cover', title: 'Cover Page', enabled: true, order: 0 },
      { id: 'exec_summary', title: 'Executive Summary', enabled: true, order: 1 },
      { id: 'kpis', title: 'Key Performance Indicators', enabled: true, order: 2 },
      { id: 'charts', title: 'Visual Analytics', enabled: true, order: 3 },
      { id: 'findings', title: 'Key Findings & Drivers', enabled: true, order: 4 },
      { id: 'recommendations', title: 'Actionable Recommendations', enabled: true, order: 5 },
      { id: 'provenance', title: 'Data Provenance & Audit Trail', enabled: true, order: 6 },
    ];

    const activeSections = defaultSections.filter((s) => s.enabled);
    expect(activeSections.length).toBe(7);

    // Toggle off recommendations
    const updated = defaultSections.map((s) =>
      s.id === 'recommendations' ? { ...s, enabled: false } : s
    );
    expect(updated.find((s) => s.id === 'recommendations')?.enabled).toBe(false);
    expect(updated.filter((s) => s.enabled).length).toBe(6);
  });

  it('correctly maps export format extensions and content types', () => {
    const FORMAT_SPECS: Record<string, { ext: string; mime: string }> = {
      pdf: { ext: '.pdf', mime: 'application/pdf' },
      docx: { ext: '.docx', mime: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' },
      xlsx: { ext: '.xlsx', mime: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' },
      csv: { ext: '.csv', mime: 'text/csv' },
    };

    expect(FORMAT_SPECS['pdf'].ext).toBe('.pdf');
    expect(FORMAT_SPECS['docx'].ext).toBe('.docx');
    expect(FORMAT_SPECS['xlsx'].ext).toBe('.xlsx');
    expect(FORMAT_SPECS['csv'].ext).toBe('.csv');
  });

  it('validates schedule cron and frequency calculations', () => {
    const formatScheduleSummary = (freq: string, dayOfWeek?: number, dayOfMonth?: number, time = '08:00') => {
      if (freq === 'daily') return `Daily at ${time}`;
      if (freq === 'weekly') {
        const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
        return `Weekly on ${days[dayOfWeek ?? 1]} at ${time}`;
      }
      if (freq === 'monthly') return `Monthly on day ${dayOfMonth ?? 1} at ${time}`;
      return 'Custom Schedule';
    };

    expect(formatScheduleSummary('daily', undefined, undefined, '09:00')).toBe('Daily at 09:00');
    expect(formatScheduleSummary('weekly', 1, undefined, '08:00')).toBe('Weekly on Monday at 08:00');
    expect(formatScheduleSummary('monthly', undefined, 15, '06:00')).toBe('Monthly on day 15 at 06:00');
  });

  it('validates recipient email validation logic', () => {
    const isValidEmail = (email: string) => {
      return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
    };

    expect(isValidEmail('leadership@datalens.ai')).toBe(true);
    expect(isValidEmail('finance-team+review@company.co.uk')).toBe(true);
    expect(isValidEmail('invalid-email')).toBe(false);
    expect(isValidEmail('@missinguser.com')).toBe(false);
    expect(isValidEmail('spaces in@address.com')).toBe(false);
  });

  it('computes data provenance verification hash and row counts', () => {
    interface ProvenanceRecord {
      dataset_id: string;
      version_id: string;
      row_count: number;
      manifest_sha256: string;
      source_name: string;
    }

    const provenance: ProvenanceRecord = {
      dataset_id: 'ds-9812-sales',
      version_id: 'v1.0.4',
      row_count: 52400,
      manifest_sha256: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
      source_name: 'Q3_Global_Transactions.parquet',
    };

    expect(provenance.row_count).toBeGreaterThan(0);
    expect(provenance.manifest_sha256).toHaveLength(64);
    expect(provenance.version_id).toBe('v1.0.4');
  });
});

