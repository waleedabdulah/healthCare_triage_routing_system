"""
Run this script ONCE after setup to populate ChromaDB with triage protocols.
Usage: python scripts/ingest_knowledge_base.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.ingestion_pipeline import run_ingestion

if __name__ == "__main__":
    run_ingestion()
