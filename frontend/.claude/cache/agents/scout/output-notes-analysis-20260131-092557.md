# Codebase Report: Meeting Notes/Memos Storage & Retrieval
Generated: 2026-01-31

## Summary
Meeting notes (called "manual_notes" in backend, "메모" in UI) are stored in PostgreSQL via REST API with auto-save functionality. Notes are associated with specific agendas and used by the LLM to generate meeting summaries.

---

## Storage Mechanism

### Frontend Store (`src/lib/stores/notes.ts`)
**Type:** Svelte writable store with Map-based state
**Key Features:**
- **Auto-save:** 30-second interval (configurable)
- **Debouncing:** Prevents excessive API calls during typing
- **Dirty tracking:** Only saves modified notes
- **State:** `Map<agendaId, Note>` for O(1) lookup

**Store Interface:**
```typescript
interface Note {
  id?: number;           // Server ID (undefined for new notes)
  agendaId: number;      // FK to agenda
  content: string;       // Note text
  createdAt?: Date;
  updatedAt?: Date;
}

interface NotesState {
  notes: Map<number, Note>;
  dirtyNotes: Set<number>;     // Unsaved agendas
  isLoading: boolean;
  isSaving: boolean;
  error: string | null;
  lastSavedAt: Date | null;
  meetingId: number | null;    // For POST endpoint
}
```

### Data Flow

```
┌─────────────────┐
│ AgendaNotePanel │ (UI)
└────────┬────────┘
         │ handleNoteInput (500ms debounce)
         ▼
    onNoteChange(agendaId, content)
         │
         ▼
  ┌──────────────┐
  │ notesStore   │
  │ .saveNote()  │ ← Updates local state + marks dirty
  └──────┬───────┘
         │
         ▼ (30s auto-save)
    autoSave()
         │
         ├─ POST /meetings/{id}/notes (new)
         └─ PATCH /notes/{id} (existing)
```

---

## API Endpoints

### Backend Routes (`app/routers/notes.py`)

| Method | Endpoint | Purpose | Request Body | Response |
|--------|----------|---------|--------------|----------|
| **GET** | `/meetings/{meeting_id}/notes` | List all notes | - | `{ data: Note[], meta: { total } }` |
| **POST** | `/meetings/{meeting_id}/notes` | Create note | `{ agenda_id, content, timestamp_seconds? }` | `Note` (201) |
| **GET** | `/notes/{note_id}` | Get single note | - | `Note` |
| **PATCH** | `/notes/{note_id}` | Update note | `{ content?, agenda_id?, timestamp_seconds? }` | `Note` |
| **DELETE** | `/notes/{note_id}` | Delete note | - | 204 No Content |

**Authentication:** All endpoints require JWT token (`get_current_user`)

### Request/Response Schema (`app/schemas/note.py`)

```python
# CREATE
class NoteCreate(BaseModel):
    agenda_id: int | None = None
    content: str
    timestamp_seconds: int | None = None

# UPDATE
class NoteUpdate(BaseModel):
    agenda_id: int | None = None
    content: str | None = None
    timestamp_seconds: int | None = None

# RESPONSE
class NoteResponse(BaseModel):
    id: int
    meeting_id: int
    agenda_id: int | None
    content: str
    timestamp_seconds: int | None
    created_at: datetime
    updated_at: datetime
```

---

## Database Schema

### Table: `manual_notes` (`app/models/note.py`)

```sql
CREATE TABLE manual_notes (
    id SERIAL PRIMARY KEY,
    meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    agenda_id INTEGER REFERENCES agendas(id),  -- NULL for general notes
    content TEXT NOT NULL,
    timestamp_seconds INTEGER,  -- Recording timestamp
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_notes_meeting ON manual_notes(meeting_id, created_at);
```

**Relationships:**
- `meeting` → Many-to-One (with cascade delete)
- `agenda` → Many-to-One (nullable)

**Ordering:** By `timestamp_seconds ASC NULLSLAST`, then `created_at`

---

## Data Association with Agendas

### In Recording Interface (`src/routes/meetings/[id]/record/+page.svelte`)

**Lifecycle:**
1. **Load notes on mount:**
   ```typescript
   await notesStore.loadNotes(meetingId);
   const notesState = get(notesStore);
   agendaNotes = new Map([...notesState.notes].map(([id, note]) => [id, note.content]));
   ```

2. **Track current agenda:**
   ```typescript
   let currentAgendaIndex = $state(0);
   let activeChildId = $state<number | null>(null);
   let activeAgendaId = activeChildId ?? currentAgenda.id;
   ```

3. **Save on input (debounced 500ms):**
   ```typescript
   function handleNoteInput(event: Event) {
       const timer = setTimeout(() => {
           onNoteChange(agendaId, content);  // → notesStore.saveNote()
       }, 500);
   }
   ```

4. **Auto-save on destroy:**
   ```typescript
   onDestroy(async () => {
       await notesStore.forceSave();
       notesStore.cleanup();
   });
   ```

### In AgendaNotePanel Component

**Props:**
- `notes: Map<number, string>` - All notes keyed by agendaId
- `onNoteChange: (agendaId, content) => void` - Save callback

**UI:**
- Textarea per agenda (lines 406-413)
- Content derived from active agenda/child: `noteContent = notes.get(activeChildId || currentAgenda.id) || ''`

---

## Results Page Data Loading

### Load Sequence (`src/routes/meetings/[id]/results/+page.svelte`)

```typescript
onMount(async () => {
    await Promise.all([
        meetingPromise,
        resultsStore.loadResult(meetingId),
        resultsStore.loadTranscript(meetingId),
        loadRecordingsStatus()
    ]);
    // Notes are NOT explicitly loaded on results page
});
```

**IMPORTANT:** Results page does **NOT** load notes directly. Notes are used server-side during LLM generation.

### How Notes Are Used in Results

**Server-Side (LLM Service):**
- When generating meeting summary, backend queries `manual_notes` table
- Notes are included in LLM prompt context
- LLM synthesizes notes + transcript → summary/action items

**Frontend Display:**
- Results page shows **generated** summary (not raw notes)
- Original notes are visible in recording interface
- No dedicated "notes" tab in results view

---

## Key Files

| File | Purpose | Key Functions |
|------|---------|---------------|
| **Frontend** | | |
| `src/lib/stores/notes.ts` | Notes state management | `loadNotes()`, `saveNote()`, `autoSave()` |
| `src/routes/meetings/[id]/record/+page.svelte` | Recording interface | `handleNoteChange()`, loads/saves notes |
| `src/lib/components/recording/AgendaNotePanel.svelte` | Agenda + note UI | Displays textarea, debounced input |
| **Backend** | | |
| `app/routers/notes.py` | Notes API | CRUD endpoints |
| `app/models/note.py` | DB model | `ManualNote` SQLAlchemy model |
| `app/schemas/note.py` | Pydantic schemas | Request/response validation |
| `app/services/llm.py` | LLM generation | Queries notes for context (likely) |

---

## Notes vs Sketches

| Feature | Notes (ManualNote) | Sketches |
|---------|-------------------|----------|
| **Table** | `manual_notes` | `sketches` |
| **Content** | Text (TEXT field) | SVG/JSON + OCR text |
| **Storage** | PostgreSQL only | File path + JSONB |
| **API** | `/meetings/{id}/notes` | `/meetings/{id}/sketches` |
| **UI Tab** | "메모" | "펜" |
| **Auto-save** | 30s interval | Per-stroke (sketch store) |

Both share `meeting_id`, `agenda_id`, `timestamp_seconds` fields.

---

## Missing/Unclear Areas

1. **LLM Integration Verification:** Could not confirm exact code path where `manual_notes` are queried and passed to Gemini. Need to check:
   - `app/services/llm.py` - likely in `generate_meeting_summary()` or similar
   - May be included via meeting relationships (Meeting → manual_notes)

2. **Results Page Note Display:** Currently NO way to view raw notes on results page. Only synthesized summaries. Consider UX improvement?

3. **Note Deletion:** API supports DELETE but UI has no delete button.

4. **Timestamp Usage:** `timestamp_seconds` field exists but unclear if it's used for playback sync or just ordering.

---

## Verification Status

✅ **VERIFIED** (Read files):
- Frontend notes store implementation
- API endpoints and routing
- Database schema and models
- Recording page data flow
- AgendaNotePanel component

? **INFERRED** (Not directly read):
- LLM service using manual_notes (grep found no matches - may use ORM relationships)
- Results page NOT loading notes (confirmed by reading +page.svelte)

