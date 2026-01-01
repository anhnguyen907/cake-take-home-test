from sqlalchemy import Column, Text, String, DateTime
from sqlalchemy.sql import func

from common.db.metadata_base import MetadataBase


class SFTPSyncedFile(MetadataBase):
    """
        Synchronized file storage model.
        
        With simple version control functionality, 
        it provides sufficient information on files that have been synchronized between two SFTP servers.
    """
    __tablename__ = "sftp_synced_files"
    __table_args__ = {"extend_existing": True}

    file_path = Column(Text, primary_key=True)
    checksum_sha256 = Column(String(64), nullable=False)
    synced_at = Column(DateTime(timezone=True), server_default=func.now())
