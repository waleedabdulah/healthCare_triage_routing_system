"""
One-time RAG knowledge base ingestion pipeline.
Loads raw documents → chunks → embeds → stores in ChromaDB.
Run: python -m src.rag.ingestion_pipeline
"""
import os
import json
import re
import hashlib
from pathlib import Path
from src.rag.vector_store import get_vector_store
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RAW_DATA_DIR = Path("data/raw")
CHUNK_SIZE = 400        # tokens (approximated by chars/4)
CHUNK_OVERLAP = 75


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks by approximate token count."""
    char_size = chunk_size * 4
    char_overlap = overlap * 4
    chunks = []
    start = 0
    while start < len(text):
        end = start + char_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start += char_size - char_overlap
    return chunks


def _extract_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML-style frontmatter from markdown files."""
    metadata = {}
    body = content

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter_text = parts[1]
            body = parts[2].strip()
            for line in frontmatter_text.strip().splitlines():
                if ":" in line:
                    key, _, value = line.partition(":")
                    key = key.strip()
                    value = value.strip()
                    # Parse list values like [a, b, c]
                    if value.startswith("["):
                        value = [v.strip().strip("'\"") for v in value.strip("[]").split(",")]
                    metadata[key] = value
    return metadata, body


def ingest_markdown_file(filepath: Path, store) -> int:
    """Load, chunk, and ingest a single markdown file. Returns chunk count."""
    content = filepath.read_text(encoding="utf-8")
    metadata, body = _extract_frontmatter(content)

    department = metadata.get("department", "General Medicine")
    urgency_category = metadata.get("urgency_category", "NON_URGENT")
    keywords = metadata.get("symptom_keywords", [])

    # Convert keywords list to string for ChromaDB metadata (must be str/int/float/bool)
    keywords_str = ", ".join(keywords) if isinstance(keywords, list) else str(keywords)

    chunks = _chunk_text(body)
    ids, texts, metas = [], [], []

    for i, chunk in enumerate(chunks):
        chunk_id = hashlib.md5(f"{filepath.stem}_{i}_{chunk[:50]}".encode()).hexdigest()
        ids.append(chunk_id)
        texts.append(chunk)
        metas.append({
            "source_file": filepath.name,
            "department": department,
            "urgency_category": urgency_category,
            "symptom_keywords": keywords_str,
            "chunk_index": i,
        })

    store.add_documents(ids=ids, texts=texts, metadatas=metas)
    logger.info(f"  ✓ {filepath.name} → {len(chunks)} chunks ingested")
    return len(chunks)


def ingest_json_file(filepath: Path, store) -> int:
    """Flatten department JSON into text chunks and ingest."""
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    ids, texts, metas = [], [], []

    departments = data.get("departments", {})
    for dept_name, dept_info in departments.items():
        text = (
            f"Department: {dept_name}\n"
            f"Scope: {dept_info.get('scope', '')}\n"
            f"Typical conditions: {', '.join(dept_info.get('typical_conditions', []))}\n"
            f"Primary symptoms: {', '.join(dept_info.get('primary_symptoms', []))}\n"
            f"Location: {dept_info.get('location', '')}, Floor {dept_info.get('floor', '')}\n"
        )
        chunk_id = hashlib.md5(f"dept_{dept_name}".encode()).hexdigest()
        ids.append(chunk_id)
        texts.append(text)
        metas.append({
            "source_file": filepath.name,
            "department": dept_name,
            "urgency_category": "NON_URGENT",
            "symptom_keywords": ", ".join(dept_info.get("primary_symptoms", [])),
            "chunk_index": 0,
        })

    store.add_documents(ids=ids, texts=texts, metadatas=metas)
    logger.info(f"  ✓ {filepath.name} → {len(ids)} department entries ingested")
    return len(ids)


def run_ingestion():
    logger.info("=" * 60)
    logger.info("Healthcare Triage RAG Ingestion Pipeline")
    logger.info("=" * 60)

    store = get_vector_store()
    total_chunks = 0

    # Ingest all markdown files
    md_files = sorted(RAW_DATA_DIR.glob("*.md"))
    logger.info(f"\nFound {len(md_files)} markdown protocol files:")
    for filepath in md_files:
        total_chunks += ingest_markdown_file(filepath, store)

    # Ingest JSON files
    json_files = sorted(RAW_DATA_DIR.glob("*.json"))
    logger.info(f"\nFound {len(json_files)} JSON data files:")
    for filepath in json_files:
        total_chunks += ingest_json_file(filepath, store)

    logger.info(f"\n{'='*60}")
    logger.info(f"Ingestion complete — {total_chunks} total chunks in ChromaDB")
    logger.info(f"Collection size: {store.count()} documents")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    run_ingestion()
