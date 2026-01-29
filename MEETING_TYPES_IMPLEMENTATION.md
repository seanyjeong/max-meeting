# Meeting Types Implementation

## Overview
Added meeting type management functionality to MAX Meeting, allowing users to create, list, and delete meeting types (e.g., 북부, 전국, 일산).

## Backend Changes

### 1. Schema (`/backend/app/schemas/meeting_type.py`)
Created new Pydantic schemas:
- `MeetingTypeCreate`: For creating new meeting types
- `MeetingTypeResponse`: For API responses
- `MeetingTypeListResponse`: For list endpoint

### 2. Router (`/backend/app/routers/meeting_types.py`)
Implemented three endpoints:

#### GET `/api/v1/meeting-types`
- Lists all non-deleted meeting types
- Returns sorted by name
- Requires authentication

#### POST `/api/v1/meeting-types`
- Creates new meeting type
- Validates uniqueness (409 Conflict if duplicate)
- Requires authentication

#### DELETE `/api/v1/meeting-types/{type_id}`
- Soft deletes meeting type
- Returns 404 if not found
- Preserves associated meetings
- Requires authentication

### 3. Main App (`/backend/app/main.py`)
- Imported `meeting_types` router
- Registered router with API prefix `/api/v1`

## Frontend Changes

### 1. New Meeting Form (`/frontend/src/routes/meetings/new/+page.svelte`)

#### Added State Variables
```typescript
let showNewTypeModal = false;
let newTypeName = '';
let isCreatingType = false;
```

#### Updated Meeting Type Select
- Changed placeholder from "유형 선택" to "유형 선택..."
- Added "+ 새 유형" button next to dropdown
- Button opens modal for creating new types

#### New Meeting Type Modal
- Modal dialog for adding new meeting types
- Input field with 50 character limit
- Keyboard shortcuts:
  - Enter: Submit
  - Escape: Close
- Real-time validation
- Error handling for duplicates (409 status)
- Auto-selects newly created type
- Updates dropdown list after creation

#### Functions Added
- `createNewMeetingType()`: Handles POST request to create type
- `closeNewTypeModal()`: Cleans up modal state

## API Endpoints

### List Meeting Types
```http
GET /api/v1/meeting-types
Authorization: Bearer <token>
```

Response:
```json
{
  "data": [
    {
      "id": 1,
      "name": "북부"
    },
    {
      "id": 2,
      "name": "전국"
    }
  ]
}
```

### Create Meeting Type
```http
POST /api/v1/meeting-types
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "일산"
}
```

Response (201 Created):
```json
{
  "data": {
    "id": 3,
    "name": "일산"
  }
}
```

Error (409 Conflict):
```json
{
  "detail": "Meeting type '일산' already exists"
}
```

### Delete Meeting Type
```http
DELETE /api/v1/meeting-types/{type_id}
Authorization: Bearer <token>
```

Response: 204 No Content

## Database Model
The `MeetingType` model already exists in `/backend/app/models/meeting.py`:
- Uses soft delete (SoftDeleteMixin)
- Has unique constraint on name
- One-to-many relationship with Meeting

## Testing

### Backend
```bash
cd backend
source venv/bin/activate
python -c "from app.main import app; print('Backend imports successfully')"
```

### Manual Testing Checklist
- [ ] List empty meeting types
- [ ] Create new meeting type
- [ ] Verify type appears in dropdown
- [ ] Create duplicate type (should fail with 409)
- [ ] Select type when creating meeting
- [ ] Delete meeting type
- [ ] Verify deleted type doesn't appear in list

## Security
- All endpoints require JWT authentication via `get_current_user`
- Soft delete preserves data integrity
- Name uniqueness enforced at database level

## Future Enhancements
- Add PATCH endpoint for renaming types
- Add type color/icon customization
- Add type usage statistics
- Add bulk operations
- Add admin-only type management
