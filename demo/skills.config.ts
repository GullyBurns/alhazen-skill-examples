// Registry of skills installed in this demo app.
// Updated by `make demo-sync` when skills are added.

export interface SkillConfig {
  name: string;
  description: string;
  path: string;
  category: string;
}

export const installedSkills: SkillConfig[] = [
  {
    name: "Job Hunt",
    description: "Track job applications, analyze positions, identify skill gaps, and plan your job search strategy.",
    path: "/jobhunt",
    category: "demo",
  },
  {
    name: "Tech Recon",
    description: "Systematically investigate external software systems, libraries, frameworks, and computational tools.",
    path: "/techrecon",
    category: "demo",
  },
];
