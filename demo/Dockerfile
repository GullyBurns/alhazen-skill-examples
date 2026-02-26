# Alhazen Skill Examples Demo — Dockerfile
# Context: repo root (alhazen-skill-examples/)
# Build: cd demo && docker compose up

# ==============================================================================
# Stage 1: Python + uv setup
# ==============================================================================
FROM python:3.11-slim AS python-base
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# ==============================================================================
# Stage 2: Install Python deps for jobhunt skill
# ==============================================================================
FROM python-base AS python-deps
WORKDIR /app/skills/demo/jobhunt
COPY skills/demo/jobhunt/pyproject.toml ./
RUN uv sync --no-dev

# ==============================================================================
# Stage 3: Node.js build
# ==============================================================================
FROM node:20-slim AS node-builder
WORKDIR /app/demo

# Install npm deps
COPY demo/package*.json ./
RUN npm ci

# Copy Next.js config and source
COPY demo/next.config.ts demo/components.json demo/postcss.config.mjs ./
COPY demo/tsconfig.json ./
COPY demo/eslint.config.mjs ./
COPY demo/skills.config.ts ./
COPY demo/src ./src

# Resolve symlinks: copy assembled skill dashboard code
# (demo-sync creates symlinks; docker build needs the real files)
COPY skills/demo/jobhunt/dashboard/components ./src/components/jobhunt
COPY skills/demo/jobhunt/dashboard/routes ./src/app/api/jobhunt
COPY skills/demo/jobhunt/dashboard/pages ./src/app/(jobhunt)
COPY skills/demo/jobhunt/dashboard/lib.ts ./src/lib/jobhunt.ts

RUN npm run build

# ==============================================================================
# Stage 4: Final runtime
# ==============================================================================
FROM python:3.11-slim AS runner

# Install Node.js and curl (for uv)
RUN apt-get update && \
    apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Copy Python environment
COPY --from=python-deps /app/skills/demo/jobhunt/.venv ./skills/demo/jobhunt/.venv
COPY skills/demo/jobhunt/pyproject.toml ./skills/demo/jobhunt/

# Copy Python scripts
COPY skills/demo/jobhunt/jobhunt.py ./skills/demo/jobhunt/
COPY skills/demo/jobhunt/job_forager.py ./skills/demo/jobhunt/
COPY skills/demo/jobhunt/job_triage.py ./skills/demo/jobhunt/

# Copy Node.js build
COPY --from=node-builder /app/demo/.next ./.next
COPY --from=node-builder /app/demo/public ./public
COPY --from=node-builder /app/demo/package*.json ./
COPY --from=node-builder /app/demo/node_modules ./node_modules

# Environment
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV SKILL_ROOT=/app/skills/demo/jobhunt
ENV TYPEDB_HOST=typedb
ENV TYPEDB_PORT=1729
ENV TYPEDB_DATABASE=alhazen_notebook

EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["npm", "start"]
