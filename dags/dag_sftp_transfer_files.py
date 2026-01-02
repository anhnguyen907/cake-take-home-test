from airflow import DAG
from airflow.providers.sftp.hooks.sftp import SFTPHook
from datetime import datetime
from operators.sftp_sync_operator import SFTPSyncOperator
from common.transform.basic_transform import AddDotTransform

with DAG(
    dag_id="sftp_data_file_transfer",
    start_date=datetime(2026, 1, 1),
    schedule="@daily",
    catchup=False
) as dag:
    sync_task = SFTPSyncOperator(
        task_id="transfer_files",
        source_hook=SFTPHook(ssh_conn_id="sftp_source"),
        target_hook=SFTPHook(ssh_conn_id="sftp_target"),
        source_path="/",
        # transform=AddDotTransform()
    )
