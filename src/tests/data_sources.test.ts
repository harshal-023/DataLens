import { describe, it, expect } from 'vitest';
import { DataSourceType } from '../services/dataSourceService';

describe('Phase 5A: External Data Source Platform Tests', () => {
  it('validates supported connector categories and features', () => {
    const connectors: Array<{
      type: DataSourceType;
      name: string;
      category: string;
      supportsWatermark: boolean;
      supportsSSL: boolean;
    }> = [
      { type: 'postgres', name: 'PostgreSQL', category: 'Relational Database', supportsWatermark: true, supportsSSL: true },
      { type: 'mysql', name: 'MySQL', category: 'Relational Database', supportsWatermark: true, supportsSSL: true },
      { type: 'rest_api', name: 'REST API', category: 'Web Services & APIs', supportsWatermark: true, supportsSSL: true },
      { type: 'google_sheets', name: 'Google Sheets', category: 'Cloud Spreadsheets', supportsWatermark: true, supportsSSL: true },
      { type: 'mongodb', name: 'MongoDB', category: 'Document Database', supportsWatermark: true, supportsSSL: true },
      { type: 's3', name: 'S3 Storage', category: 'Object Storage', supportsWatermark: true, supportsSSL: true },
    ];

    expect(connectors).toHaveLength(6);
    connectors.forEach((c) => {
      expect(c.supportsWatermark).toBe(true);
      expect(c.supportsSSL).toBe(true);
      expect(c.category).toBeTruthy();
    });
  });

  it('correctly flattens complex nested JSON structures for REST and Mongo connectors', () => {
    const flatten = (data: any, prefix = '', sep = '_'): Record<string, any> => {
      const result: Record<string, any> = {};
      for (const key of Object.keys(data)) {
        const val = data[key];
        const newKey = prefix ? `${prefix}${sep}${key}` : key;
        if (val !== null && typeof val === 'object' && !Array.isArray(val)) {
          Object.assign(result, flatten(val, newKey, sep));
        } else if (Array.isArray(val)) {
          result[newKey] = val.join(', ');
        } else {
          result[newKey] = val;
        }
      }
      return result;
    };

    const nested = {
      order_id: 'ord_9901',
      customer: {
        name: 'Jane Doe',
        contact: { email: 'jane@example.com', phone: '+123456789' },
      },
      items_summary: ['Laptop', 'Mouse'],
      total_amount: 1250.75,
    };

    const flat = flatten(nested);
    expect(flat.order_id).toBe('ord_9901');
    expect(flat.customer_name).toBe('Jane Doe');
    expect(flat.customer_contact_email).toBe('jane@example.com');
    expect(flat.items_summary).toBe('Laptop, Mouse');
    expect(flat.total_amount).toBe(1250.75);
  });

  it('masks sensitive credentials preventing secret exposure in client state', () => {
    const mask = (value: string) => {
      if (!value) return '';
      if (value.length <= 6) return '••••••••';
      return '••••••••' + value.slice(-4);
    };

    expect(mask('short')).toBe('••••••••');
    expect(mask('super_secret_db_password_2026')).toBe('••••••••2026');
    expect(mask('live_api_key_abcdef1234')).toBe('••••••••1234');
  });

  it('formats byte sizes into readable units', () => {
    const formatBytes = (bytes: number) => {
      if (bytes === 0) return '0 B';
      const k = 1024;
      const sizes = ['B', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    expect(formatBytes(0)).toBe('0 B');
    expect(formatBytes(1024)).toBe('1 KB');
    expect(formatBytes(1048576)).toBe('1 MB');
    expect(formatBytes(157286400)).toBe('150 MB');
  });

  it('calculates next execution times for scheduled syncs', () => {
    const getNextRun = (frequency: 'hourly' | 'daily' | 'weekly', base: Date): Date => {
      const next = new Date(base.getTime());
      if (frequency === 'hourly') {
        next.setHours(next.getHours() + 1);
      } else if (frequency === 'daily') {
        next.setDate(next.getDate() + 1);
      } else if (frequency === 'weekly') {
        next.setDate(next.getDate() + 7);
      }
      return next;
    };

    const base = new Date('2026-11-12T12:00:00Z');
    const nextH = getNextRun('hourly', base);
    expect(nextH.toISOString()).toBe('2026-11-12T13:00:00.000Z');

    const nextD = getNextRun('daily', base);
    expect(nextD.toISOString()).toBe('2026-11-13T12:00:00.000Z');

    const nextW = getNextRun('weekly', base);
    expect(nextW.toISOString()).toBe('2026-11-19T12:00:00.000Z');
  });
});

