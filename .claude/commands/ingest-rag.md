Run the ChromaDB RAG ingestion pipeline to populate or refresh the triage protocol knowledge base.

$ARGUMENTS

First, list available protocol files:
```bash
ls d:/AI_project/data/raw/
```

Check current collection size before ingestion:
```bash
cd d:/AI_project && .venv/Scripts/python.exe -c "
from src.rag.vector_store import get_vector_store
vs = get_vector_store()
print(f'Current ChromaDB document count: {vs.count()}')
"
```

Run the ingestion pipeline:
```bash
cd d:/AI_project && source .venv/Scripts/activate && python -m src.rag.ingestion_pipeline
```

Verify the new count after ingestion:
```bash
cd d:/AI_project && .venv/Scripts/python.exe -c "
import src.rag.vector_store as vsmod
vsmod.get_vector_store.cache_clear()
vs = vsmod.get_vector_store()
print(f'New ChromaDB document count: {vs.count()}')
"
```

If the argument contains `test` or `verify`, also run a test retrieval query:
```bash
cd d:/AI_project && .venv/Scripts/python.exe -c "
from src.rag.vector_store import get_vector_store
vs = get_vector_store()
results = vs.query('chest pain shortness of breath', n_results=3)
print('Test query: chest pain shortness of breath')
for r in results:
    print(f\"  {r['metadata']['source_file']} | {r['metadata']['department']} | {r['metadata']['urgency_category']} | dist={round(r['distance'],4)}\")
"
```

**Always remind the user:**
- `get_vector_store()` is `@lru_cache()` — the **running backend will NOT see new data until restarted**
- Run `/start-backend` (full restart) to pick up the re-ingested collection
- Ingestion uses `upsert` — safe to re-run at any time; existing chunks are overwritten by content hash ID
- New protocol files in `data/raw/` must have YAML frontmatter: `department`, `urgency_category`, `symptom_keywords`
