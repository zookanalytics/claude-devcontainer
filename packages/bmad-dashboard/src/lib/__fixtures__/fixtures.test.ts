import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parse } from 'yaml';

const FIXTURES_DIR = path.dirname(fileURLToPath(import.meta.url));

function loadFixture(filename: string): string {
  return readFileSync(path.join(FIXTURES_DIR, filename), 'utf8');
}

describe('YAML fixtures', () => {
  describe('valid-sprint-status.yaml', () => {
    it('parses successfully', () => {
      const content = loadFixture('valid-sprint-status.yaml');
      const parsed = parse(content);

      expect(parsed).toBeDefined();
      expect(parsed.project).toBe('test-project');
      expect(parsed.project_key).toBe('test-dashboard');
      expect(parsed.development_status).toBeDefined();
    });

    it('has expected structure', () => {
      const content = loadFixture('valid-sprint-status.yaml');
      const parsed = parse(content);

      expect(parsed.development_status['epic-1']).toBe('done');
      expect(parsed.development_status['epic-2']).toBe('in-progress');
      expect(parsed.development_status['2-2-feature-beta']).toBe('in-progress');
    });
  });

  describe('valid-worker-state.yaml', () => {
    it('parses successfully', () => {
      const content = loadFixture('valid-worker-state.yaml');
      const parsed = parse(content);

      expect(parsed).toBeDefined();
      expect(parsed.worker_id).toBe('devpod-worker-1');
      expect(parsed.status).toBe('working');
    });

    it('has assignment and heartbeat', () => {
      const content = loadFixture('valid-worker-state.yaml');
      const parsed = parse(content);

      expect(parsed.assignment).toBeDefined();
      expect(parsed.assignment.story_id).toBe('2-2-feature-beta');
      expect(parsed.heartbeat).toBeDefined();
      expect(parsed.heartbeat.last_update).toBeDefined();
    });

    it('has progress tracking', () => {
      const content = loadFixture('valid-worker-state.yaml');
      const parsed = parse(content);

      expect(parsed.progress).toBeDefined();
      expect(parsed.progress.tasks_total).toBe(5);
      expect(parsed.progress.tasks_completed).toBe(3);
      expect(parsed.progress.percentage).toBe(60);
    });
  });

  describe('malformed.yaml', () => {
    it('throws parse error for tab character', () => {
      const content = loadFixture('malformed.yaml');

      expect(() => parse(content)).toThrow(/tab/i);
    });
  });

  describe('partial-state.yaml', () => {
    it('parses successfully', () => {
      const content = loadFixture('partial-state.yaml');
      const parsed = parse(content);

      expect(parsed).toBeDefined();
      expect(parsed.worker_id).toBe('devpod-worker-minimal');
      expect(parsed.status).toBe('idle');
    });

    it('has minimal required fields', () => {
      const content = loadFixture('partial-state.yaml');
      const parsed = parse(content);

      expect(parsed.assignment.story_id).toBe('1-1-basic-task');
      expect(parsed.heartbeat.last_update).toBeDefined();
    });

    it('is missing optional fields', () => {
      const content = loadFixture('partial-state.yaml');
      const parsed = parse(content);

      expect(parsed.progress).toBeUndefined();
      expect(parsed.session).toBeUndefined();
      expect(parsed.pending_questions).toBeUndefined();
      expect(parsed.assignment.story_title).toBeUndefined();
    });
  });
});
