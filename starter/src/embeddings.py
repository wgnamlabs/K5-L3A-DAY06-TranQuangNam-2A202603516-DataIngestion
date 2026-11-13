"""Local text embeddings with the user's selected EmbeddingGemma 2 model."""

from __future__ import annotations

import math
from typing import Protocol


class Embedder(Protocol):
    model_name: str
    dimensions: int

    def embed_documents(self, texts: list[str], titles: list[str] | None = None) -> list[list[float]]:
        """Return one vector per input text, in the same order."""
        ...

    def embed_query(self, question: str) -> list[float]:
        """Return a query vector compatible with the stored document vectors."""
        ...


class MyEmbedder:
    """SentenceTransformers adapter using distinct document and QA query prefixes."""

    def __init__(self, model_name: str = "google/embeddinggemma-2", dimensions: int = 768,
                 batch_size: int = 16, revision: str | None = None) -> None:
        if model_name != "google/embeddinggemma-2":
            raise ValueError("This adapter is configured only for google/embeddinggemma-2")
        if dimensions not in (128, 256, 512, 768):
            raise ValueError("Unsupported EmbeddingGemma 2 dimension")
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        import torch
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self.revision = revision
        self.dimensions = dimensions
        self.batch_size = batch_size
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA GPU was selected for this lab, but PyTorch cannot access it")
        self.device = "cuda"
        dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float32
        self.dtype = str(dtype)
        self.model = SentenceTransformer(
            model_name,
            revision=revision,
            device=self.device,
            config_kwargs={"vision_config": None, "audio_config": None},
            model_kwargs={"torch_dtype": dtype},
        )

    def _encode(self, texts: list[str], *, prompt_name: str | None = None) -> list[list[float]]:
        if not texts:
            return []
        vectors = self.model.encode(
            texts,
            prompt_name=prompt_name,
            batch_size=self.batch_size,
            truncate_dim=self.dimensions,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=len(texts) > self.batch_size,
        )
        result = [[float(value) for value in vector] for vector in vectors]
        if any(len(vector) != self.dimensions or not all(math.isfinite(x) for x in vector)
               for vector in result):
            raise ValueError("Embedding model returned invalid vectors")
        return result

    def embed_documents(self, texts: list[str], titles: list[str] | None = None) -> list[list[float]]:
        if titles is not None and len(titles) != len(texts):
            raise ValueError("titles and texts have different lengths")
        formatted = [f"title: {title or 'none'} | text: {content}"
                     for title, content in zip(titles or [None] * len(texts), texts)]
        return self._encode(formatted)

    def embed_query(self, question: str) -> list[float]:
        if not question.strip():
            raise ValueError("question is empty")
        return self._encode([question], prompt_name="QuestionAnswering")[0]
