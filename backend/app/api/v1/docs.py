"""
Documentation API Endpoints
Serves markdown documentation files from docs/ folder
"""

from fastapi import APIRouter, HTTPException, status
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

DOCS_DIR = Path(__file__).parent.parent.parent.parent.parent / "docs"


@router.get("/list")
async def list_documentation():
    """
    List all available documentation files
    """
    try:
        if not DOCS_DIR.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Documentation directory not found"
            )

        docs = []
        for doc_file in DOCS_DIR.glob("*.md"):
            # Read first line as title
            try:
                with open(doc_file, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    # Remove markdown heading symbols
                    title = first_line.lstrip('#').strip()
            except:
                title = doc_file.stem.replace('_', ' ').title()

            docs.append({
                "filename": doc_file.name,
                "title": title,
                "path": f"/api/v1/docs/{doc_file.name}"
            })

        # Sort by filename
        docs.sort(key=lambda x: x['filename'])

        return {
            "docs": docs,
            "total": len(docs)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing documentation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list documentation: {str(e)}"
        )


@router.get("/{filename}")
async def get_documentation(filename: str):
    """
    Get documentation file content by filename

    Examples:
    - /api/v1/docs/QUICK_INSTALL.md
    - /api/v1/docs/PHASE1_SETUP.md
    - /api/v1/docs/FREESCOUT_INTEGRATION.md
    """
    try:
        # Security: only allow .md files and no path traversal
        if not filename.endswith('.md') or '/' in filename or '\\' in filename or '..' in filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid filename. Only .md files are allowed."
            )

        doc_path = DOCS_DIR / filename

        if not doc_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Documentation file '{filename}' not found"
            )

        # Read file content
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()

        return {
            "filename": filename,
            "content": content,
            "size": len(content)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading documentation file {filename}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read documentation: {str(e)}"
        )
