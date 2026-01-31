# encode.py

import os
import redis
import traceback
import psutil
import numpy as np
import unicodedata
import re

from sentence_transformers import SentenceTransformer
from pdf_ocr import extract_text_from_pdf

from redis.commands.search.field import VectorField, TextField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from config import *

# Text normalization
def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

# Language detection
def detect_lang(text: str, threshold=0.05) -> str:
    ml_chars, total_chars = 0, 0
    for ch in text:
        if ch.isalpha():
            total_chars += 1
            if "\u0D00" <= ch <= "\u0D7F":
                ml_chars += 1
    if total_chars == 0:
        return "en"
    return "ml" if (ml_chars / total_chars) >= threshold else "en"

# Redis
def get_redis():
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=False)
    r.ping()
    print("Connected to Redis Stack")
    return r

def create_index(r):
    try:
        r.ft(INDEX_NAME).info()
        print("Redis index already exists")
        return
    except Exception:
        pass

    schema = [
        TextField("filename"),
        TextField("text"),
        TextField("lang"),
        TextField("file_location"),
        VectorField(
            "embedding",
            "HNSW",
            {
                "TYPE": "FLOAT32",
                "DIM": VECTOR_DIM,
                "DISTANCE_METRIC": "COSINE"
            },
        ),
    ]

    r.ft(INDEX_NAME).create_index(
        schema,
        definition=IndexDefinition(
            prefix=[REDIS_PREFIX],
            index_type=IndexType.HASH
        ),
    )
    print("Redis index created")

def file_already_ingested(r, filename: str) -> bool:
    return r.exists(f"{REDIS_PREFIX}{filename}:0")

# Chunking
def chunk_text(text, max_chars=300):
    for i in range(0, len(text), max_chars):
        yield text[i:i + max_chars]

# Ingest PDFs
def ingest():
    r = get_redis()
    create_index(r)

    model = SentenceTransformer(MODEL_NAME)

    print("Reading PDFs from:", PDF_DIR)
    print("Files:", os.listdir(PDF_DIR))

    for pdf in os.listdir(PDF_DIR):
    if not pdf.lower().endswith(".pdf"):
        continue

    if file_already_ingested(r, pdf):
        print(f"Skipping already ingested file: {pdf}")
        continue

    pdf_path = os.path.join(PDF_DIR, pdf)
    relative_path = os.path.relpath(pdf_path, BASE_DIR)

    print(f"\nProcessing: {pdf}")

        try:
            raw_text = extract_text_from_pdf(pdf_path)
            if not raw_text or not raw_text.strip():
                print("No text extracted. Skipping.")
                continue

            text = normalize_text(raw_text)
            lang = detect_lang(text)
            print(f"Detected language: {lang}")

            for i, chunk in enumerate(chunk_text(text)):
                if psutil.virtual_memory().percent > 90:
                    print("High memory usage, skipping chunk")
                    continue

                vec = model.encode(
                    chunk,
                    convert_to_numpy=True,
                    normalize_embeddings=True
                ).astype(np.float32)

                r.hset(
                    f"{REDIS_PREFIX}{pdf}:{i}",
                    mapping={
                        "filename": pdf,
                        "text": chunk,
                        "lang": lang,
                        "file_location": relative_path,
                        "embedding": vec.tobytes(),
                    },
                )

            print(f"Finished {pdf}")

        except Exception:
            traceback.print_exc()

    print("\n🎉 Ingestion complete")

if __name__ == "__main__":
    ingest()
