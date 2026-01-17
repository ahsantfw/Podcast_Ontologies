"""
Chunking module with dialogue-aware splitting and deterministic sizing.
Uses LangChain RecursiveCharacterTextSplitter as a fallback for non-dialogue text.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from core_engine.logging import get_logger, log_progress


TIMESTAMP_LINE_RE = re.compile(r"^\s*\[(\d{2}:\d{2}:\d{2}(?:\.\d+)?)\]\s*-\s*([^\]]+)?", re.IGNORECASE)
SPEAKER_COLON_LINE_RE = re.compile(r"^\s*([A-Za-z][\w\.\-]{0,20})\s*:\s*(.*)$")


def detect_dialogue_markers(text: str) -> bool:
    """Heuristic to decide if text has speaker/timestamp structure."""
    # Require at least 3 real dialogue markers (speaker or timestamp)
    turns = split_into_turns(text)
    dialogue_count = sum(
        1 for t in turns if t.get("speaker") or t.get("timestamp")
    )
    return dialogue_count >= 3


def split_into_turns(text: str) -> List[Dict]:
    """
    Split text into speaker turns, capturing start/end char positions and optional timestamp.
    Handles two formats:
      1) [hh:mm:ss] - Speaker X
      2) XX: line-leading initials (e.g., RR:, PJ:, S1:)
    """
    turns: List[Dict] = []
    lines = text.splitlines(keepends=True)

    def flush(current):
        if current and current["text"].strip():
            turns.append(current)

    current = {"text": "", "speaker": None, "timestamp": None, "start_char": 0, "end_char": 0}
    offset = 0

    for line in lines:
        line_start = offset
        line_no_nl = line.rstrip("\n")
        ts_match = TIMESTAMP_LINE_RE.match(line)
        sp_match = None if ts_match else SPEAKER_COLON_LINE_RE.match(line)

        if ts_match:
            current["end_char"] = line_start
            flush(current)
            timestamp = ts_match.group(1)
            speaker = ts_match.group(2).strip() if ts_match.group(2) else None
            remainder = line[ts_match.end():].lstrip()
            current = {
                "text": remainder,
                "speaker": speaker,
                "timestamp": timestamp,
                "start_char": line_start,
                "end_char": line_start + len(remainder),
            }
        elif sp_match:
            current["end_char"] = line_start
            flush(current)
            speaker = sp_match.group(1).strip()
            remainder = sp_match.group(2)
            current = {
                "text": remainder,
                "speaker": speaker,
                "timestamp": None,
                "start_char": line_start,
                "end_char": line_start + len(remainder),
            }
        else:
            if current["text"]:
                current["text"] += "\n" + line
            else:
                current["text"] = line
            current["end_char"] = line_start + len(line_no_nl)

        offset += len(line)

    flush(current)
    return turns


def merge_turns(
    turns: List[Dict],
    target_chars: int,
    overlap_chars: int,
) -> List[Dict]:
    """
    Merge adjacent turns to reach target size, add overlap between consecutive chunks.
    """
    chunks: List[Dict] = []
    buf: List[Dict] = []
    buf_len = 0

    for turn in turns:
        tlen = len(turn["text"])
        if buf and buf_len + tlen > target_chars and buf_len > 0:
            # flush buffer
            chunk_text = "\n\n".join(t["text"] for t in buf)
            first_speaker = next((t.get("speaker") for t in buf if t.get("speaker")), None)
            first_ts = next((t.get("timestamp") for t in buf if t.get("timestamp")), None)
            speakers_in_chunk = list(dict.fromkeys([t.get("speaker") for t in buf if t.get("speaker")]))
            timestamps_in_chunk = list(dict.fromkeys([t.get("timestamp") for t in buf if t.get("timestamp")]))
            turns_meta = [
                {
                    "speaker": t.get("speaker"),
                    "timestamp": t.get("timestamp"),
                    "start_char": t.get("start_char"),
                    "end_char": t.get("end_char"),
                }
                for t in buf
            ]
            chunk = {
                "text": chunk_text,
                "speaker": first_speaker,
                "timestamp": first_ts,
                "speakers_in_chunk": speakers_in_chunk,
                "timestamps_in_chunk": timestamps_in_chunk,
                "turns": turns_meta,
                "start_char": buf[0].get("start_char"),
                "end_char": buf[-1].get("end_char"),
            }
            chunks.append(chunk)
            # start new buffer with overlap (simple char overlap from previous chunk end)
            buf = [turn]
            buf_len = tlen
        else:
            buf.append(turn)
            buf_len += tlen + 2  # account for separator

    if buf:
        chunk_text = "\n\n".join(t["text"] for t in buf)
        speakers_in_chunk = list(dict.fromkeys([t.get("speaker") for t in buf if t.get("speaker")]))
        timestamps_in_chunk = list(dict.fromkeys([t.get("timestamp") for t in buf if t.get("timestamp")]))
        turns_meta = [
            {
                "speaker": t.get("speaker"),
                "timestamp": t.get("timestamp"),
                "start_char": t.get("start_char"),
                "end_char": t.get("end_char"),
            }
            for t in buf
        ]
        chunk = {
            "text": chunk_text,
            "speaker": buf[0].get("speaker"),
            "timestamp": buf[0].get("timestamp"),
            "speakers_in_chunk": speakers_in_chunk,
            "timestamps_in_chunk": timestamps_in_chunk,
            "turns": turns_meta,
            "start_char": buf[0].get("start_char"),
            "end_char": buf[-1].get("end_char"),
        }
        chunks.append(chunk)

    # Store overlap in metadata only - DO NOT embed overlap text
    if overlap_chars > 0 and len(chunks) > 1:
        for i in range(1, len(chunks)):
            prev_tail = chunks[i - 1]["text"][-overlap_chars:]
            chunks[i]["overlap_text"] = prev_tail
            # Note: overlap_text is NOT added to "text" field to avoid re-embedding

    return chunks


def map_splits_to_offsets(text: str, splits: List[str]) -> List[Tuple[Optional[int], Optional[int]]]:
    """
    Map sequential splits back to start/end char offsets in the original text.
    Uses a forward search to align each split after the previous one.
    """
    positions: List[Tuple[Optional[int], Optional[int]]] = []
    cursor = 0
    for split in splits:
        if not split:
            positions.append((None, None))
            continue
        start = text.find(split, cursor)
        if start == -1:
            positions.append((None, None))
            continue
        end = start + len(split)
        positions.append((start, end))
        cursor = end
    return positions


# Constants for chunk quality control
MIN_CHARS_PER_CHUNK = 400  # Minimum chunk size to embed
MAX_CHARS_PER_CHUNK = 20000  # Maximum chunk size (safety for embedding API)
MAX_CHUNKS_PER_DOC = 80  # Safety cap per document


def chunk_text(
    text: str,
    base_metadata: Dict,
    target_chars: int = 2000,  # Increased from 1300 to reduce chunk count
    overlap_chars: int = 200,  # Increased proportionally
    workspace_id: Optional[str] = None,
    logger=None,
) -> List[Document]:
    """
    Chunk a single document, preserving speaker/timestamp when present.
    Enforces minimum chunk size and maximum chunks per document.
    """
    lg = logger or get_logger("core_engine.chunking", workspace_id=workspace_id)
    chunks: List[Document] = []

    # Try dialogue-aware chunking first
    turns = split_into_turns(text)
    has_dialogue = detect_dialogue_markers(text)

    if has_dialogue:
        merged = merge_turns(turns, target_chars=target_chars, overlap_chars=overlap_chars)
        for idx, m in enumerate(merged, start=0):
            # Enforce minimum chunk size - skip tiny chunks
            chunk_text_content = m["text"].strip()
            if len(chunk_text_content) < MIN_CHARS_PER_CHUNK:
                continue
            
            # If chunk is too large, split it further using RecursiveCharacterTextSplitter
            if len(chunk_text_content) > MAX_CHARS_PER_CHUNK:
                lg.warning(
                    "chunk_too_large",
                    extra={
                        "context": {
                            "file": base_metadata.get("source_path"),
                            "size": len(chunk_text_content),
                            "max": MAX_CHARS_PER_CHUNK,
                        }
                    },
                )
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=target_chars,
                    chunk_overlap=overlap_chars,
                    separators=["\n\n", "\n", ". ", " "],
                )
                sub_splits = splitter.split_text(chunk_text_content)
                for sub_idx, sub_split in enumerate(sub_splits):
                    if len(sub_split.strip()) < MIN_CHARS_PER_CHUNK:
                        continue
                    metadata = dict(base_metadata)
                    metadata.update({
                        "chunk_index": len(chunks),
                        "speaker": m.get("speaker"),
                        "timestamp": m.get("timestamp"),
                        "speakers_in_chunk": m.get("speakers_in_chunk", []),
                        "timestamps_in_chunk": m.get("timestamps_in_chunk", []),
                        "turns": m.get("turns", []),
                        "start_char": m.get("start_char"),
                        "end_char": m.get("end_char"),
                        "overlap_text": m.get("overlap_text"),
                    })
                    doc = Document(page_content=sub_split.strip(), metadata=metadata)
                    chunks.append(doc)
                    log_progress(
                        lg,
                        stage="chunk",
                        message="chunk_created",
                        index=len(chunks),
                        total=len(merged),
                        file=metadata.get("source_path"),
                        episode_id=metadata.get("episode_id"),
                        chunk_index=len(chunks) - 1,
                    )
            else:
                metadata = dict(base_metadata)
                metadata.update({
                    "chunk_index": len(chunks),
                    "speaker": m.get("speaker"),
                    "timestamp": m.get("timestamp"),
                    "speakers_in_chunk": m.get("speakers_in_chunk", []),
                    "timestamps_in_chunk": m.get("timestamps_in_chunk", []),
                    "turns": m.get("turns", []),
                    "start_char": m.get("start_char"),
                    "end_char": m.get("end_char"),
                    "overlap_text": m.get("overlap_text"),  # Store overlap separately, not in page_content
                })
                # Only embed the main text, NOT overlap_text
                doc = Document(page_content=chunk_text_content, metadata=metadata)
                chunks.append(doc)
                log_progress(
                    lg,
                    stage="chunk",
                    message="chunk_created",
                    index=len(chunks),
                    total=len(merged),
                    file=metadata.get("source_path"),
                    episode_id=metadata.get("episode_id"),
                    chunk_index=len(chunks) - 1,
                )
    else:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=target_chars,
            chunk_overlap=overlap_chars,
            separators=["\n\n", "\n", ". ", " "],
        )
        splits = splitter.split_text(text)
        offsets = map_splits_to_offsets(text, splits)
        for idx, split in enumerate(splits, start=0):
            # Enforce minimum chunk size - skip tiny chunks
            split_text_content = split.strip()
            if len(split_text_content) < MIN_CHARS_PER_CHUNK:
                continue
            
            # If chunk is too large, split it further
            if len(split_text_content) > MAX_CHARS_PER_CHUNK:
                lg.warning(
                    "chunk_too_large",
                    extra={
                        "context": {
                            "file": base_metadata.get("source_path"),
                            "size": len(split_text_content),
                            "max": MAX_CHARS_PER_CHUNK,
                        }
                    },
                )
                # Re-split the oversized chunk
                sub_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=target_chars,
                    chunk_overlap=overlap_chars,
                    separators=["\n\n", "\n", ". ", " "],
                )
                sub_splits = sub_splitter.split_text(split_text_content)
                for sub_idx, sub_split in enumerate(sub_splits):
                    if len(sub_split.strip()) < MIN_CHARS_PER_CHUNK:
                        continue
                    metadata = dict(base_metadata)
                    start_char, end_char = offsets[idx]
                    metadata.update({
                        "chunk_index": len(chunks),
                        "speaker": None,
                        "timestamp": None,
                        "speakers_in_chunk": [],
                        "timestamps_in_chunk": [],
                        "turns": [],
                        "start_char": start_char,
                        "end_char": end_char,
                    })
                    doc = Document(page_content=sub_split.strip(), metadata=metadata)
                    chunks.append(doc)
                    log_progress(
                        lg,
                        stage="chunk",
                        message="chunk_created",
                        index=len(chunks),
                        total=len(splits),
                        file=metadata.get("source_path"),
                        episode_id=metadata.get("episode_id"),
                        chunk_index=len(chunks) - 1,
                    )
            else:
                metadata = dict(base_metadata)
                start_char, end_char = offsets[idx]
                metadata.update({
                    "chunk_index": len(chunks),
                    "speaker": None,
                    "timestamp": None,
                    "speakers_in_chunk": [],
                    "timestamps_in_chunk": [],
                    "turns": [],
                    "start_char": start_char,
                    "end_char": end_char,
                })
                doc = Document(page_content=split_text_content, metadata=metadata)
                chunks.append(doc)
                log_progress(
                    lg,
                    stage="chunk",
                    message="chunk_created",
                    index=len(chunks),
                    total=len(splits),
                    file=metadata.get("source_path"),
                    episode_id=metadata.get("episode_id"),
                    chunk_index=len(chunks) - 1,
                )
    
    # Safety cap: warn if too many chunks
    if len(chunks) > MAX_CHUNKS_PER_DOC:
        lg.warning(
            "too_many_chunks",
            extra={
                "context": {
                    "file": base_metadata.get("source_path"),
                    "count": len(chunks),
                    "max": MAX_CHUNKS_PER_DOC,
                }
            },
        )

    lg.info(
        "chunk_complete",
        extra={"context": {"file": base_metadata.get("source_path"), "chunks": len(chunks)}},
    )
    return chunks


def chunk_documents(
    docs: List[Document],
    target_chars: int = 2000,  # Increased from 1300 to reduce chunk count
    overlap_chars: int = 200,  # Increased proportionally
) -> List[Document]:
    """
    Chunk a list of LangChain Documents, preserving metadata and adding chunk-level fields.
    """
    all_chunks: List[Document] = []
    total_docs = len(docs)
    for i, doc in enumerate(docs, start=1):
        metadata = dict(doc.metadata)
        workspace_id = metadata.get("workspace_id")
        logger = get_logger("core_engine.chunking", workspace_id=workspace_id)
        logger.info(
            "chunk_start",
            extra={"context": {"file": metadata.get("source_path"), "doc_index": i, "total_docs": total_docs}},
        )
        chunks = chunk_text(
            doc.page_content,
            base_metadata=metadata,
            target_chars=target_chars,
            overlap_chars=overlap_chars,
            workspace_id=workspace_id,
            logger=logger,
        )
        all_chunks.extend(chunks)
    return all_chunks

