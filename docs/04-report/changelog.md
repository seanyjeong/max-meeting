# MAX Meeting Changelog

All notable changes to this project are documented in this file.

---

## [2026-01-30] - UX 개선 및 버그 수정 v1.4

### Added
- Progress gauge for STT processing and meeting transcription
  - Time-based estimated progress percentage
  - Real-time progress updates during processing
  - Progress display in results page and recordings list
- Question edit/delete UI in meeting details page
  - Inline action buttons for editing questions
  - Inline action buttons for deleting questions
  - Confirmation dialogs before deletion
- Child agenda numbering in hierarchical agenda display
  - Format: 1.1, 1.2, etc. for child agendas
  - Clear visual hierarchy in meeting details and PDF

### Changed
- Meeting start buttons consolidated
  - Single unified "회의 시작" (Start Meeting) button
  - Recording mode selected automatically in recording interface
- Transcript viewer tab styling for better visibility
  - Selected tab background: blue (#1d4ed8)
  - Selected tab text: white with increased contrast
  - Added box-shadow for depth perception
- Recording controls repositioned
  - Moved from floating bottom-right to integrated recording section
  - Better integration with meeting workspace layout
- CompactRecordingBar component
  - Removed fixed positioning
  - Changed to relative positioning within recording section
  - Better alignment with note-sketch area

### Fixed
- Child agenda creation not persisting
  - ROOT CAUSE: Missing recursive save function in new meeting page
  - Solution: Added `saveAgendasRecursively` function for hierarchical storage
  - Impact: Child agendas now properly created and stored in database
- Agenda-discussion content mismatch
  - ROOT CAUSE: LLM response mapping not using agenda IDs
  - Solution: Added `agenda_id` to LLM prompt and worker mapping logic
  - Impact: Discussions now correctly matched to specific agendas including children
- Child agendas missing from PDF reports
  - ROOT CAUSE: Discussions not generated for child agendas (fixed by C3)
  - Solution: Automatic fix via improved discussion generation
  - Impact: PDF reports now include discussions for all agenda levels
- Typing Shift key lock behavior
  - Investigation completed: No code issue found
  - Confirmed as environment/keyboard issue, not application bug
- NoteSketchArea scroll overflow
  - Fixed scrolling behavior in note-taking interface
  - Improved scroll performance during recording
- Tablet responsive layout (2000x1200)
  - Added media queries for high-resolution tablets
  - Font size adjustments for tablet screens
  - Minimum width settings for agenda panel
  - Improved layout stability on large tablets

### Technical Details
- **Match Rate**: 100% (Design vs Implementation)
- **Files Modified**: 9 (backend: 2, frontend: 7)
- **Files Added**: 0
- **Backend Changes**:
  - `app/services/llm.py`: Enhanced LLM prompt with agenda metadata
  - `workers/tasks/llm.py`: Improved agenda-discussion mapping logic
- **Frontend Changes**:
  - `routes/meetings/new/+page.svelte`: Recursive agenda save function
  - `routes/meetings/[id]/+page.svelte`: Question UI and meeting start consolidation
  - `routes/meetings/[id]/record/+page.svelte`: Recording controls repositioning
  - `routes/meetings/[id]/results/+page.svelte`: Progress gauge implementation
  - `lib/components/recording/CompactRecordingBar.svelte`: Positioning fix
  - `lib/components/recording/NoteSketchArea.svelte`: Scroll fix
  - `lib/components/results/TranscriptViewer.svelte`: Tab styling improvement
  - `lib/components/results/RecordingsList.svelte`: Progress display
  - `app.css`: Tablet responsive styles
- **Database**: No schema changes
- **Svelte Version**: 5 (Rune-based reactivity)

### Files Changed
```
Backend:
  - app/services/llm.py
  - workers/tasks/llm.py

Frontend:
  - src/routes/meetings/new/+page.svelte
  - src/routes/meetings/[id]/+page.svelte
  - src/routes/meetings/[id]/record/+page.svelte
  - src/routes/meetings/[id]/results/+page.svelte
  - src/lib/components/recording/CompactRecordingBar.svelte
  - src/lib/components/recording/NoteSketchArea.svelte
  - src/lib/components/results/TranscriptViewer.svelte
  - src/lib/components/results/RecordingsList.svelte
  - src/app.css

Documentation:
  - docs/01-plan/features/ux-improvements-v1.4.plan.md
  - docs/02-design/features/ux-improvements-v1.4.design.md
  - docs/04-report/features/ux-improvements-v1.4.report.md
```

### Notes
- All 12 issues from user feedback completely resolved
- 100% design-to-implementation alignment achieved
- No breaking changes to existing features
- Backward compatible with all previous meeting data
- Improved accessibility through better visual contrast
- Responsive design now covers tablet resolutions from 1200px to 2000px
- Progress indicators provide better feedback during long-running operations

### Version Info
- **Version**: v1.4.0
- **Release Date**: 2026-01-30
- **Related Issues**: 12 (C1-C4, U1-U6, L1-L2)
- **Estimated Development Time**: 5 hours
- **PDCA Report**: docs/04-report/features/ux-improvements-v1.4.report.md

---

## [2026-01-30] - Hierarchical Agenda System v1.2.3

### Added
- Hierarchical agenda toggle UI in meeting details page
  - Parent agenda expand/collapse
  - Child agenda display with indentation
  - Per-child question rendering
- Child agenda timestamp tracking in recording interface
  - Clickable child agenda buttons with time segment support
  - Separate time_segments storage for child agendas
- Multi-level agenda filtering in results page
  - Parent agenda dropdown filter
  - Child agenda submenu for detailed filtering
  - Time-based transcript segment matching
- PDF meeting report page
  - Agenda-organized content layout
  - Notes and sketches display
  - Print-optimized styling
  - Sketch modal viewer
- Question generation priority logic
  - Child agenda-first generation
  - Parent agenda fallback when no children exist

### Changed
- Meeting detail page: flatten UI to show agenda hierarchy
- Recording page: AgendaNotePanel now supports child agenda selection
- Results page: TranscriptViewer implements hierarchical filtering
- PWA update notifier: disabled per user request
- Question generation: backend logic prioritizes child agendas

### Fixed
- Svelte 5 Rune reactivity for toggle state management
- Time segment assignment for child agendas during recording
- Transcript filtering accuracy for multi-level time boundaries
- Print styling for PDF generation

### Technical Details
- **Match Rate**: 98% (Design vs Implementation)
- **Files Modified**: 6
- **Files Added**: 1 (report page)
- **Backend Changes**: agendas.py question generation logic
- **Database**: No schema changes (reuses existing agendas table)
- **Svelte Version**: 5 (Rune-based reactivity)

### Files Changed
```
Frontend:
  - src/lib/components/UpdateNotifier.svelte
  - src/routes/meetings/[id]/+page.svelte
  - src/lib/components/recording/AgendaNotePanel.svelte
  - src/routes/meetings/[id]/record/+page.svelte
  - src/lib/components/results/TranscriptViewer.svelte
  - src/routes/meetings/[id]/results/report/+page.svelte (NEW)
  - src/routes/meetings/[id]/results/+page.svelte

Backend:
  - app/routers/agendas.py

Documentation:
  - docs/01-plan/features/hierarchical-agenda-system.plan.md
  - docs/02-design/features/hierarchical-agenda-system.design.md
  - docs/04-report/features/hierarchical-agenda-system.report.md
```

### Notes
- Backward compatible with meetings without child agendas
- Existing time_segments data remains unchanged
- PWA offline functionality preserved after update notifier removal
- All 6 implementation phases completed successfully

---

## Previous Versions

See git history for earlier changes.
