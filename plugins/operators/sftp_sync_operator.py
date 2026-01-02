from airflow.models import BaseOperator
from airflow.providers.sftp.hooks.sftp import SFTPHook
import os
import hashlib
from sqlalchemy.orm.session import Session
from common.models.sftp_synced_file import SFTPSyncedFile
from common.db.metadata_session import get_metadata_session
from common.storage.base import StorageAdapter
from common.transform.base import FileTransform, IdentityTransform
from common.storage.registry import storage_adapter_from_hook

class SFTPSyncOperator(BaseOperator):
    """
    Resumable, transfer files with SFTP.
    IMPORTANT:
        - When a transformation is applied, target bytes differ from source bytes.
        - Therefore, checksum validation applies ONLY to the SOURCE data.
    """
    def __init__(
        self,
        *,
        source_hook: SFTPHook,
        target_hook: SFTPHook,
        source_path: str,
        metadata_conn_id: str = "metadata_postgres",
        chunk_size: int = 8 * 1024 * 1024,  # 8MB
        transform: FileTransform | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.source_hook = source_hook
        self.target_hook = target_hook
        self.source_path = source_path
        self.metadata_conn_id = metadata_conn_id
        self.chunk_size = chunk_size
        self.transform = transform or IdentityTransform()

    def execute(self, context):
        source = storage_adapter_from_hook(hook=self.source_hook, logger=self.log)
        target = storage_adapter_from_hook(hook=self.target_hook, logger=self.log)
        session = get_metadata_session(self.metadata_conn_id)

        for file_path in source.list_files(path=self.source_path):
            if self._already_synced(session=session, path=file_path):
                self.log.info("Path %s already sync to target, Skip file.", file_path)
                continue

            self._sync_one_file(
                source=source,
                target=target,
                session=session,
                path=file_path,
            )
        
    def _sync_one_file(
        self, 
        source: StorageAdapter, 
        target: StorageAdapter, 
        session: Session, 
        path: str
    ):
        temp_path = f"{path}.part"
        
        target.ensure_dir(path=os.path.dirname(path))
        
        src_size = source.stat_size(path=path)
        offset = target.stat_size(path=temp_path) if target.exists(path=temp_path) else 0
        if offset:
            self.log.info("Resuming transfer file %s from offset %s.", path, offset)
        
        with source.open_reader(path=path, offset=offset) as src:
            with target.open_writer(path=temp_path, offset=offset) as trg:
                transferred = offset
                while transferred < src_size:
                    chunk = src.read(self.chunk_size)
                    if not chunk:
                        break
                    trg.write(self.transform.apply(chunk))
                    transferred += len(chunk)
        
        src_hash = self._checksum(storage=source, path=path)        
    
        target.rename(temp_path, path)
        session.merge(
            SFTPSyncedFile(
                file_path=path,
                checksum_sha256=src_hash
            )
        )
        session.commit()
        
        self.log.info("Synced %s successfully", path)
    
    def _already_synced(
        self,
        session: Session,
        path: str
    ):
        return (
            session.query(SFTPSyncedFile)
            .filter_by(file_path=path)
            .one_or_none()
        )
    
    def _checksum(self, storage: StorageAdapter, path: str) -> str:
        sha = hashlib.sha256()
        with storage.open_reader(path) as f:
            while True:
                data = f.read(self.chunk_size)
                if not data:
                    break
                sha.update(data)
        return sha.hexdigest()
        