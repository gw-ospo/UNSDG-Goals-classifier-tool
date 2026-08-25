"""
embedder.py
~~~~~~~~~~~

One shared sentence-transformers embedder for the whole process.

`embedding_url` and `services.recommendation_pipeline` previously each kept
their own module-level `_embedder` global and each constructed
`all-mpnet-base-v2`. They run in the same Flask process, so that was two copies
of identical weights (~420 MB each) resident for the process lifetime.

Loading stays lazy: importing this module costs nothing, and the weights are
only fetched the first time something actually needs an embedding.
"""

from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"

_embedder = None


def get_embedder():
    """Return the process-wide embedder, constructing it on first use."""
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(MODEL_NAME)
    return _embedder
