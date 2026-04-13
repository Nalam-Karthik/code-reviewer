# flask-api/app/services/memory.py

import os
import logging
import chromadb
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)

# ChromaDB runs in its own container
# HttpClient connects to it over the Docker network
_client     = None
_collection = None


def get_collection():
    """
    Get or create the ChromaDB collection.
    A collection is like a table — stores embeddings + metadata.
    """
    global _client, _collection

    if _collection is None:
        _client = chromadb.HttpClient(
            host=os.getenv("CHROMADB_HOST", "chromadb"),
            port=int(os.getenv("CHROMADB_PORT", "8000"))
        )

        # Use ChromaDB's built-in sentence transformer for embeddings
        # This converts text → a list of numbers (the embedding vector)
        # Similar text → similar vectors → findable by similarity search
        embed_fn = embedding_functions.DefaultEmbeddingFunction()

        _collection = _client.get_or_create_collection(
            name="code_reviews",
            embedding_function=embed_fn,
            metadata={"hnsw:space": "cosine"}  # cosine similarity = good for text
        )

    return _collection


def store_review_embedding(
    review_id: int,
    user_id: int,
    language: str,
    code: str,
    summary: str,
    score: int
):
    """
    Store a review in ChromaDB as an embedding.

    What gets embedded: the code + summary together.
    This means "find me reviews similar to THIS code that got THIS kind of feedback."

    Args:
        review_id: MySQL review ID (used as ChromaDB document ID)
        user_id:   stored as metadata for per-user filtering
        language:  stored as metadata for filtering by language
        code:      the actual code submitted
        summary:   AI's summary of the review
        score:     severity score
    """
    try:
        collection = get_collection()

        # The text we embed = code + summary
        # This gives semantic meaning to both what the code looks like
        # AND what kind of issues it has
        document = f"Language: {language}\nCode:\n{code}\nReview summary: {summary}"

        collection.add(
            ids       =[str(review_id)],   # must be string, must be unique
            documents =[document],
            metadatas =[{
                "user_id":  str(user_id),
                "language": language,
                "score":    score or 0,
                "review_id": review_id
            }]
        )
        logger.info(f"Stored embedding for review_id={review_id}")

    except Exception as e:
        # Don't crash the API if ChromaDB fails — log and continue
        logger.warning(f"ChromaDB store failed: {e}")


def get_similar_past_reviews(user_id: int, language: str, code: str, n=3) -> list:
    """
    Find the N most similar past reviews for this user.

    This is what creates "memory" — the AI gets told:
    "Here are 3 similar code snippets this user submitted before
    and what issues they had. Use this context."

    Args:
        user_id:  only look at THIS user's past reviews
        language: filter by same language
        code:     the new code being reviewed
        n:        how many similar reviews to return (default 3)

    Returns:
        List of dicts with past review summaries and scores
    """
    try:
        collection = get_collection()

        # Check if collection has any documents first
        if collection.count() == 0:
            return []

        results = collection.query(
            query_texts=[code],          # find embeddings similar to this code
            n_results=min(n, collection.count()),
            where={                      # filter: only this user's reviews
                "$and": [
                    {"user_id":  {"$eq": str(user_id)}},
                    {"language": {"$eq": language}}
                ]
            }
        )

        # results["documents"] is a list of lists — flatten it
        past_reviews = []
        if results["documents"] and results["documents"][0]:
            for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
                past_reviews.append({
                    "summary":   doc,
                    "score":     meta.get("score"),
                    "review_id": meta.get("review_id")
                })

        return past_reviews

    except Exception as e:
        logger.warning(f"ChromaDB query failed: {e}")
        return []