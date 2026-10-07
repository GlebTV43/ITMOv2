"""
Subscription Registry.

Feature A (validated subscribe) and Feature B (validated unsubscribe)
are both implemented.
"""


class Registry:
    """In-memory subscription registry."""

    def __init__(self):
        self._subscribers: set[str] = set()

    @staticmethod
    def _normalise(name: str) -> str:
        """Validate and normalise *name*; raise TypeError or ValueError on rejection.

        Validation order (identical for subscribe and unsubscribe):
        1. name must be a str; otherwise raise TypeError.
        2. Strip surrounding whitespace.
        3. Normalised name must be non-empty; otherwise raise ValueError.
        4. Normalised name must be <= 80 Unicode characters; otherwise raise ValueError.

        Returns the normalised name on success.
        """
        if not isinstance(name, str):
            raise TypeError(f"name must be str, got {type(name).__name__!r}")
        normalised = name.strip()
        if not normalised:
            raise ValueError("name is empty after stripping whitespace")
        if len(normalised) > 80:
            raise ValueError(
                f"name has {len(normalised)} Unicode characters after normalisation; maximum is 80"
            )
        return normalised

    def subscribe(self, name: str) -> bool:
        """Add *name* to the registry (Feature A — validated subscribe).

        Returns True if newly added, False if already present.
        """
        normalised = self._normalise(name)
        if normalised in self._subscribers:
            return False
        self._subscribers.add(normalised)
        return True

    def unsubscribe(self, name: str) -> bool:
        """Remove *name* from the registry (Feature B — validated unsubscribe).

        Applies the same validation contract as subscribe (same order).
        Returns True if the name was present and removed, False if absent.
        Calling with an absent name is safe and idempotent.
        """
        normalised = self._normalise(name)
        if normalised not in self._subscribers:
            return False
        self._subscribers.discard(normalised)
        return True

    def names(self) -> list[str]:
        """Return a sorted snapshot of all current subscribers."""
        return sorted(self._subscribers)
