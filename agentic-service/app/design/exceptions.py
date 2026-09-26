from __future__ import annotations

class GenerationFailure(ValueError):
    """No valid candidate exists within this procedural search's supported limits."""

    def __init__(self, message: str, failures: list[dict] | None = None):
        super().__init__(message)
        self.failures = failures or []
