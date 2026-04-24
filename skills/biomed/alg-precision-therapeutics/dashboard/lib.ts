import { execFile } from 'child_process';
import { promisify } from 'util';
import path from 'path';

const execFileAsync = promisify(execFile);

const PROJECT_ROOT = process.env.PROJECT_ROOT || path.resolve(process.cwd());

const APT_SCRIPT = path.join(
  PROJECT_ROOT,
  '.claude/skills/alg-precision-therapeutics/alg_precision_therapeutics.py'
);

async function runApt(args: string[]): Promise<unknown> {
  const { stdout } = await execFileAsync(
    'uv',
    ['run', 'python', APT_SCRIPT, ...args],
    { cwd: PROJECT_ROOT, maxBuffer: 10 * 1024 * 1024 }
  );
  return JSON.parse(stdout);
}

export async function listInvestigations() {
  return runApt(['list-investigations']);
}

export async function showDisease(mondoId: string) {
  return runApt(['show-disease', '--mondo-id', mondoId]);
}

export async function showMechanisms(mondoId: string) {
  return runApt(['show-mechanisms', '--mondo-id', mondoId]);
}

export async function showPhenome(mondoId: string) {
  return runApt(['show-phenome', '--mondo-id', mondoId]);
}

export async function showGenes(mondoId: string) {
  return runApt(['show-genes', '--mondo-id', mondoId]);
}

export async function showGaps(mondoId: string) {
  return runApt(['show-gaps', '--mondo-id', mondoId]);
}

export async function showEvidence(mechanismId: string) {
  return runApt(['show-evidence', '--mechanism-id', mechanismId]);
}

export async function searchEvidence(query: string, mondoId: string) {
  const args = ['search-evidence', '--query', query];
  if (mondoId) args.push('--mondo-id', mondoId);
  return runApt(args);
}
