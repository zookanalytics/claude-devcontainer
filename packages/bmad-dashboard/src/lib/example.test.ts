import { formatDevPodStatus, isActiveStatus } from './example.js';

describe('formatDevPodStatus', () => {
  it('formats idle status', () => {
    expect(formatDevPodStatus('idle')).toBe('Idle');
  });

  it('formats running status', () => {
    expect(formatDevPodStatus('running')).toBe('Running');
  });

  it('formats stale status', () => {
    expect(formatDevPodStatus('stale')).toBe('Stale');
  });

  it('formats unknown status', () => {
    expect(formatDevPodStatus('unknown')).toBe('Unknown');
  });
});

describe('isActiveStatus', () => {
  it('returns true for running status', () => {
    expect(isActiveStatus('running')).toBe(true);
  });

  it('returns false for idle status', () => {
    expect(isActiveStatus('idle')).toBe(false);
  });

  it('returns false for stale status', () => {
    expect(isActiveStatus('stale')).toBe(false);
  });

  it('returns false for unknown status', () => {
    expect(isActiveStatus('unknown')).toBe(false);
  });
});
