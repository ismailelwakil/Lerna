"""
Artifact Download Routes (SVG, PPTX, Documents)
"""
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/artifacts", tags=["Artifacts"])

# Candidate directories where generated artifacts reside
CANDIDATE_DIRS = [
    Path(__file__).resolve().parent.parent.parent / "ai-service" / "data" / "artifacts",
    Path(__file__).resolve().parent.parent.parent / "data" / "artifacts",
    Path("/home/user/academic-os/data/artifacts"),
    Path("./data/artifacts"),
]


@router.get("/{artifact_id}/download")
def download_artifact(artifact_id: str):
    """
    Download a generated artifact (e.g., SVG diagram, PPTX presentation).
    Serves with proper MIME types and headers.
    """
    clean_id = os.path.basename(artifact_id)
    target_file = None

    for candidate_dir in CANDIDATE_DIRS:
        check_path = candidate_dir / clean_id
        if check_path.exists() and check_path.is_file():
            target_file = check_path
            break

    if not target_file:
        raise HTTPException(
            status_code=404,
            detail=f"Artifact '{artifact_id}' not found. It may have expired or not finished generating.",
        )

    ext = target_file.suffix.lower()
    media_type = "application/octet-stream"
    if ext == ".svg":
        media_type = "image/svg+xml"
    elif ext == ".pptx":
        media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    elif ext == ".pdf":
        media_type = "application/pdf"
    elif ext == ".docx":
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    return FileResponse(
        path=str(target_file),
        media_type=media_type,
        filename=clean_id,
    )
