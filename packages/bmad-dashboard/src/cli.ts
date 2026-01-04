import { Command } from 'commander';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const packageJson = JSON.parse(
  readFileSync(join(__dirname, '..', 'package.json'), 'utf-8')
) as { version: string };

const program = new Command();

program
  .name('bmad-dashboard')
  .description('TUI dashboard for multi-DevPod BMAD orchestration')
  .version(packageJson.version);

program.parse();
