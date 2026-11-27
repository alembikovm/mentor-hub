# Mentor Hub

Mentors publish learning roadmaps; mentees follow them and submit screenshots of their solutions;
a LangGraph + Claude vision pipeline gives every submission a first-pass review before the mentor looks.

```
web/  Next.js 16 (App Router, Cache Components) + Clerk + Tailwind 4
api/  FastAPI + SQLAlchemy (async) + LangGraph + Anthropic SDK
```

## Features

- **Clerk auth, two roles.** After sign-up a user picks *mentor* or *mentee* (stored in the API DB).
- **Courses.** A mentor can have any number of courses; each course's content is an uploaded roadmap.
- **Invite codes + per-course access.** Mentees join a mentor with an invite code (a mentee can have
  several mentors). Joining shows nothing by itself: the mentor grants access course by course, from
  the mentee's page or the course's "Access & progress" table. Revoking keeps progress and submissions.
- **Progress, mentor-confirmed.** Only the mentor marks a mentee's topics done (`?mentee=<id>` on any
  course page), typically after reviewing their solution. Progress counts leaf topics; marking a section
  marks all of its subtopics. A course can be marked completed (this also marks every topic done);
  reopening a topic un-completes it. Both sides see progress bars on the dashboard, course and mentee pages.
- **Sequential unlocking.** Topics open in course order: a mentee can open the topics already done plus
  the first one that isn't ("Up next"); later topics are locked (the API returns 403 for them, including
  submissions) until the mentor marks the current one done.
- **Roadmap upload.** Markdown or JSON with live tree preview. Headings and nested bullet lists become
  topics; text under an item becomes its description.
- **Nested routes.** `/roadmaps/:id/:topic/:subtopic/...` — every level is its own page with breadcrumbs
  and a list of children. Non-canonical paths redirect to the real ancestry.
- **Screenshot submissions.** Drag-and-drop, file picker or Ctrl+V paste, up to 6 images.
- **VLM review (LangGraph).**

  ```
  START → perceive ──readable──→ assess → END
                   └─unreadable─→ ask_for_resubmit → END
  ```

  - `perceive` (low effort): transcribes code/terminal/UI and visible errors from the screenshots.
  - `assess` (high effort): grades against the topic path + mentor's description, using the
    transcription as grounding. Output is a typed `Review` (verdict, score, strengths, issues with
    severity/location, next steps, questions for the mentor) via structured outputs.
  - Runs as a background task; the submission page polls until it's done. Mentors can re-run it and
    write their own feedback.

## Setup

### 1. Clerk

Create an app at <https://dashboard.clerk.com>. You need the publishable key, the secret key and the
JWKS URL (`https://<your-app>.clerk.accounts.dev/.well-known/jwks.json`).

### 2. API

```bash
cd api
cp .env.example .env     # fill CLERK_JWKS_URL and ANTHROPIC_API_KEY
uv sync
uv run uvicorn app.main:app --reload --port 8000
uv run pytest            # parser + end-to-end API flow (auth and VLM stubbed)
```

### 3. Web

```bash
cd web
cp .env.example .env.local   # fill Clerk keys
pnpm install
pnpm dev                     # http://localhost:3000
```

## Roadmap format

```markdown
# Frontend Developer
A path from the basics to a first production app.

## HTML & CSS
- Semantic HTML
  - Forms and validation
    Build a sign-up form with native validation.
- Layout
  - Flexbox

## JavaScript
### Closures
```

Or JSON: `{"title": "...", "description": "...", "children": [{"title": "...", "children": [...]}]}`.

## Notes

- No migrations yet: tables are created on startup. After a schema change in development, delete
  `api/mentor_hub.db`. Add Alembic before the first real deployment.

- The model defaults to `claude-haiku-5-5` (`ANALYSIS_MODEL`), with server-side refusal fallback enabled
  (`fallbacks: "default"`).
- SQLite + local `uploads/` for development. For production, point `DATABASE_URL` at Postgres and move
  uploads to object storage.
