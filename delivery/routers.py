from django.core.cache import cache
from django.conf import settings

class CacheRouter:
    """
    Custom database router with intelligent caching
    """
    def __init__(self):
        self.cache_timeout = getattr(settings, 'CACHE_MIDDLEWARE_SECONDS', 600)

    def _get_cache_key(self, model, pk):
        """
        Generate a unique cache key for a model instance
        """
        return f"{model._meta.app_label}_{model._meta.model_name}_{pk}"

    def cache_get(self, model, pk):
        """
        Retrieve an object from cache
        """
        cache_key = self._get_cache_key(model, pk)
        return cache.get(cache_key)

    def cache_set(self, model, pk, obj):
        """
        Set an object in cache
        """
        cache_key = self._get_cache_key(model, pk)
        cache.set(cache_key, obj, self.cache_timeout)

    def cache_delete(self, model, pk):
        """
        Delete an object from cache
        """
        cache_key = self._get_cache_key(model, pk)
        cache.delete(cache_key)

    def db_for_read(self, model, **hints):
        """
        Attempt to read from cache first
        """
        if hasattr(model, 'id'):
            cached_obj = self.cache_get(model, model.id)
            if cached_obj:
                return None  # Use cache
        return 'default'

    def db_for_write(self, model, **hints):
        """
        Write to database and update cache
        """
        if hasattr(model, 'id'):
            self.cache_set(model, model.id, model)
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations between objects
        """
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Ensure all models can migrate
        """
        return True
