# config.py

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

REDIS_HOST = "localhost"
REDIS_PORT = 6379

INDEX_NAME = "orders_idx"
REDIS_PREFIX = "doc:"

PDF_DIR = os.path.join(BASE_DIR, "data", "pdfs")

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
VECTOR_DIM = 384
