"""
Transcript loader with deterministic discovery, LangChain documents, and rich logging.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

from langchain_core.documents import Document

from core_engine.logging import get_logger, log_progress


def discover_transcripts(
    root_path: Path,
    glob: str = "**/*.txt",
    min_bytes: int = 10,
    workspace_id: Optional[str] = None,
) -> List[Path]:
    """
    Recursively discover transcript files, sorted deterministically.
    Skips files smaller than `min_bytes`.
    """
    logger = get_logger("core_engine.ingestion", workspace_id=workspace_id)
    root_path = root_path.expanduser().resolve()
    if not root_path.exists():
        logger.error("root_path_not_found", extra={"context": {"root": str(root_path)}})
        return []

    paths = sorted([p for p in root_path.glob(glob) if p.is_file()])
    filtered: List[Path] = []
    for p in paths:
        size = p.stat().st_size
        if size < min_bytes:
            logger.warning(
                "skip_too_small",
                extra={"context": {"file": str(p), "size": size, "min_bytes": min_bytes}},
            )
            continue
        filtered.append(p)

    logger.info(
        "discovery_complete",
        extra={"context": {"root": str(root_path), "found": len(paths), "kept": len(filtered)}},
    )
    return filtered


def filename_to_episode_id(path: Path) -> str:
    """
    Derive a stable episode_id from filename.
    Example: '001_PHIL_JACKSON.txt' -> '001_PHIL_JACKSON'
    """
    stem = path.stem
    normalized = stem.replace(" ", "_")
    return normalized


def read_text(path: Path) -> str:
    """
    Read text with UTF-8 fallback to latin-1.
    """
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")


def build_metadata(path: Path, workspace_id: Optional[str]) -> Dict:
    stat = path.stat()
    return {
        "episode_id": filename_to_episode_id(path),
        "source_path": str(path),
        "workspace_id": workspace_id,
        "file_size": stat.st_size,
        "modified_time": stat.st_mtime,
        # placeholders; can be filled downstream if available
        "speaker": None,
        "timestamp": None,
    }


def load_with_langchain(
    paths: List[Path],
    workspace_id: Optional[str] = None,
) -> List[Document]:
    """
    Create LangChain Document objects with our metadata.
    Uses manual read for encoding fallback; keeps deterministic order.
    """
    logger = get_logger("core_engine.ingestion", workspace_id=workspace_id)
    docs: List[Document] = []
    total = len(paths)
    for idx, path in enumerate(paths, start=1):
        try:
            text = read_text(path)
            metadata = build_metadata(path, workspace_id)
            doc = Document(page_content=text, metadata=metadata)
            docs.append(doc)
            log_progress(
                logger,
                stage="load",
                message="loaded_transcript",
                index=idx,
                total=total,
                file=str(path),
                episode_id=metadata["episode_id"],
                size=metadata["file_size"],
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "load_failed",
                exc_info=True,
                extra={"context": {"file": str(path), "error": str(exc)}},
            )

    logger.info(
        "load_complete",
        extra={"context": {"total": total, "loaded": len(docs)}},
    )
    return docs


def load_transcripts(
    root_path: Path,
    workspace_id: Optional[str] = None,
    glob: str = "**/*.txt",
    min_bytes: int = 10,
) -> List[Document]:
    """
    Orchestrator: discover -> load -> return LangChain Documents.
    """
    paths = discover_transcripts(root_path, glob=glob, min_bytes=min_bytes, workspace_id=workspace_id)
    return load_with_langchain(paths, workspace_id=workspace_id)

