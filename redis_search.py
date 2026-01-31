# redis_search.py

import numpy as np
import redis
from sentence_transformers import SentenceTransformer
from redis.commands.search.query import Query
from config import *
import re

_model = SentenceTransformer(MODEL_NAME)
_redis = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=False)

def highlight_query(text: str, query: str) -> str:
    """
    Highlight query inside text using Markdown bold.
    Case-insensitive, OCR-safe.
    """
    if not query.strip():
        return text

    pattern = re.compile(re.escape(query), re.IGNORECASE)
    return pattern.sub(lambda m: f"**{m.group(0)}**", text)

def keyword_file_search(query_text: str):
    """
    Find ALL files where the query appears at least once.
    Returns ONE matching line per file.
    """

    query_lower = query_text.lower()
    seen_files = set()
    results = []

    # Scan all Redis keys for this index prefix
    cursor = 0
    while True:
        cursor, keys = _redis.scan(
            cursor=cursor,
            match=f"{REDIS_PREFIX}*",
            count=500
        )

        for key in keys:
            doc = _redis.hgetall(key)

            if not doc:
                continue

            filename = doc[b"filename"].decode()
            text = doc[b"text"].decode()
            file_location = doc[b"file_location"].decode()

            if filename in seen_files:
                continue

            # Split into lines (robust for OCR)
            lines = re.split(r"[.\n]", text)

            for line in lines:
                if query_lower in line.lower():
                    results.append({
                        "filename": filename,
                        "matched_line": line.strip(),
                        "file_location": file_location
                    })
                    seen_files.add(filename)
                    break  # stop after first match per file

        if cursor == 0:
            break

    return results

def hybrid_search(query_text, region=None, complaint_type=None, top_k=5):
    query_vector = _model.encode([query_text]).astype(np.float32).tobytes()

    base_query = "*"
    search_query = f"{base_query}=>[KNN {top_k} @embedding $vec AS score]"

    results = _redis.ft(INDEX_NAME).search(
        Query(search_query)
        .return_fields(
            "text",
            "filename",
            "file_location",
            "lang",
            "score"
        )
        .sort_by("score")
        .dialect(2),
        query_params={"vec": query_vector},
    )

    return [
        {
            "filename": d.filename,
            "text": d.text,
            "file_location": d.file_location,
            "lang": d.lang,
            "score": float(d.score),
        }
        for d in results.docs
    ]
