# MAX Meeting Changelog

All notable changes to this project are documented in this file.

---

## [2026-02-03] - Meeting Agenda CRUD v1.17.0

### Added
- **Feature**: 회의 중 아젠다 CRUD
  - 녹음 전/후 전체 CRUD 지원
  - 녹음 중 제한적 편집 (안전 장치 포함)
  - 인라인 제목 편집 (클릭 → input 전환 → Enter/blur 저장)
  - 안건 추가 버튼 (목록 하단)
  - 안건 삭제 버튼 (hover 시 표시, 권한 있을 때만)
  - 편집 불가 시 잠금 아이콘 표시

- **New File**: `frontend/src/lib/utils/agenda-permissions.ts`
  - `getAgendaPermissions()` - 안건별 권한 계산
  - `canAddAgenda()` - 추가 가능 여부 확인
  - `getAgendaPermissionsMap()` - 계층형 안건 일괄 권한 체크

### Changed
- **AgendaNotePanel.svelte**: CRUD UI 추가
  - 새 props: `activeAgendaId`, `isPaused`, `onAgendaCreate`, `onAgendaUpdate`, `onAgendaDelete`
  - 인라인 편집 상태 관리
  - 키보드 지원 (Enter/Escape)

- **record/+page.svelte**: 핸들러 연결
  - `handleAgendaCreate()` - 낙관적 업데이트
  - `handleAgendaUpdate()` - 낙관적 업데이트 + 롤백
  - `handleAgendaDelete()` - time_segments 보호 로직

### Safety Features
- `activeAgendaId` 체크로 현재 녹음 중 안건 편집 차단
- `time_segments` 있는 안건 삭제 차단
- API 실패 시 자동 롤백

### Technical Details
- **Match Rate**: 100% (Design vs Implementation)
- **Build**: 성공 (10.78s)
- **Type Check**: 통과 (경고만, 에러 없음)

---

## [2026-02-01] - Question Perspective Customization v1.16.7

### Added
- **Feature**: Question Perspective Customization for MeetingType
  - New field `question_perspective` in MeetingType model
  - Stores custom perspective/context for LLM-based question generation
  - Allows users to customize the tone and focus of auto-generated agenda questions
- **Database**: Alembic migration for question_perspective column
  - File: `backend/alembic/versions/2bf4f5c94298_add_question_perspective_to_meeting_.py`
  - Text column, nullable, no length limit (⚠️ future improvement: add max_length)
- **API**: Meeting Type endpoints extended
  - POST /api/v1/meeting-types now accepts `question_perspective` parameter
  - PATCH /api/v1/meeting-types/{type_id} supports perspective updates
  - GET /api/v1/meeting-types returns perspective in response
- **Schema**: Validation schemas updated
  - MeetingTypeCreate: optional question_perspective field
  - MeetingTypeUpdate: optional question_perspective field with partial update support
  - MeetingTypeResponse: includes question_perspective in API responses
- **LLM Integration**: Question generation improved
  - generate_questions() method extended with `question_perspective` parameter
  - Perspective automatically included in Gemini API prompt when set
  - Format: "회의 관점: {perspective}\n이 관점을 반영하여..."
  - Applies to both single and hierarchical agenda creation
- **Frontend**: Meeting Type creation UI with perspective input
  - New textarea input for question perspective in "New Meeting Type" modal
  - Character placeholder showing usage example
  - Integrated with MeetingType store for state management
  - TypeScript interface updated to include perspective field

### Changed
- **Agenda Creation**: Auto-question generation now perspective-aware
  - create_agenda() endpoint: queries meeting_type.question_perspective and passes to LLM
  - create_agenda_hierarchical() endpoint: same integration for hierarchical agendas
  - Performance: uses selectinload to prevent N+1 queries when fetching meeting_type
- **LLM Prompts**: Question generation prompts restructured
  - Added perspective section after context in prompt template
  - Users can now influence the style/focus of generated questions
  - Example: "North Branch Director's perspective on profitability impact"

### Technical Details
- **Match Rate**: 100% (Design vs Implementation)
- **Quality Score**: 85/100 (Code Analyzer)
  - ⚠️ Warning: Prompt Injection risk (direct user input in LLM prompt)
  - ⚠️ Warning: No length limit on perspective field
  - ⚠️ Warning: Frontend textarea has no maxlength attribute
  - ⚠️ Bug: Cannot set question_perspective to null (line 129 issue)
- **Files Modified**: 9 total
  - Backend: 5 files (models, schemas, routers, services)
  - Frontend: 3 files (stores, routes, version)
  - Database: 1 migration file
- **New Files**: 1 (migration file)
- **Lines of Code**: ~150 added

### Known Issues
- ⚠️ **BUG**: Setting question_perspective to null doesn't work
  - Affected: PATCH /api/v1/meeting-types/{type_id}
  - Cause: Line 129 condition `if data.question_perspective is not None`
  - Workaround: Cannot delete perspective through API (only through DB)
  - Fix: Use `model_dump(exclude_unset=True)` instead of None check
- ⚠️ **Security**: Prompt Injection risk
  - No validation on perspective content
  - Direct insertion into LLM prompt without escaping
  - Recommendation: Add input sanitization and max_length validation
- ⚠️ **Usability**: No front-end UI for editing meeting types
  - Meeting types can only be created (no edit/delete UI)
  - Editing requires direct API calls
  - Recommendation: Add Meeting Types management page
- ⏭️ **Missing**: Unit tests and E2E tests
  - No test coverage for new perspective functionality
  - Recommendation: Add pytest tests and Playwright E2E tests

### Security Considerations
- **Prompt Injection Prevention**: RECOMMENDED
  - Add max_length constraint (suggest 1000 characters)
  - Sanitize dangerous prompt control characters
  - Example: Remove triple backticks, "---", "===" from input
- **Input Validation**: RECOMMENDED
  - Trim and validate perspective content
  - Consider providing template options instead of free-form text
- **Rate Limiting**: No changes (existing limits apply)

### Performance Impact
- **Positive**: selectinload optimization prevents N+1 queries
- **Neutral**: LLM prompt slightly longer (50-200 extra characters) due to perspective
- **No degradation** in API response times

### Backward Compatibility
- ✅ Fully backward compatible
- question_perspective is optional (nullable)
- Existing meeting types without perspective continue to work
- Meeting with question_perspective=null generate questions normally (perspective ignored)

### Testing Recommendations
```python
# Unit tests needed:
- test_create_meeting_type_with_perspective()
- test_update_meeting_type_perspective()
- test_perspective_in_question_generation()
- test_null_perspective_handling()
- test_perspective_length_limit() # when implemented

# E2E tests needed:
- Create meeting type → create agenda → verify questions reflect perspective
- Edit meeting type perspective → create new agenda → verify updated perspective applied
- Delete perspective → verify fallback to default behavior
```

### Deployment Checklist
- [ ] Run Alembic migration: `alembic upgrade head`
- [ ] Test API endpoints manually
- [ ] Verify question generation with perspective
- [ ] Check frontend UI rendering
- [ ] Perform E2E testing (meeting creation flow)
- [ ] Monitor LLM API calls for unexpected token usage
- [ ] Consider adding rate limiting if necessary

---

## [2026-01-30] - Code Quality Improvements v1.6.0

### Added
- **Security**: SQL Injection escape utility for LIKE pattern queries
  - New function `escape_like()` in `backend/app/services/contact.py`
  - Prevents special character injection in contact search
- **Security**: Meeting access ownership verification
  - New method `verify_meeting_access()` in `backend/app/services/meeting.py`
  - Prevents unauthorized users from accessing other users' meeting data
- **Logging**: Environment-based logger utility
  - New file `frontend/src/lib/utils/logger.ts`
  - Conditional logging based on DEV environment variable
  - Supports debug, info, warn, error levels
- **Utilities**: Consolidated date/time formatting functions
  - New file `frontend/src/lib/utils/format.ts`
  - Single source for formatDate, formatDateTime, formatTime, formatDuration, truncate

### Changed
- **Security**: Deprecated asyncio methods replaced
  - `asyncio.get_event_loop().run_until_complete()` → `asyncio.run()`
  - Updated in `workers/tasks/stt.py` (lines 359, 442)
  - Updated in `workers/tasks/llm.py` (line 442)
  - Resolves Python 3.10+ deprecation warnings
- **Logging**: Console logging refactored
  - All `console.log` calls in `frontend/src/lib/api.ts` → `logger.debug`
  - All `console.error` calls → `logger.error`
  - Debug logs automatically removed in production builds
- **Frontend**: All date formatting imports unified
  - 9 files updated to use new `$lib/utils/format.ts`
  - Eliminated duplicate formatting logic

### Fixed
- SQL injection vulnerability in contact search with special characters
- Unauthorized access to meeting data (ownership verification added)
- Production logs cluttered with debug information
- Deprecated asyncio patterns causing warnings on Python 3.10+

### Technical Details
- **Match Rate**: 92.9% (Design vs Implementation)
- **Files Modified**: 18 total
  - Backend: 7 files (services, workers, routers)
  - Frontend: 11 files (components, routes, stores, utils)
- **New Files**: 2 (logger.ts, format.ts)
- **Lines of Code**: ~200 added, ~50 removed

---

## Previous Versions

See `/home/et/max-ops/max-meeting/frontend/src/lib/version.ts` for version history prior to v1.16.0.
