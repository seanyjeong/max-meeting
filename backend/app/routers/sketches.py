"""Sketch management endpoints."""

from typing import Annotated
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models.note import Sketch

router = APIRouter(prefix="/sketches", tags=["sketches"])


@router.get("/{sketch_id}/export")
async def export_sketch(
    sketch_id: int,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    format: str = Query("png", pattern="^(png|pdf)$"),
):
    """스케치를 PNG 또는 PDF로 내보내기"""
    sketch = await db.get(Sketch, sketch_id)
    if not sketch:
        raise HTTPException(status_code=404, detail="스케치를 찾을 수 없습니다")

    # 썸네일 파일이 있으면 반환
    if sketch.thumbnail_path:
        settings = get_settings()
        ALLOWED_SKETCH_DIR = Path(settings.STORAGE_PATH) / "sketches"

        # 보안: 경로 순회 공격 방지 - STORAGE_PATH/sketches 내부만 허용
        file_path = (ALLOWED_SKETCH_DIR / sketch.thumbnail_path).resolve()

        # 실제 경로가 허용된 디렉토리 내부에 있는지 검증
        if not str(file_path).startswith(str(ALLOWED_SKETCH_DIR.resolve())):
            raise HTTPException(status_code=403, detail="Access denied")

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="썸네일 파일을 찾을 수 없습니다")

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

    # 썸네일이 없으면 JSON 데이터만 반환 (프론트에서 렌더링)
    return {"json_data": sketch.json_data, "format": format}
