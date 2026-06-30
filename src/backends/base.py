from abc import ABC, abstractmethod

class Backend(ABC):
    """One contract every model backend must satisfy.
    The gateway depends on THIS, never on a specific model."""

    name: str  # e.g. "mock", "llama-8b"

    @abstractmethod
    async def predict(self, prompt: str) -> str:
        """Run the model on a prompt and return its text output."""
        ...