SHELL := /bin/bash

SCHEDULER_CONTAINER := $(shell docker ps --filter "name=scheduler" --format "{{.Names}}")

setup_connections:
	docker exec -it $(SCHEDULER_CONTAINER) airflow connections add  --conn-type sftp --conn-host sftp_source --conn-login sftpuser --conn-password password --conn-port 22 sftp_source
	docker exec -it $(SCHEDULER_CONTAINER) airflow connections add  --conn-type sftp --conn-host sftp_target --conn-login sftpuser --conn-password password --conn-port 22 sftp_target
	docker exec -it $(SCHEDULER_CONTAINER) airflow connections add  --conn-type postgres --conn-host postgres --conn-login airflow --conn-password airflow --conn-port 5432 --conn-schema metadata metadata_postgres
    