import faiss
import numpy as np
import json
import os
# Offline mode only when explicitly set (local dev with no internet).
# CI and first-run need online access to download the model.
if os.environ.get("TALENTAI_OFFLINE") == "1":
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
from sentence_transformers import SentenceTransformer

# Load embedding model once at startup (downloads ~90MB first time)
print("⏳ Loading embedding model...")
model = SentenceTransformer("all-MiniLM-L6-v2")
print("✅ Embedding model loaded!")

FAISS_DIR = "faiss_index"
INDEX_PATH = os.path.join(FAISS_DIR, "resumes.index")
META_PATH = os.path.join(FAISS_DIR, "meta.json")


def get_embedding(text: str) -> np.ndarray:
    """Convert text to a 384-dimension vector"""
    return model.encode([text])[0].astype("float32")


def build_index(resume_texts: list, resume_ids: list):
    """Build FAISS index from all resumes"""
    if not resume_texts:
        return False

    os.makedirs(FAISS_DIR, exist_ok=True)

    embeddings = np.array([get_embedding(t) for t in resume_texts])
    dim = embeddings.shape[1]  # 384

    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    faiss.write_index(index, INDEX_PATH)
    with open(META_PATH, "w") as f:
        json.dump(resume_ids, f)

    return True


def search_candidates(job_description: str, top_k: int = 10) -> list:
    """Find top matching resumes for a job description"""
    if not os.path.exists(INDEX_PATH):
        return []

    index = faiss.read_index(INDEX_PATH)
    with open(META_PATH) as f:
        resume_ids = json.load(f)

    if not resume_ids:
        return []

    query_vec = np.array([get_embedding(job_description)])
    k = min(top_k, len(resume_ids))
    distances, indices = index.search(query_vec, k)

    results = []
    for i, idx in enumerate(indices[0]):
        if 0 <= idx < len(resume_ids):
            # Convert L2 distance to a 0-100 similarity score
            dist = float(distances[0][i])
            similarity = round(100 / (1 + dist), 2)
            results.append({
                "resume_id": resume_ids[idx],
                "match_score": similarity
            })

    return sorted(results, key=lambda x: x["match_score"], reverse=True)