# Max-Meeting Codebase Summary

**Last Updated:** 2026-01-30
**Version:** v1.2.0

## Quick Stats

| Metric | Count |
|--------|-------|
| **Total API Endpoints** | 58 |
| **Backend Models** | 11 |
| **Backend Services** | 12 |
| **Frontend Routes** | 13 pages |
| **Frontend Components** | 43 |
| **Frontend Stores** | 9 (+ 3 test files) |

---

## API Endpoints by Router

| Router | Endpoints | Key Features |
|--------|-----------|--------------|
| `auth.py` | 4 | Login, token refresh, user info |
| `contacts.py` | 5 | CRUD with PII encryption |
| `meetings.py` | 8 | CRUD + attendees + soft delete |
| `agendas.py` | 12 | Hierarchical structure, LLM parsing, drag-drop |
| `recordings.py` | 9 | Chunked upload, STT processing, SSE progress |
| `results.py` | 10 | LLM generation, versioning, action items |
| `notes.py` | 5 | Meeting notes CRUD |
| `sketches.py` | 1 | Export sketch as PNG |
| `search.py` | 1 | Full-text search |
| `meeting_types.py` | 3 | Meeting templates |

**Total: 58 endpoints**

---

## Frontend Structure

### Routes
```
/ ..................... Dashboard
/login ................ Authentication
/contacts ............. Contact list
/contacts/new ......... Create contact
/contacts/[id] ........ Contact detail
/meetings ............. Meeting list
/meetings/new ......... Create meeting
/meetings/[id] ........ Meeting detail
/meetings/[id]/sketch . Whiteboard (tldraw)
/meetings/[id]/record . Audio recording
/meetings/[id]/results  Meeting summary
/meetings/[id]/results/edit  Edit summary
/meetings/deleted ..... Trash
```

### Component Categories
- **Core UI** (9): Button, Input, Modal, Toast, etc.
- **UI Components** (9): ConfirmDialog, MeetingCard, Skeleton, etc.
- **Results** (4): ActionItems, SpeakerMapper, SummaryEditor, TranscriptViewer
- **Sketch** (3): SketchPad, SketchToolbar, TldrawWrapper
- **Layout** (1): Sidebar
- **System** (5): PreflightCheck, UpdateNotifier, SyncConflictDialog, etc.

### Stores
- `auth.ts` - User authentication
- `contacts.ts` - Contact management
- `meeting.ts` - Meeting state
- `notes.ts` - Notes state
- `offline.ts` - Offline detection
- `offlineCache.ts` - IndexedDB cache
- `recording.ts` - Recording/upload state
- `results.ts` - Results/summary state
- `sketch.ts` - Drawing state
- `toast.ts` - Notifications
- `viewport.ts` - Responsive state

---

## Recent Major Changes (Jan 28-30, 2026)

### STT Pipeline Refactor (v1.2.0)
- Changed from Celery chord → sequential processing
- Fixed temp file cleanup issues
- Improved WebM duration detection (ffmpeg fallback)
- **NEW**: Generate results without recording (agendas + notes only)

### Performance Optimization
- Added `lazy="noload"` to all SQLAlchemy relationships
- Result: 15s → 100ms for meeting detail API
- **NEW API**: `GET /meetings/{id}/recordings` - list recordings
- **NEW API**: `POST /recordings/{id}/process` - manual STT trigger

### PWA Support
- Service worker for offline caching
- IndexedDB for offline data
- Update notification system

### UX Improvements
- Recording status indicators on results page
- "Generate from Notes" button
- Korean empty state messages
- Tablet-optimized responsive design

---

## Technology Stack

### Backend
- **Framework**: FastAPI 0.109+
- **Database**: PostgreSQL 16 (asyncpg driver)
- **ORM**: SQLAlchemy 2.0 (async)
- **Task Queue**: Celery + Redis
- **AI/ML**: 
  - Google Gemini Flash (LLM)
  - faster-whisper (STT)
  - pyannote.audio (speaker diarization)
  - silero-vad (voice activity detection)

### Frontend
- **Framework**: SvelteKit 2
- **State**: Svelte 5 (runes)
- **Styling**: TailwindCSS
- **Drawing**: tldraw
- **Offline**: IndexedDB + Service Worker

### Infrastructure
- **Web Server**: Caddy (reverse proxy)
- **Process Manager**: systemd
- **Frontend Hosting**: Vercel
- **Backend Hosting**: Self-hosted (ET server)

---

## Key Architectural Patterns

### 1. Soft Delete
All main entities inherit `SoftDeleteMixin`:
- `deleted_at` timestamp (null = active)
- Restore endpoints available
- Filtered by default in queries

### 2. PII Encryption
Contact information encrypted at rest:
- Fernet symmetric encryption
- Transparent in service layer
- Key stored in environment

### 3. Chunked Upload
Large audio files uploaded in chunks:
- Client tracks byte offset
- Server resumes from last chunk
- HEAD request for upload status

### 4. Hierarchical Agendas
Self-referential agenda structure:
- `parent_id` foreign key
- Recursive loading with `children` relationship
- LLM parses plain text → nested structure

### 5. Result Versioning
Multiple result versions per meeting:
- Track editing history
- Regenerate with LLM
- Mark versions as verified

### 6. Offline-First Frontend
Progressive web app with offline support:
- Service worker caches routes
- IndexedDB stores API data
- Sync on reconnect with conflict resolution

---

## File Locations

```
max-meeting/
├── backend/
│   ├── app/
│   │   ├── routers/      # 11 API router files
│   │   ├── services/     # 12 business logic services
│   │   ├── models/       # 11 SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   └── main.py       # FastAPI app
│   ├── workers/
│   │   └── tasks/        # Celery tasks (stt.py, llm.py)
│   └── .env              # Environment variables
├── frontend/
│   ├── src/
│   │   ├── routes/       # 13 SvelteKit pages
│   │   └── lib/
│   │       ├── components/  # 43 Svelte components
│   │       └── stores/      # 9 state stores
│   └── .env              # PUBLIC_API_URL
├── docs/                 # Detailed documentation
└── CLAUDE.md             # Quick reference
```

---

## Related Documentation

- [BACKEND.md](docs/BACKEND.md) - API details, services, environment
- [FRONTEND.md](docs/FRONTEND.md) - Routes, components, stores
- [DATABASE.md](docs/DATABASE.md) - Schema, tables, relationships
- [INFRASTRUCTURE.md](docs/INFRASTRUCTURE.md) - Deployment, servers, config
- [CLAUDE.md](CLAUDE.md) - Quick reference for development

---

For detailed codebase analysis, see: `.claude/cache/agents/scout/output-*.md`

