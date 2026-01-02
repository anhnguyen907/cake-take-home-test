from typing import Dict, Type
from common.storage.base import StorageAdapter

_STORAGE_ADAPTERS: Dict[type, Type[StorageAdapter]] = {}

def register_adapter(hook_cls):
    """
    Decorator for register a StorageAdapter
    """
    def wrapper(adapter_cls: Type[StorageAdapter]):
        _STORAGE_ADAPTERS[hook_cls] = adapter_cls
        return adapter_cls
    return wrapper

def storage_adapter_from_hook(hook, logger=None) -> StorageAdapter:
    for hook_cls, adapter_cls in _STORAGE_ADAPTERS.items():
        if isinstance(hook, hook_cls):
            return adapter_cls(hook, logger)
    raise TypeError(
        f"No StorageAdapter for hook type: {type(hook_cls).__name__}"
    )
