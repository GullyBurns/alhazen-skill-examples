'use client';

import { useState, useEffect, useMemo, use } from 'react';
import Link from 'next/link';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import {
  ArrowLeft,
  BookOpen,
  Building2,
  MapPin,
  DollarSign,
  ExternalLink,
  RefreshCw,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Calendar,
  User,
  FileText,
  Target,
  MessageSquare,
  Lightbulb,
  ClipboardList,
  LayoutDashboard,
} from 'lucide-react';

// --- Helpers ---

function unesc(s: string | undefined | null): string {
  let text = (s ?? '').replace(/\\n/g, '\n');
  text = text.replace(
    /(?<!\]\()(?<!\()(?<![<"'])(https?:\/\/[^\s)>\]"']+)/g,
    '[$1]($1)'
  );
  text = text.replace(
    /(?<!\]\()(?<!\()(?<![<"'])(?:^|(?<=\s))(\/(?:tech-recon|jobhunt|dismech|agentic-memory|coach|skill-builder)\/[^\s)>\]"']+)/gm,
    '[$1]($1)'
  );
  return text;
}

function getValue(attr: unknown): string | null {
  if (attr === null || attr === undefined) return null;
  if (typeof attr === 'string') {
    return attr.replace(/\\\\n/g, '\n').replace(/\\n/g, '\n')
              .replace(/\\\\t/g, '\t').replace(/\\t/g, '\t');
  }
  if (typeof attr === 'number') return String(attr);
  if (Array.isArray(attr) && attr.length > 0 && attr[0]?.value !== undefined) {
    return getValue(attr[0].value);
  }
  return null;
}

function getNumber(attr: unknown): number | null {
  if (attr === null || attr === undefined) return null;
  if (typeof attr === 'number') return attr;
  if (typeof attr === 'string') { const n = Number(attr); return isNaN(n) ? null : n; }
  if (Array.isArray(attr) && attr.length > 0 && attr[0]?.value !== undefined) {
    return getNumber(attr[0].value);
  }
  return null;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function getNoteType(n: any): string {
  const raw = typeof n.type === 'string' ? n.type : n.type?.label;
  return (raw || '').replace('jhunt-', '').replace('-note', '') || 'general';
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function formatShortDate(dateStr: string | null): string {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// --- Constants ---

const NOTE_ICONS: Record<string, React.ReactNode> = {
  'fit-analysis': <Target className="w-4 h-4" />,
  'strategy': <Lightbulb className="w-4 h-4" />,
  'interaction': <User className="w-4 h-4" />,
  'research': <FileText className="w-4 h-4" />,
  'interview': <MessageSquare className="w-4 h-4" />,
  'skill-gap': <AlertCircle className="w-4 h-4" />,
  'application': <ClipboardList className="w-4 h-4" />,
  'general': <FileText className="w-4 h-4" />,
};

const NOTE_LABELS: Record<string, string> = {
  'fit-analysis': 'Fit Analysis',
  'strategy': 'Strategy',
  'interaction': 'Interactions',
  'research': 'Research',
  'interview': 'Interview',
  'skill-gap': 'Skill Gaps',
  'application': 'Application',
  'general': 'General',
};

const SECTION_ORDER = [
  'fit-analysis', 'research', 'strategy', 'interaction',
  'interview', 'skill-gap', 'application', 'general',
];

const PRIORITY_COLORS: Record<string, string> = {
  high: 'bg-red-500/20 text-red-400 border-red-500/30',
  medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  low: 'bg-green-500/20 text-green-400 border-green-500/30',
};

const STATUS_COLORS: Record<string, string> = {
  researching: 'bg-slate-500/20 text-slate-300 border-slate-500/30',
  applied: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  'phone-screen': 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  interviewing: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  offer: 'bg-green-500/20 text-green-400 border-green-500/30',
  rejected: 'bg-red-500/20 text-red-400 border-red-500/30',
  withdrawn: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
};

// --- Page ---

interface PositionPageProps {
  params: Promise<{ id: string }>;
}

export default function PositionPage({ params }: PositionPageProps) {
  const { id } = use(params);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNote, setSelectedNote] = useState<string>('overview');

  useEffect(() => {
    async function fetchPosition() {
      setLoading(true);
      setError(null);
      try {
        const [posRes, skillsRes] = await Promise.all([
          fetch(`/api/jobhunt/position/${id}`),
          fetch('/api/jobhunt/skills'),
        ]);
        if (!posRes.ok) throw new Error('Failed to fetch position');
        const json = await posRes.json();
        if (skillsRes.ok) {
          const skillsData = await skillsRes.json();
          const mySkills: Record<string, string> = {};
          for (const s of (skillsData.skills ?? [])) {
            mySkills[s.name.toLowerCase()] = s.level;
          }
          if (json.requirements) {
            for (const req of json.requirements) {
              const skillName = req['jhunt-skill-name'] || req['slog-skill-name'] || '';
              req['_seeker_level'] = mySkills[skillName.toLowerCase()] || 'none';
            }
          }
        }
        setData(json);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    }
    fetchPosition();
  }, [id]);

  // Group and sort notes
  const groupedNotes = useMemo(() => {
    if (!data?.notes) return {};
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const groups: Record<string, any[]> = {};
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    for (const note of data.notes) {
      const type = getNoteType(note);
      if (!groups[type]) groups[type] = [];
      groups[type].push(note);
    }
    for (const g of Object.values(groups)) {
      g.sort((a, b) => {
        const da = getValue(a['created-at']) || '';
        const db = getValue(b['created-at']) || '';
        return db.localeCompare(da);
      });
    }
    return groups;
  }, [data?.notes]);

  // Find the selected note object
  const selectedNoteObj = useMemo(() => {
    if (selectedNote === 'overview' || !data?.notes) return null;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return data.notes.find((n: any) => n.id === selectedNote) || null;
  }, [selectedNote, data?.notes]);

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <RefreshCw className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-background p-8">
        <Link href="/jobhunt">
          <Button variant="ghost" className="mb-4">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Dashboard
          </Button>
        </Link>
        <div className="bg-destructive/10 text-destructive px-4 py-3 rounded-lg">
          <strong>Error:</strong> {error || 'Position not found'}
        </div>
      </div>
    );
  }

  const position = data.position;
  const company = data.company;
  const notes = data.notes || [];
  const requirements = data.requirements || [];
  const jobDescription = data.job_description;
  const tags = data.tags || [];
  const backgroundReading = data.background_reading || [];

  const title = getValue(position?.name) || 'Unknown Position';
  const url = getValue(position?.['jhunt-job-url']);
  const location = getValue(position?.location);
  const salary = getValue(position?.['jhunt-salary-range']);
  const remotePolicy = getValue(position?.['jhunt-remote-policy']);
  const priority = getValue(position?.['jhunt-priority-level']);

  const companyName = getValue(company?.name);
  const companyUrl = getValue(company?.['alh-company-url']);
  const companyDescription = getValue(company?.description);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const statusNote = notes.find((n: any) => getNoteType(n) === 'application');
  const status = getValue(statusNote?.['jhunt-application-status']) || 'researching';

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const fitNote = notes.find((n: any) => getNoteType(n) === 'fit-analysis');
  const fitScore = getNumber(fitNote?.['jhunt-fit-score']);
  const fitSummary = getValue(fitNote?.['jhunt-fit-summary']);

  return (
    <div className="h-screen flex flex-col">
      {/* Compact sticky header */}
      <header className="shrink-0 border-b border-border/50 bg-card/95 backdrop-blur-sm px-4 py-3">
        <div className="flex items-center gap-3">
          <Link href="/jobhunt">
            <Button variant="ghost" size="sm" className="hover:bg-primary/10">
              <ArrowLeft className="w-4 h-4" />
            </Button>
          </Link>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-lg font-bold text-foreground truncate">{title}</h1>
              {companyName && (
                <span className="text-muted-foreground text-sm">@ {companyName}</span>
              )}
            </div>
            <div className="flex items-center gap-2 flex-wrap mt-0.5">
              <Badge className={STATUS_COLORS[status]}>
                {status.replace('-', ' ')}
              </Badge>
              {priority && (
                <Badge className={PRIORITY_COLORS[priority]}>
                  {priority}
                </Badge>
              )}
              {fitScore !== null && (
                <Badge variant="outline">
                  <Target className="w-3 h-3 mr-1" />
                  {Math.round(fitScore * 100)}% fit
                </Badge>
              )}
              {salary && (
                <span className="text-xs text-muted-foreground flex items-center gap-1">
                  <DollarSign className="w-3 h-3" />{salary}
                </span>
              )}
              {location && (
                <span className="text-xs text-muted-foreground flex items-center gap-1">
                  <MapPin className="w-3 h-3" />{location}
                </span>
              )}
              {remotePolicy && (
                <span className="text-xs text-muted-foreground flex items-center gap-1">
                  <Building2 className="w-3 h-3" />{remotePolicy}
                </span>
              )}
            </div>
          </div>
          <div className="shrink-0 flex items-center gap-2">
            {url && (
              <a href={url} target="_blank" rel="noopener noreferrer">
                <Button variant="outline" size="sm">
                  <ExternalLink className="w-3 h-3 mr-1" />
                  Posting
                </Button>
              </a>
            )}
            {companyUrl && (
              <a href={companyUrl} target="_blank" rel="noopener noreferrer">
                <Button variant="ghost" size="sm">
                  <Building2 className="w-3 h-3 mr-1" />
                  Company
                </Button>
              </a>
            )}
          </div>
        </div>
      </header>

      {/* Main: sidebar + reading pane */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left nav */}
        <nav style={{ width: '256px', minWidth: '256px', maxWidth: '256px' }} className="shrink-0 border-r border-border/50 overflow-y-auto overflow-x-hidden p-3 space-y-1 bg-card/30">
          {/* Overview */}
          <button
            onClick={() => setSelectedNote('overview')}
            className={`w-full text-left px-3 py-2 rounded-md text-sm font-medium flex items-center gap-2 transition-colors ${
              selectedNote === 'overview'
                ? 'bg-accent text-accent-foreground'
                : 'text-muted-foreground hover:bg-muted hover:text-foreground'
            }`}
          >
            <LayoutDashboard className="w-4 h-4" />
            Overview
          </button>

          <Separator className="my-2" />

          {/* Note sections */}
          {SECTION_ORDER.map(type => {
            const typeNotes = groupedNotes[type];
            if (!typeNotes?.length) return null;
            return (
              <details key={type} open className="group">
                <summary className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-muted-foreground cursor-pointer hover:text-foreground select-none list-none [&::-webkit-details-marker]:hidden min-w-0">
                  <span className="text-xs transition-transform group-open:rotate-90">&#9656;</span>
                  {NOTE_ICONS[type] || <FileText className="w-4 h-4" />}
                  <span>{NOTE_LABELS[type] || type}</span>
                  <Badge variant="secondary" className="ml-auto text-[10px] px-1.5 py-0">
                    {typeNotes.length}
                  </Badge>
                </summary>
                <div className="ml-3 mt-0.5 space-y-0.5 border-l border-border/30 pl-2 min-w-0">
                  {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                  {typeNotes.map((note: any) => {
                    const noteId = note.id;
                    const noteName = getValue(note.name) || 'Untitled';
                    const createdAt = getValue(note['created-at']);
                    const isSelected = selectedNote === noteId;
                    return (
                      <button
                        key={noteId}
                        onClick={() => setSelectedNote(noteId)}
                        className={`w-full min-w-0 text-left px-2.5 py-1.5 rounded text-xs transition-colors overflow-hidden ${
                          isSelected
                            ? 'bg-accent text-accent-foreground'
                            : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                        }`}
                      >
                        <div className="truncate font-medium">
                          {noteName}
                          {createdAt && (
                            <span className="text-[10px] opacity-50 font-normal ml-1">({formatShortDate(createdAt)})</span>
                          )}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </details>
            );
          })}

          {/* Job Description nav item */}
          {jobDescription && (
            <>
              <Separator className="my-2" />
              <button
                onClick={() => setSelectedNote('job-description')}
                className={`w-full text-left px-3 py-2 rounded-md text-sm flex items-center gap-2 transition-colors ${
                  selectedNote === 'job-description'
                    ? 'bg-accent text-accent-foreground'
                    : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                }`}
              >
                <FileText className="w-4 h-4" />
                Job Description
              </button>
            </>
          )}
        </nav>

        {/* Reading pane */}
        <main className="flex-1 overflow-y-auto p-6">
          <div className="max-w-4xl">
            {selectedNote === 'overview' && (
              <OverviewPane
                fitNote={fitNote}
                fitScore={fitScore}
                fitSummary={fitSummary}
                requirements={requirements}
                company={company}
                companyName={companyName}
                companyUrl={companyUrl}
                companyDescription={companyDescription}
                tags={tags}
                backgroundReading={backgroundReading}
                location={location}
                salary={salary}
                remotePolicy={remotePolicy}
              />
            )}

            {selectedNote === 'job-description' && jobDescription && (
              <div>
                <h2 className="text-xl font-semibold mb-4">Job Description</h2>
                <Separator className="mb-4" />
                <pre className="whitespace-pre-wrap text-sm bg-muted p-4 rounded-lg overflow-auto">
                  {getValue(jobDescription.content)}
                </pre>
              </div>
            )}

            {selectedNote !== 'overview' && selectedNote !== 'job-description' && selectedNoteObj && (
              <NotePane note={selectedNoteObj} />
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

// --- Overview Pane ---

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function OverviewPane({ fitNote, fitScore, fitSummary, requirements, company, companyName, companyUrl, companyDescription, tags, backgroundReading, location, salary, remotePolicy }: any) {
  return (
    <div className="space-y-6">
      {/* Quick Info */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {location && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-muted/50">
            <MapPin className="w-4 h-4 text-muted-foreground shrink-0" />
            <div className="min-w-0">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Location</p>
              <p className="text-sm font-medium truncate">{location}</p>
            </div>
          </div>
        )}
        {salary && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-muted/50">
            <DollarSign className="w-4 h-4 text-muted-foreground shrink-0" />
            <div className="min-w-0">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Salary</p>
              <p className="text-sm font-medium truncate">{salary}</p>
            </div>
          </div>
        )}
        {remotePolicy && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-muted/50">
            <Building2 className="w-4 h-4 text-muted-foreground shrink-0" />
            <div className="min-w-0">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Remote</p>
              <p className="text-sm font-medium truncate">{remotePolicy}</p>
            </div>
          </div>
        )}
        {fitScore !== null && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-muted/50">
            <Target className="w-4 h-4 text-muted-foreground shrink-0" />
            <div>
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Fit Score</p>
              <p className="text-sm font-medium">{Math.round(fitScore * 100)}%</p>
            </div>
          </div>
        )}
      </div>

      {/* Tags */}
      {tags.length > 0 && (
        <div className="flex items-center gap-2 flex-wrap">
          {tags.map((tag: string) => (
            <Badge key={tag} variant="outline" className="text-xs">{tag}</Badge>
          ))}
        </div>
      )}

      {/* Fit Analysis */}
      {fitNote && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="w-5 h-5" />
              Fit Analysis
              {fitScore !== null && (
                <Badge variant="outline" className="ml-auto">
                  {Math.round(fitScore * 100)}%
                </Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {fitSummary && (
              <p className="text-sm font-medium mb-4">{fitSummary}</p>
            )}
            {getValue(fitNote?.content) && (
              <div className="prose prose-sm max-w-none dark:prose-invert">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {unesc(getValue(fitNote?.content))}
                </ReactMarkdown>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Requirements */}
      {requirements.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Requirements ({requirements.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
              {requirements.map((req: any, idx: number) => {
                const skill = getValue(req['jhunt-skill-name']) || getValue(req['slog-skill-name']);
                const level = getValue(req['jhunt-skill-level']) || getValue(req['requirement-level']);
                const yourLevel = req['_seeker_level'] || getValue(req['jhunt-your-level']) || 'none';
                const content = getValue(req.content);

                const levelValue: Record<string, number> = { none: 0, aware: 1, learning: 1, practiced: 2, some: 2, expert: 3, strong: 3 };
                const threshold: Record<string, number> = { required: 2, preferred: 1, 'nice-to-have': 0 };
                const myVal = levelValue[yourLevel] ?? 0;
                const reqVal = threshold[level ?? 'required'] ?? 1;
                const match = myVal >= reqVal ? 'match' : myVal > 0 ? 'partial' : 'gap';

                return (
                  <div key={idx} className="flex items-start gap-3 p-3 rounded-lg bg-muted/50">
                    {match === 'match' && <CheckCircle2 className="w-5 h-5 text-green-500 mt-0.5" />}
                    {match === 'partial' && <AlertCircle className="w-5 h-5 text-yellow-500 mt-0.5" />}
                    {match === 'gap' && <XCircle className="w-5 h-5 text-red-500 mt-0.5" />}
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{skill}</span>
                        <Badge variant="outline" className="text-xs">{level}</Badge>
                        {yourLevel && (
                          <Badge variant="secondary" className="text-xs">You: {yourLevel}</Badge>
                        )}
                      </div>
                      {content && (
                        <p className="text-sm text-muted-foreground mt-1">{content}</p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Company */}
      {company && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Building2 className="w-5 h-5" />
              About {companyName}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {companyDescription && (
              <div className="prose prose-sm max-w-none dark:prose-invert">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {unesc(companyDescription)}
                </ReactMarkdown>
              </div>
            )}
            {companyUrl && (
              <a href={companyUrl} target="_blank" rel="noopener noreferrer"
                 className="text-primary hover:underline text-sm flex items-center gap-1 mt-2">
                <ExternalLink className="w-3 h-3" />{companyUrl}
              </a>
            )}
          </CardContent>
        </Card>
      )}

      {/* Background Reading */}
      {backgroundReading.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BookOpen className="w-5 h-5" />
              Background Reading
              <Badge variant="secondary" className="ml-auto">{backgroundReading.length}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
            {backgroundReading.map((col: any, idx: number) => {
              const colName = getValue(col['collection-name']) || col['collection-name'];
              const colDesc = getValue(col.description) || col.description;
              return (
                <div key={idx} className="p-3 rounded-lg bg-muted/50">
                  <Link
                    href={`/jobhunt/collection/${col['collection-id']}`}
                    className="font-medium text-sm text-cyan-400 font-semibold underline underline-offset-2 hover:text-blue-400 transition-colors"
                  >
                    {colName}
                  </Link>
                  {colDesc && (
                    <p className="text-xs text-muted-foreground mt-1">{colDesc}</p>
                  )}
                </div>
              );
            })}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// --- Note Pane ---

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function NotePane({ note }: { note: any }) {
  const content = getValue(note.content);
  const createdAt = getValue(note['created-at']);
  const noteName = getValue(note.name) || 'Untitled';
  const noteType = getNoteType(note);
  const interactionType = getValue(note['alh-interaction-type']);
  const interactionDate = getValue(note['alh-interaction-date']);
  const interviewDate = getValue(note['jhunt-interview-date']);

  return (
    <div>
      {/* Note header */}
      <div className="mb-6">
        <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
          {NOTE_ICONS[noteType] || <FileText className="w-4 h-4" />}
          <Badge variant="outline" className="text-xs capitalize">
            {NOTE_LABELS[noteType] || noteType}
          </Badge>
          {interactionType && (
            <Badge variant="secondary" className="text-xs">{interactionType}</Badge>
          )}
          {createdAt && (
            <span className="flex items-center gap-1 ml-auto">
              <Calendar className="w-3 h-3" />
              {formatDate(createdAt)}
            </span>
          )}
        </div>
        <h2 className="text-xl font-semibold">{noteName}</h2>
        {(interactionDate || interviewDate) && (
          <p className="text-sm text-muted-foreground mt-1">
            {interactionDate && <>Event date: {formatDate(interactionDate)}</>}
            {interviewDate && <>Interview date: {formatDate(interviewDate)}</>}
          </p>
        )}
      </div>
      <Separator className="mb-6" />

      {/* Note content */}
      {content ? (
        <div className="prose prose-sm max-w-none dark:prose-invert">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {unesc(content)}
          </ReactMarkdown>
        </div>
      ) : (
        <p className="text-muted-foreground italic">No content</p>
      )}
    </div>
  );
}
