# MAX Meeting Changelog

All notable changes to this project are documented in this file.

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
