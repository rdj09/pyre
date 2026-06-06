import operator
from typing import Generic, Iterator, TypeVar, overload

T = TypeVar("T")


class ItemContainer(Generic[T]):
    def __init__(self) -> None:
        self._items: list[T] = []

    def append(self, item: T) -> None:
        self._items.append(item)

    def __iter__(self) -> Iterator[T]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    @overload
    def __getitem__(self, index: int) -> T: ...
    @overload
    def __getitem__(self, index: slice) -> "ItemContainer[T]": ...
    def __getitem__(self, index: "int | slice") -> "T | ItemContainer[T]":
        if isinstance(index, slice):
            cls = type(self)
            return cls(self._items[index])
        return self._items[operator.index(index)]

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._items!r})"
