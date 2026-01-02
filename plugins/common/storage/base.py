from typing import Iterable, BinaryIO
from abc import ABC, abstractmethod


class StorageAdapter(ABC):

    @abstractmethod
    def list_files(self, path: str) -> Iterable[str]:
        ...

    @abstractmethod
    def open_reader(self, path: str, offset: int = 0) -> BinaryIO:
        ...

    @abstractmethod
    def open_writer(self, path: str, offset: int = 0) -> BinaryIO:
        ...

    @abstractmethod
    def stat_size(self, path: str) -> int:
        ...

    @abstractmethod
    def exists(self, path: str) -> bool:
        ...

    @abstractmethod
    def rename(self, src: str, dst: str) -> None:
        ...

    @abstractmethod
    def ensure_dir(self, path: str) -> None:
        ...
