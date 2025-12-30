from airflow import DAG
from airflow.providers.sftp.hooks.sftp import SFTPHook
from airflow.operators.python import PythonOperator
from airflow.models import Variable
from datetime import datetime
import os

SOURCE_BASE_PATH = "/"
TARGET_BASE_PATH = "/"
SYNC_STATE_VAR = "sftp_sync_state"


def list_files_recursive(sftp, path):
    files = []
    for item in sftp.listdir_attr(path):
        full_path = os.path.join(path, item.filename)
        if item.longname.startswith("d"):
            files.extend(list_files_recursive(sftp, full_path))
        else:
            files.append(full_path)
    return files


def ensure_remote_dir(sftp, remote_dir):
    parts = remote_dir.strip("/").split("/")
    current = ""
    for part in parts:
        current += f"/{part}"
        try:
            sftp.stat(current)
        except FileNotFoundError:
            sftp.mkdir(current)


def sync_sftp_files(**context):
    source_hook = SFTPHook(ssh_conn_id="sftp_source")
    target_hook = SFTPHook(ssh_conn_id="sftp_target")

    source_client = source_hook.get_conn()
    target_client = target_hook.get_conn()

    synced_files = set(Variable.get(SYNC_STATE_VAR, default_var=[], deserialize_json=True))

    all_source_files = list_files_recursive(source_client, SOURCE_BASE_PATH)

    new_files = [f for f in all_source_files if f not in synced_files]

    for source_file in new_files:
        relative_path = os.path.relpath(source_file, SOURCE_BASE_PATH)
        target_file = os.path.join(TARGET_BASE_PATH, relative_path)

        target_dir = os.path.dirname(target_file)
        ensure_remote_dir(target_client, target_dir)

        with source_client.open(source_file, "rb") as src_f:
            with target_client.open(target_file, "wb") as tgt_f:
                tgt_f.write(src_f.read())

        synced_files.add(source_file)

    Variable.set(SYNC_STATE_VAR, list(synced_files), serialize_json=True)


with DAG(
    dag_id="sftp_unidirectional_incremental_sync",
    start_date=datetime(2024, 3, 1),
    schedule="@daily",
    catchup=False,
    max_active_runs=1,
    tags=["sftp", "sync"],
) as dag:

    sync_task = PythonOperator(
        task_id="sync_sftp_source_to_target",
        python_callable=sync_sftp_files,
        # provide_context=True,
    )
