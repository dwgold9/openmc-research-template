from typing import Any, Dict, Optional, Type


# ============================================================
# Registry
# ============================================================

class Registry:
    """
    Hierarchical namespace registry.

    Namespaces:
        - models
        - tallies
        - metrics
        - artifacts

    Supports parent fallback.
    """

    _VALID_NAMESPACES = {"models", "tallies", "metrics", "artifacts"}

    def __init__(self, parent: Optional["Registry"] = None):
        self.parent = parent
        self._store: Dict[str, Dict[str, Any]] = {
            ns: {} for ns in self._VALID_NAMESPACES
        }

    # --------------------------------------------------------
    # Registration
    # --------------------------------------------------------

    def register(self, namespace: str, name: str, obj: Any):
        if namespace not in self._VALID_NAMESPACES:
            raise ValueError(f"Invalid namespace '{namespace}'")

        if name in self._store[namespace]:
            raise ValueError(
                f"Duplicate registration: {namespace}:{name}"
            )

        # Optional: detect shadowing of parent
        if self.parent and self.parent.contains(namespace, name):
            print(
                f"[Registry Warning] '{namespace}:{name}' "
                f"overrides parent definition."
            )

        self._store[namespace][name] = obj

    # --------------------------------------------------------
    # Resolution
    # --------------------------------------------------------

    def get(self, namespace: str, name: str):
        if namespace not in self._VALID_NAMESPACES:
            raise ValueError(f"Invalid namespace '{namespace}'")

        if name in self._store[namespace]:
            return self._store[namespace][name]

        if self.parent:
            return self.parent.get(namespace, name)

        raise KeyError(f"{namespace}:{name} not found")

    def contains(self, namespace: str, name: str) -> bool:
        if name in self._store[namespace]:
            return True
        if self.parent:
            return self.parent.contains(namespace, name)
        return False

    # --------------------------------------------------------
    # Introspection
    # --------------------------------------------------------

    def list(self, namespace: str):
        items = set(self._store[namespace].keys())
        if self.parent:
            items |= set(self.parent.list(namespace))
        return sorted(items)

    def namespaces(self):
        return list(self._VALID_NAMESPACES)


# ============================================================
# Decorator Metadata Attachment
# ============================================================

def _attach_registry_metadata(cls: Type, namespace: str, name: str):
    cls._registry_namespace = namespace
    cls._registry_name = name
    return cls


# ------------------------------------------------------------
# Typed Decorators (with Base Enforcement)
# ------------------------------------------------------------

def model(name: str):
    from core.models.base import ModelBase

    def decorator(cls: Type):
        if not issubclass(cls, ModelBase):
            raise TypeError(
                f"{cls.__name__} must inherit from ModelBase"
            )
        return _attach_registry_metadata(cls, "models", name)

    return decorator


def tally(name: str):
    from core.tallies.base import TallyBase

    def decorator(cls: Type):
        if not issubclass(cls, TallyBase):
            raise TypeError(
                f"{cls.__name__} must inherit from TallyBase"
            )
        return _attach_registry_metadata(cls, "tallies", name)

    return decorator


def metric(name: str):
    from core.metrics.base import MetricBase

    def decorator(cls: Type):
        if not issubclass(cls, MetricBase):
            raise TypeError(
                f"{cls.__name__} must inherit from MetricBase"
            )
        return _attach_registry_metadata(cls, "metrics", name)

    return decorator


def artifact(name: str):
    from core.artifacts.base import ArtifactBase

    def decorator(cls: Type):
        if not issubclass(cls, ArtifactBase):
            raise TypeError(
                f"{cls.__name__} must inherit from ArtifactBase"
            )
        return _attach_registry_metadata(cls, "artifacts", name)

    return decorator