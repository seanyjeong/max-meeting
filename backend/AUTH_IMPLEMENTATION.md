# JWT Authentication System Implementation

## Completed Components

### 1. Configuration (`app/config.py`)
- Pydantic Settings for environment variables
- JWT configuration (HS256, 1h access, 7d refresh)
- Rate limiting configuration
- Redis and database URLs

### 2. Password Module (`app/auth/password.py`)
- bcrypt hashing with cost factor 12
- `verify_password()` - verify plain password against hash
- `get_password_hash()` - hash password

### 3. JWT Module (`app/auth/jwt.py`)
- `create_access_token()` - 1 hour expiry, includes jti/aud/iss
- `create_refresh_token()` - 7 days expiry
- `verify_token()` - decode and validate JWT with audience/issuer checks
- Token rotation on refresh

### 4. Dependencies (`app/auth/deps.py`)
- `get_current_user()` - FastAPI dependency for access token
- `verify_refresh_token()` - FastAPI dependency for refresh token
- HTTPBearer security scheme

### 5. Rate Limiting (`app/middleware/rate_limit.py`)
- Redis-based sliding window rate limiter
- `RateLimiter` class with `check_rate_limit()`
- `parse_rate_limit()` - parse strings like "5/minute"
- `rate_limit_dependency()` - FastAPI dependency
- Configurable limits: login (5/min), refresh (10/min), default (200/min)

### 6. Audit Logging (`app/middleware/audit_log.py`)
- `AuditLogger.log()` - log security events to database
- `audit_middleware()` - add request ID to all requests
- Logs: timestamp, event_type, user_id, IP, action, status, details

### 7. Auth Router (`app/routers/auth.py`)
- `POST /auth/login` - password auth, returns access + refresh tokens
- `POST /auth/refresh` - refresh access token (with rotation)
- `POST /auth/logout` - logout (future: token blacklist)
- `GET /auth/me` - get current user info
- All endpoints include rate limiting

## Environment Variables Required

```bash
SECRET_KEY=your-secret-key-32-bytes
AUTH_PASSWORD_HASH=$2b$12$...  # bcrypt hash
JWT_SECRET=your-jwt-secret-32-bytes
JWT_ALGORITHM=HS256
JWT_ACCESS_EXPIRE_MINUTES=60
JWT_REFRESH_EXPIRE_DAYS=7
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=postgresql://user:pass@localhost/maxmeeting
```

## Generate Password Hash

```bash
python3 << 'PYTHON'
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], bcrypt__rounds=12)
password = "your-password-here"
print(pwd_context.hash(password))
PYTHON
```

## Security Features

1. **Token Rotation**: New refresh token on each refresh
2. **Rate Limiting**: Sliding window using Redis
3. **Audit Logging**: All auth events logged to database
4. **JWT Claims**: aud, iss, jti for validation
5. **BCrypt**: Cost factor 12 for password hashing

## Next Steps

1. Add Redis and database initialization to main.py
2. Create .env file with secrets
3. Run database migrations (audit_logs table)
4. Add token blacklist for logout
5. Write integration tests

## API Usage

### Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"password": "your-password"}'
```

### Get Current User
```bash
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"
```

### Refresh Token
```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Authorization: Bearer <refresh_token>"
```

### Logout
```bash
curl -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Authorization: Bearer <access_token>"
```
