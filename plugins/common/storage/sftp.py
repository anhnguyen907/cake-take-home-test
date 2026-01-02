from airflow.providers.sftp.hooks.sftp import SFTPHook
from common.storage.base import StorageAdapter
import os
import logging
from common.storage.registry import register_adapter

log = logging.getLogger(__name__)

@register_adapter(SFTPHook)
class SFTPStorageAdapter(StorageAdapter):

    def __init__(self, hook: SFTPHook, logger=None):
        self._client = hook.get_conn()
        self.hook = hook
        self.log = logger

    def list_files(self, path: str):
        self.log.info("Lookup file from path %s", path)
        files = []
        for e in self._client.listdir_attr(path):
            full = os.path.join(path, e.filename)
            if e.longname.startswith("d"):
                files.extend(self.list_files(path=full))
            else:
                files.append(full)
        return files

    def stat_size(self, path):
        return self._client.stat(path).st_size

    def exists(self, path):
        try:
            self._client.stat(path)
            return True
        except FileNotFoundError:
            return False

    def open_reader(self, path: str, offset=0):
        f = self._client.open(path, "rb")
        if offset:
            f.seek(offset)
        return f

    def open_writer(self, path: str, offset=0):
        mode = "ab" if offset else "wb"
        return self._client.open(path, mode)

    def rename(self, src: str, dst: str):
        self._client.rename(src, dst)

    def ensure_dir(self, path: str):
        if not path:
            return
        cur = ""
        for part in path.strip("/").split("/"):
            cur += f"/{part}"
            try:
                self._client.stat(cur)
            except FileNotFoundError:
                self._client.mkdir(cur)
