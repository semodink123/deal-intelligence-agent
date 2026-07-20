"""Base connector class for extensibility."""
from abc import ABC, abstractmethod
from typing import List
from src.models import Deal


class BaseConnector(ABC):
    """Abstract base class for all deal connectors."""
    
    def __init__(self, name: str, config: dict = None):
        self.name = name
        self.config = config or {}
    
    @abstractmethod
    def fetch_deals(self) -> List[Deal]:
        """Fetch deals from the connector source.
        
        Returns:
            List of Deal objects.
        """
        pass
    
    def validate(self) -> bool:
        """Validate connector configuration.
        
        Returns:
            True if configuration is valid.
        """
        return True
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.name}>"
