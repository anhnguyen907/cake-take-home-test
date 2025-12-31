CREATE TABLE if not exists public.sftp_synced_files (
    file_path TEXT PRIMARY KEY,
    checksum_sha256 CHAR(64) NOT NULL,
    synced_at TIMESTAMPTZ DEFAULT now()
);
