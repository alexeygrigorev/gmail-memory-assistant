"""Persistent memory for the agent, stored in a local vector database.

The pattern comes from the Agent Memory Hub:
https://github.com/actian-devs/agent-memory-hub

Every memory is one short sentence about the user. We turn it into an
embedding and store it in VectorAI DB together with the user id. Later
we can find the memories that are relevant to a new question with a
similarity search.
"""

import hashlib

from actian_vectorai import (
    Distance,
    Field,
    FilterBuilder,
    PointStruct,
    VectorAIClient,
    VectorParams,
)
from sentence_transformers import SentenceTransformer

DB_ADDRESS = "localhost:6574"
COLLECTION = "email_drafting_memories"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_SIZE = 384
USER_ID = "alexey"

model = SentenceTransformer(EMBEDDING_MODEL)


def embed(text: str) -> list[float]:
    """Turn a sentence into a list of 384 numbers."""
    return model.encode(text).tolist()


def ensure_collection(client: VectorAIClient) -> None:
    """Create the collection once; do nothing when it already exists."""
    vectors = VectorParams(size=EMBEDDING_SIZE, distance=Distance.Cosine)
    client.collections.get_or_create(COLLECTION, vectors_config=vectors)


def point_id(content: str) -> int:
    """A stable id: the same sentence always maps to the same number.

    Saving the same fact twice then just overwrites the old copy
    instead of creating a duplicate.
    """
    digest = hashlib.sha256(content.encode()).hexdigest()
    return int(digest[:15], 16)


def remember(content: str, category: str = "general", rule: str = "") -> None:
    """Save a scoped drafting rule; the same rule key replaces an older version."""
    point = PointStruct(
        id=point_id(f"{USER_ID}:{category}:{rule or content}"),
        vector=embed(f"{category}: {content}"),
        payload={"user_id": USER_ID, "category": category, "content": content},
    )
    with VectorAIClient(DB_ADDRESS) as client:
        ensure_collection(client)
        client.points.upsert(COLLECTION, [point])


def recall(query: str, limit: int = 5) -> list[str]:
    """Return the stored memories most relevant to the query."""
    with VectorAIClient(DB_ADDRESS) as client:
        ensure_collection(client)
        user_filter = FilterBuilder().must(Field("user_id").eq(USER_ID)).build()
        points = client.points.search(
            COLLECTION,
            vector=embed(query),
            limit=limit,
            filter=user_filter,
        )
    memories = []
    for point in points:
        memories.append(f"[{point.payload.get('category', 'general')}] {point.payload['content']}")
    return memories
