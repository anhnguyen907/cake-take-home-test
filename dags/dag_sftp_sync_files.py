from airflow import DAG
from airflow.providers.sftp.hooks.sftp import SFTPHook
from datetime import datetime
from operators.sftp_sync_operator import SFTPSyncOperator

with DAG(
    dag_id="sftp_data_file_sync",
    start_date=datetime(2024, 3, 1),
    schedule="@daily",
    catchup=False
) as dag:

    source_hook = SFTPHook(ssh_conn_id="sftp_source")
    target_hook = SFTPHook(ssh_conn_id="sftp_target")

    SFTPSyncOperator(
        task_id="sync_sftp",
        source_hook=source_hook,
        source_path="/",
        target_hook=target_hook,
    )
