"""
Package de chunking RAG pour documents juridiques
==================================================
"""

__version__ = "1.0.0"
__author__ = "SALMA"

from .chunking_pipeline import RAGChunkingPipeline
from .config import Config

__all__ = ['RAGChunkingPipeline', 'Config']