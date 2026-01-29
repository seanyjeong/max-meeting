"""Audit logging middleware."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession


class AuditLogger:
    """Audit logger for security events."""

    @staticmethod
    async def log(
        db: AsyncSession,
        event_type: str,
        user_id: Optional[int],
        action: str,
        status: str,
        request: Request,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        details: Optional[dict] = None,
    ):
        """Log an audit event."""
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

        audit_log = {
            "timestamp": datetime.now(timezone.utc),
            "event_type": event_type,
            "user_id": user_id,
            "ip_address": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "resource_type": resource_type,
            "resource_id": resource_id,
            "action": action,
            "status": status,
            "details": details,
            "request_id": request_id,
        }

        from sqlalchemy import text

        await db.execute(
            text("""
                INSERT INTO audit_logs
                (timestamp, event_type, user_id, ip_address, user_agent,
                 resource_type, resource_id, action, status, details, request_id)
                VALUES
                (:timestamp, :event_type, :user_id, :ip_address, :user_agent,
                 :resource_type, :resource_id, :action::audit_action,
                 :status::audit_status, :details::jsonb, :request_id::uuid)
            """),
            audit_log
        )

        await db.commit()


async def audit_middleware(request: Request, call_next):
    """Middleware to add audit logging capabilities."""
    request.state.request_id = str(uuid.uuid4())

    response = await call_next(request)

    response.headers["X-Request-ID"] = request.state.request_id

    return response
