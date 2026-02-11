import { describe, it, expect } from 'vitest';
import { cn, formatCurrency, formatNumber, formatPercent, percentChange, debounce } from '../lib/utils';

describe('cn utility', () => {
  it('merges class names correctly', () => {
    expect(cn('foo', 'bar')).toBe('foo bar');
    expect(cn('foo', undefined, 'bar')).toBe('foo bar');
    expect(cn('foo', null, 'bar')).toBe('foo bar');
  });

  it('handles conditional classes', () => {
    expect(cn('base', true && 'active')).toBe('base active');
    expect(cn('base', false && 'active')).toBe('base');
  });

  it('merges tailwind classes correctly', () => {
    expect(cn('px-2 py-1', 'px-4')).toBe('py-1 px-4');
  });
});

describe('formatCurrency', () => {
  it('formats USD by default', () => {
    expect(formatCurrency(1234.56)).toBe('$1,234.56');
    expect(formatCurrency(1000000)).toBe('$1,000,000.00');
  });

  it('handles zero', () => {
    expect(formatCurrency(0)).toBe('$0.00');
  });

  it('formats with different locales', () => {
    expect(formatCurrency(1234.56, 'EUR', 'de-DE')).toContain('1.234,56');
  });
});

describe('formatNumber', () => {
  it('formats integers', () => {
    expect(formatNumber(1234567)).toBe('1,234,567');
  });

  it('handles small numbers', () => {
    expect(formatNumber(42)).toBe('42');
  });
});

describe('formatPercent', () => {
  it('formats decimals as percentages', () => {
    expect(formatPercent(0.1234)).toBe('12.3%');
    expect(formatPercent(0.5)).toBe('50.0%');
    expect(formatPercent(1)).toBe('100.0%');
  });

  it('handles zero', () => {
    expect(formatPercent(0)).toBe('0.0%');
  });
});

describe('percentChange', () => {
  it('calculates positive change', () => {
    expect(percentChange(100, 120)).toBeCloseTo(20);
  });

  it('calculates negative change', () => {
    expect(percentChange(100, 80)).toBeCloseTo(-20);
  });

  it('handles zero old value', () => {
    expect(percentChange(0, 100)).toBe(0);
  });
});

describe('debounce', () => {
  it('debounces function calls', async () => {
    let count = 0;
    const increment = debounce(() => count++, 50);
    
    increment();
    increment();
    increment();
    
    expect(count).toBe(0);
    
    await new Promise(resolve => setTimeout(resolve, 100));
    
    expect(count).toBe(1);
  });
});
