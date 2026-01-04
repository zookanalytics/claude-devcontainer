import { Command } from 'commander';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const currentDirectory = path.dirname(fileURLToPath(import.meta.url));
const packageJson = JSON.parse(
  readFileSync(path.join(currentDirectory, '..', 'package.json'), 'utf8'),
) as { version: string };

const program = new Command();

program
  .name('bmad-dashboard')
  .description('TUI dashboard for multi-DevPod BMAD orchestration')
  .version(packageJson.version);

program.parse();
