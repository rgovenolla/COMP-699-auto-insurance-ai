class TokenCache:
    """Simple in-memory cache for classification results."""

    def __init__(self):
        self._cache = {}

    def get(self, key: str):
        """Retrieve a cached result."""
        return self._cache.get(key)

    def store(self, key: str, value: dict):
        """Store a result in the cache."""
        self._cache[key] = value

    def clear(self):
        """Clear all cached results."""
        self._cache = {}
