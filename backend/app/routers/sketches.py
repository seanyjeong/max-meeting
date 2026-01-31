"""Sketch management endpoints."""

import base64
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models.meeting import Meeting
from app.models.note import Sketch
from app.schemas.sketch import SketchCreate, SketchListResponse, SketchResponse

router = APIRouter(tags=["sketches"])


async def get_meeting_or_raise(db: AsyncSession, meeting_id: int) -> Meeting:
    """Get meeting by ID or raise 404."""
    meeting = await db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="회의를 찾을 수 없습니다",
        )
    return meeting


async def get_sketch_or_raise(db: AsyncSession, sketch_id: int) -> Sketch:
    """Get sketch by ID or raise 404."""
    sketch = await db.get(Sketch, sketch_id)
    if not sketch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="스케치를 찾을 수 없습니다",
        )
    return sketch


# ============================================
# Meeting Sketch Endpoints
# ============================================


@router.get("/meetings/{meeting_id}/sketches", response_model=SketchListResponse)
async def list_sketches(
    meeting_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """List all sketches for a meeting."""
    await get_meeting_or_raise(db, meeting_id)

    result = await db.execute(
        select(Sketch)
        .where(Sketch.meeting_id == meeting_id)
        .order_by(Sketch.timestamp_seconds.asc().nullslast(), Sketch.created_at)
    )
    sketches = result.scalars().all()

    return SketchListResponse(
        data=[SketchResponse.model_validate(sketch) for sketch in sketches],
        meta={"total": len(sketches)},
    )


@router.post(
    "/meetings/{meeting_id}/sketches",
    response_model=SketchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_sketch(
    meeting_id: int,
    data: SketchCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Create a new sketch for a meeting with PNG image."""
    await get_meeting_or_raise(db, meeting_id)
    settings = get_settings()

    # Decode base64 image data
    try:
        # Remove data URL prefix if present
        image_data = data.image_data
        if image_data.startswith("data:"):
            image_data = image_data.split(",", 1)[1]
        image_bytes = base64.b64decode(image_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"잘못된 이미지 데이터입니다: {str(e)}",
        )

    # Create storage directory
    sketch_dir = Path(settings.STORAGE_PATH) / "sketches" / str(meeting_id)
    sketch_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"sketch_{timestamp}_{uuid.uuid4().hex[:8]}.png"
    file_path = sketch_dir / filename

    # Save PNG file
    with open(file_path, "wb") as f:
        f.write(image_bytes)

    # Store relative path in database
    relative_path = f"{meeting_id}/{filename}"

    sketch = Sketch(
        meeting_id=meeting_id,
        agenda_id=data.agenda_id,
        timestamp_seconds=data.timestamp_seconds,
        thumbnail_path=relative_path,
    )
    db.add(sketch)
    await db.commit()
    await db.refresh(sketch)

    return SketchResponse.model_validate(sketch)


# ============================================
# Sketch Endpoints (by ID)
# ============================================


@router.get("/sketches/{sketch_id}", response_model=SketchResponse)
async def get_sketch(
    sketch_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Get a specific sketch by ID."""
    sketch = await get_sketch_or_raise(db, sketch_id)
    return SketchResponse.model_validate(sketch)


@router.delete("/sketches/{sketch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sketch(
    sketch_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Delete a sketch."""
    sketch = await get_sketch_or_raise(db, sketch_id)
    settings = get_settings()

    # Delete file if exists
    if sketch.thumbnail_path:
        file_path = Path(settings.STORAGE_PATH) / "sketches" / sketch.thumbnail_path
        if file_path.exists():
            file_path.unlink()

    await db.delete(sketch)
    await db.commit()


@router.get("/sketches/{sketch_id}/image")
async def get_sketch_image(
    sketch_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Get sketch image file."""
    sketch = await get_sketch_or_raise(db, sketch_id)

    if not sketch.thumbnail_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="스케치 이미지가 없습니다",
        )

    settings = get_settings()
    ALLOWED_SKETCH_DIR = Path(settings.STORAGE_PATH) / "sketches"

    # Security: path traversal prevention
    file_path = (ALLOWED_SKETCH_DIR / sketch.thumbnail_path).resolve()
    if not str(file_path).startswith(str(ALLOWED_SKETCH_DIR.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="스케치 파일을 찾을 수 없습니다",
        )

    def iterfile():
        with open(file_path, "rb") as f:
            yield from f

    return StreamingResponse(
        iterfile(),
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=31536000"},
    )


@router.get("/sketches/{sketch_id}/export")
async def export_sketch(
    sketch_id: int,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    format: str = Query("png", pattern="^(png|pdf)$"),
):
    """Export sketch as PNG or PDF."""
    sketch = await get_sketch_or_raise(db, sketch_id)

    if sketch.thumbnail_path:
        settings = get_settings()
        ALLOWED_SKETCH_DIR = Path(settings.STORAGE_PATH) / "sketches"

        # Security: path traversal prevention
        file_path = (ALLOWED_SKETCH_DIR / sketch.thumbnail_path).resolve()
        if not str(file_path).startswith(str(ALLOWED_SKETCH_DIR.resolve())):
            raise HTTPException(status_code=403, detail="Access denied")

        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="스케치 파일을 찾을 수 없습니다",
            )

        if format == "png":
            media_type = "image/png"
        else:
            media_type = "application/pdf"

        def iterfile():
            with open(file_path, "rb") as f:
                yield from f

        return StreamingResponse(
            iterfile(),
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="sketch_{sketch_id}.{format}"'
            },
        )

    # If no thumbnail, return JSON data (frontend can render)
    return {"json_data": sketch.json_data, "format": format}
