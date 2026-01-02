SHELL := /bin/bash

SCHEDULER_CONTAINER := $(shell docker ps --filter "name=scheduler" --format "{{.Names}}")
POSTGRES_CONTAINER := $(shell docker ps --filter "expose=5432" --format "{{.Names}}")

setup_airflow_cluster:
	mkdir -p ./dags ./logs ./plugins ./config
	echo -e "AIRFLOW_UID=$(id -u)" > .env
	docker compose run airflow-cli airflow config list
	chmod -R 777 ./config
	docker compose up airflow-init
	docker compose up -d

add_meta_database:
	docker exec -it $(POSTGRES_CONTAINER) psql -U airflow -d airflow -f /home/scripts/create_database__metadata.sql
	docker exec -it $(POSTGRES_CONTAINER) psql -U airflow -d metadata -f /home/scripts/create_table__sftp_synced_files.sql

setup_airflow_connections:
	docker exec -it $(SCHEDULER_CONTAINER) airflow connections add  --conn-type sftp --conn-host sftp_source --conn-login sftpuser --conn-password password --conn-port 22 sftp_source
	docker exec -it $(SCHEDULER_CONTAINER) airflow connections add  --conn-type sftp --conn-host sftp_target --conn-login sftpuser --conn-password password --conn-port 22 sftp_target
	docker exec -it $(SCHEDULER_CONTAINER) airflow connections add  --conn-type postgres --conn-host postgres --conn-login airflow --conn-password airflow --conn-port 5432 --conn-schema metadata metadata_postgres
    
clean_up:
	docker compose down --volumes --rmi all	

airflow_trigger_dag:
	docker exec -it $(SCHEDULER_CONTAINER) airflow dags trigger sftp_data_file_transfer

sftp_check_files:
	docker exec -it $(SFTP_CONTAINER) ls -Rtl /home/sftpuser/