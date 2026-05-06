import { execFile } from 'child_process';
import { promisify } from 'util';
import path from 'path';

const execFileAsync = promisify(execFile);

// COACH_SKILL_ROOT: absolute path to the coach skill directory (standalone mode)
// PROJECT_ROOT: absolute path to skillful-alhazen root (installed mode)
const SKILL_ROOT = process.env.COACH_SKILL_ROOT;
const PROJECT_ROOT = process.env.PROJECT_ROOT || path.resolve(process.cwd());

const COACH_SCRIPT = SKILL_ROOT
  ? path.join(SKILL_ROOT, 'coach.py')
  : path.join(PROJECT_ROOT, '.claude/skills/coach/coach.py');

const CWD = SKILL_ROOT || PROJECT_ROOT;

async function runCoach(args: string[]): Promise<Record<string, unknown>> {
  const { stdout } = await execFileAsync(
    'uv',
    ['run', 'python', COACH_SCRIPT, ...args],
    {
      cwd: CWD,
      env: { ...process.env, TYPEDB_DATABASE: 'alhazen_notebook' },
      maxBuffer: 10 * 1024 * 1024,
    }
  );
  return JSON.parse(stdout);
}

// --- Pipeline ---

export async function getLatestMetrics(metric?: string) {
  const args = ['latest'];
  if (metric) args.push('--metric', metric);
  return runCoach(args);
}

export async function getTrends() {
  return runCoach(['trends']);
}

export async function getPipelineStatus() {
  return runCoach(['pipeline-status']);
}

// --- Sleep ---

export async function getSleepSummary(days = 7) {
  return runCoach(['sleep-summary', '--days', String(days)]);
}

// --- Workouts ---

export async function getWorkoutHistory(limit = 10) {
  return runCoach(['workout-history', '--limit', String(limit)]);
}

// --- Metric Detail ---

export async function getMetricHistory(type: string, days = 30) {
  return runCoach(['show-metric', '--type', type, '--days', String(days)]);
}

// --- Goals ---

export async function getGoals(status?: string) {
  const args = ['list-goals'];
  if (status) args.push('--status', status);
  return runCoach(args);
}

// --- Appointments ---

export async function getAppointments() {
  return runCoach(['list-appointments']);
}

// --- Providers ---

export async function getProviders() {
  return runCoach(['list-providers']);
}

// --- Recommendations ---

export async function getRecommendations() {
  return runCoach(['list-recommendations']);
}

// --- Profile ---

export async function getProfile() {
  return runCoach(['show-profile']);
}
