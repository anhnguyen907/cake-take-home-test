from airflow.models import BaseOperator
from airflow.providers.sftp.hooks.sftp import SFTPHook
from airflow.utils.session import provide_session
from paramiko.sftp_client import SFTPClient
import os
import hashlib
from sqlalchemy.orm.session import Session
from common.models.sftp_synced_file import SFTPSyncedFile
from common.db.metadata_session import get_metadata_session


class SFTPSyncOperator(BaseOperator):
    """
    Sync a file between 2 SFTP Servers, resumable, checksum-validated SFTP sync.
    """

    template_fields = ("source_path",)

    # @apply_defaults
    def __init__(
        self,
        *,
        source_hook: SFTPHook,
        source_path: str,
        target_hook: SFTPHook,
        metadata_conn_id: str = "metadata_postgres",
        chunk_size: int = 8 * 1024 * 1024,  # 8MB
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.source_hook = source_hook
        self.source_path = source_path
        self.target_hook = target_hook
        self.metadata_conn_id = metadata_conn_id
        self.chunk_size = chunk_size

    def execute(self, context):        
        source_client = self.source_hook.get_conn()
        target_client = self.target_hook.get_conn()
        session = get_metadata_session(conn_id=self.metadata_conn_id)

        files = self._list_recursive(source_client, self.source_path)

        for source_file in files:
            self.log.info("Currently working on file %s", source_file)
            self._sync_file(session, source_client, target_client, source_file)

    @provide_session
    def _sync_file(
        self,
        session: Session,
        source_client: SFTPClient,
        target_client: SFTPClient,
        source_file: str,
    ):
        """
        This func implement the syncronize a file between SFTP servers with ChunkSize.
        1. Check the target path exists the temporary/part files. If exist, continue to process at offset of the part file.
        2. Read the source file with Chunk-Size to make sure the func can process the large file.
        3. Compute and Compare CheckSum between Source and path file
        4. Commit the synced file to Meta Database        
        """
        target_file = source_file
        temp_file = f"{target_file}.part"

        record = (
            session.query(SFTPSyncedFile).filter_by(file_path=source_file).one_or_none()
        )
        if record:
            self.log.info("Skip already synced file: %s", source_file)
            return

        self._ensure_remote_dir(target_client, os.path.dirname(target_file))

        src_size = source_client.stat(source_file).st_size

        offset = 0
        try:
            # Try to check offset of target we will continue sync data.
            offset = target_client.stat(temp_file).st_size
            self.log.info("Resuming %s from offset %s", source_file, offset)
        except FileNotFoundError:
            pass


        with source_client.open(source_file, "r") as src:
            src.seek(offset)

            mode = "a" if offset > 0 else "w"
            with target_client.open(temp_file, mode) as tgt:
                transferred = offset

                while transferred < src_size:
                    self.log.info("Currently process at offset: %s", transferred)
                    chunk = src.read(self.chunk_size)
                    if not chunk:
                        break
                    tgt.write(chunk)
                    transferred += len(chunk)

        # Compute checksum between Source and Target 
        # Before rename temp file at target.
        target_hash = self._compute_checksum(target_client, temp_file)
        source_hash = self._compute_checksum(source_client, source_file)
        if source_hash != target_hash:
            self.log.error("Check sum mis-match with source: %s and target: %s", source_hash, target_hash)
            raise ValueError(f"Checksum mismatch for {source_file}")

        target_client.rename(temp_file, target_file)

        # After successfully copy files, commit to Meta database
        session.merge(
            SFTPSyncedFile(file_path=source_file, checksum_sha256=target_hash)
        )
        session.commit()

        self.log.info("Synced %s successfully", source_file)

    def _compute_checksum(self, sftp: SFTPClient, path: str) -> str:
        """
        Compute the data file to get Checksum.
        With args:

            - SFTPClient
            - Target Path

        """
        sha = hashlib.sha256()
        with sftp.open(path, "r") as f:
            while True:
                data = f.read(self.chunk_size)
                if not data:
                    break
                sha.update(data)
        return sha.hexdigest()

    def _list_recursive(self, sftp: SFTPClient, path: str):
        """
        Recursive look up files in the path.
        Call func when a path is directory. 
        """
        self.log.info("Lookup file from path %s", path)
        files = []
        for entry in sftp.listdir_attr(path):
            full_path = os.path.join(path, entry.filename)
            if entry.longname.startswith("d"):
                files.extend(self._list_recursive(sftp, full_path))
            else:
                files.append(full_path)
        return files

    def _ensure_remote_dir(self, sftp: SFTPClient, remote_dir: str):
        """
        Make sure the destination path exists; 
        Otherwise, the func will create folders corresponding to the source.
        """
        if not remote_dir or remote_dir == "/":
            return
        parts = remote_dir.strip("/").split("/")
        current = ""
        for part in parts:
            current += f"/{part}"
            try:
                sftp.stat(current)
            except FileNotFoundError:
                sftp.mkdir(current)
