from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from common.storage.base import StorageAdapter
from common.storage.registry import register_adapter

@register_adapter(S3Hook)
class S3StorageAdapter(StorageAdapter):
    """
    Here we can implement funcs that interact with S3 file
    """
    def __init__(self):
        super().__init__()
        