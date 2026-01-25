# features/__init__.py
"""
Feature engineering package for MovieLens recommender.

Modules:
- utils.py: I/O, dtype helpers, GPU detection
- config.py: default paths and constants
- build_user_features.py: user aggregate features
- build_item_features.py: item aggregate features
"""
__all__ = [
    "config",
    "build_user_features",
    "build_item_features",
]
