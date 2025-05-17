
from typing import Protocol

class Model(Protocol):
    """
    A protocol that defines the interface for a model.
    """
    def run(self) -> None:
        pass

    def validate(self) -> None:
        pass

    def save(self) -> None:
        pass

    def load(self) -> None:
        pass

class ModelData(Protocol):
    """
    A protocol that defines the interface for a model.
    """
    def run(self) -> None:
        pass

    def validate(self) -> None:
        pass

    def save(self) -> None:
        pass

    def load(self) -> None:
        pass

    def output_for_model():
        pass
    def data_summary():
        pass

