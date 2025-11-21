from abc import ABC
from typing import Callable, List, Optional, Union

__all__ = ["Action"]


class Action(ABC):
    def __init__(
        self,
        name: str,
        fn: Callable,
        callback: Optional[Callable] = None,
        dependency: Union[List, str, None] = None,
        reduce: Optional[List] = None,
        reduce_fn: Optional[Callable] = None,
        expand: Optional[List] = None,
        expand_fn: Optional[Callable] = None,
        chunk_size: int = 1,
        check_complete: Optional[Callable] = None,
    ):
        self.name = name
        self.fn = fn
        self.callback = callback
        self.dependency = dependency if dependency is not None else []
        if not isinstance(self.dependency, list):
            self.dependency = [self.dependency]
        self.reduce = reduce if reduce is not None else []
        self.reduce_fn = reduce_fn
        self.expand = expand if expand is not None else []
        self.expand_fn = expand_fn
        self.chunk_size = chunk_size
        self.check_complete = check_complete

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.name
