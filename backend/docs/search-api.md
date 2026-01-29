# Search API Documentation

## Overview

The Search API provides full-text search capabilities across meetings, contacts, and transcripts using PostgreSQL's `pg_trgm` (trigram) extension for fuzzy matching.

## Endpoint

```
GET /api/v1/search?q={query}&limit={limit}&offset={offset}
```

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `q` | string | Yes | - | Search query string (1-200 characters) |
| `limit` | integer | No | 20 | Maximum results per type (1-100) |
| `offset` | integer | No | 0 | Pagination offset |

### Authentication

Requires valid JWT token in Authorization header:
```
Authorization: Bearer {token}
```

## Response Format

```json
{
  "data": {
    "meetings": [
      {
        "id": 1,
        "title": "Weekly Team Sync",
        "scheduled_at": "2026-01-28T10:00:00Z",
        "status": "completed",
        "highlight": "...discussion about project timeline...",
        "match_score": 0.85
      }
    ],
    "contacts": [
      {
        "id": 1,
        "name": "John Doe",
        "organization": "Acme Corp",
        "role": "Developer",
        "highlight": "John Doe",
        "match_score": 0.92
      }
    ],
    "transcripts": [
      {
        "id": 1,
        "meeting_id": 1,
        "meeting_title": "Weekly Team Sync",
        "chunk_index": 0,
        "highlight": "...we need to finalize the budget...",
        "match_score": 0.78,
        "created_at": "2026-01-28T10:05:00Z"
      }
    ]
  },
  "meta": {
    "query": "budget",
    "total": 3,
    "limit": 20,
    "offset": 0
  }
}
```

## Search Behavior

### Similarity Scoring

The API uses PostgreSQL's `similarity()` function from pg_trgm which:
- Returns scores between 0 (no match) and 1 (perfect match)
- Uses trigram matching for fuzzy search
- Finds results even with typos or partial matches
- Threshold: 0.1 (results below this score are filtered out)

### Search Targets

| Entity | Field | Description |
|--------|-------|-------------|
| Meetings | `summary` | From `meeting_results.summary` |
| Contacts | `name` | From `contacts.name` |
| Transcripts | `full_text` | From `transcripts.full_text` |

### Highlighting

Each result includes a `highlight` field showing:
- Context around the matched term (100 characters before/after)
- Ellipsis (...) for truncated text
- The matched snippet if exact match found
- First 200 characters if no exact match

## Database Indexes

The following GIN indexes are created for performance:

```sql
-- Contacts (already existed)
CREATE INDEX ix_contacts_name_trgm ON contacts
USING gin (name gin_trgm_ops);

-- Meeting Results (new)
CREATE INDEX ix_meeting_results_summary_trgm ON meeting_results
USING gin (summary gin_trgm_ops);

-- Transcripts (new)
CREATE INDEX ix_transcripts_full_text_trgm ON transcripts
USING gin (full_text gin_trgm_ops);
```

## Example Usage

### Search for "budget discussion"

```bash
curl -X GET \
  'http://localhost:8000/api/v1/search?q=budget%20discussion&limit=10' \
  -H 'Authorization: Bearer {token}'
```

### Search with pagination

```bash
curl -X GET \
  'http://localhost:8000/api/v1/search?q=project&limit=20&offset=20' \
  -H 'Authorization: Bearer {token}'
```

## Performance Considerations

1. **Index Usage**: GIN indexes are used for fast trigram matching
2. **Parallel Queries**: Searches across all entity types run in sequence (could be parallelized)
3. **Result Limit**: Default 20 results per type (max 100)
4. **Null Handling**: Skips null values in full_text column

## Implementation Files

- **Router**: `app/routers/search.py`
- **Service**: `app/services/search.py`
- **Schemas**: `app/schemas/search.py`
- **Migration**: `alembic/versions/e3b64dac2684_add_pg_trgm_indexes_for_search.py`

## Future Enhancements

- [ ] Parallel search execution across entity types
- [ ] Configurable similarity threshold
- [ ] Search in additional fields (e.g., meeting description, notes)
- [ ] Search result ranking/scoring improvements
- [ ] Full-text search with weighted fields
- [ ] Search filters (by date, status, type, etc.)
- [ ] Search history and suggestions
