import logging

logger = logging.getLogger(__name__)

# Global memory cache store
GLOBAL_CACHE = {}


def get_cached_item(key: str):
    """Retrieve an item from the global cache."""
    val = GLOBAL_CACHE.get(key)
    if val is not None:
        logger.debug(f"Cache HIT for key: {key}")
    else:
        logger.debug(f"Cache MISS for key: {key}")
    return val


def set_cached_item(key: str, value: any):
    """Save an item to the global cache."""
    logger.debug(f"Saving to cache key: {key}")
    GLOBAL_CACHE[key] = value


def invalidate_global_cache():
    """Clear all cached items (called on new dataset uploads)."""
    logger.info("Invalidating all global caches.")
    GLOBAL_CACHE.clear()
