# cake-take-home-test

## Problem Statement
The task involves two SFTP destinations, referred to as <source> and <target>.

Your objective is to develop an Apache Airflow DAG that facilitates the transfer of files from the SFTP server at <source> to the SFTP server at <target> and ensures the preservation of the original directory structure.

The synchronization process should be unidirectional; hence, any modification made on <target> must not impact the <source>.
Deleted files on SFTP server at <source> must remain intact on <target> server.

Examples:
- On March 1st, 2024, when a file named sftp://<source>/a/b/c/file_1.txt is detected on the source server, it should be replicated to sftp://<target>/a/b/c/file_1.txt on the destination server.
- On March 2nd, 2024, a file named sftp://<source>/a/b/c/file_2.txt appears on the source server and subsequently should be transferred to sftp://<target>/a/b/c/file_2.txt on the destination server.
- On March 3rd, 2024, a file named sftp://<source>/a/b/c/file_3.txt appears on the source server and should then be transferred to sftp://<target>/a/b/c/file_3.txt on the destination server.


## Expected Outcome
- Use separated commits that reflect your incremental development and refactoring. Pure atomic commits are not expected, and don’t squash them.
- A docker-compose.yml file for deploying latest Airflow version, with each service (Scheduler, Worker, Web Server) running in a separate container. Utilizing SQLite as the backend is permissible. The use of Celery executor is advised.
- A README.md file that includes:
    - Detailed instructions for setting up and running the project.
    - Any additional initial setup requirements.
    - An explanation of assumptions made, decisions taken, and any trade-offs considered.
    - One or more DAG file(s).
    - Any additional plugins required for the project.

## Approach:
### Main requirements:
- Based on the problem requirements, we want to create a process to transfer files between SFTP servers.
- Data must be transferred incrementally from source to destination.
- Because "**Deleted files** on the SFTP server at <source> **must remain** on the <destination> server." Therefore, I assume there are no instances of overwriting the file at the source, for example, file_1.txt is deleted, then a content file with the same name file_1.txt is created. File_1.txt at the destination will not be changed.

### Solutions:

![Data flow](images/flow.png)

#### Design Decisions
1. Create Metadata Database. A dedicated metadata database is used instead of Airflow Variables or XComs to:
- Avoid scheduler overload
- Supports large-scale file tracking in the future, when the number of files may be very large.
- Enable cross-DAG reuse in the future

2. Storage Adapter Abstraction
- Hooks are converted into storage adapters at runtime.
- This decouples DAGs and operators from specific storage technologies (SFTP servers, GCS, S3,...)

3. Resume-on-Failure.
- Partial files (.part) are used to support resumable transfers.

4. Optional Transformations
- Transformations are supported but discouraged for complex use cases.

5. Read a file with ChunkSize
- By using chunkSize for data reading, we can ensure that handling large data files up to GB will still be efficient.

#### Trade-offs
| Decision                         | Trade-off                                |
| -------------------------------- | ---------------------------------------- |
| Checksum computed on source only | Cannot validate transformed target bytes |
| Resume requires prefix re-hash   | Slight performance cost                  |
| Transform during file transfer   | Limited observability and validation     |


#### Transformation Policy

Although transformations are technically supported, they are not recommended for production-grade processing.
For complex or computationally expensive transformations, a separate data pipeline should be used:
1. Sync raw files.
2. Transform in a dedicated processing job. E.g: transformations can be processed in Hadoop cluster, Spark cluster, Glue,...
3. Write outputs and control output to destination storage. E.g when i transfer file_1.txt, i will also create a file_20260101100110.json, the folder can be like this /a/b/c/date=2026-01-01/data/file_1.txt, /a/b/c/date=2026-01-01/metadata/file_1.json. The manifest file contains some infomation about the data: No. Rows, List of Columns and its Datatype, CheckSum, number of data files,...

> Synchronization and transformation serve different purposes and should be handled in different layers.

My opinion may be right or wrong depending on the specific circumstances. 😊

#### Extensibility

To add a new storage system (e.g. S3):
1. Implement a new StorageAdapter
2. Register it using @register_adapter(HookClass)
3. Use the corresponding Hook in the DAG


### Runbook:
#### Prerequisites
- Docker
- Make tool

```
git clone https://github.com/anhnguyen907/cake-take-home-test.git && cd cake-take-home-test
```

1. First setup airflow cluster
```
make setup_airflow_cluster
```

2. Add Meta Database to Postgres database
```
make add_meta_database
```

3. Create Airflow Connections
```
make setup_airflow_connections
```
Please wait a moment for the Airflow Dag processing to complete.

4. Simulate the creation of data files at **SFTP source**.
```
mkdir -p data/source/a/b/c && echo "abc" > data/source/a/b/c/file_1.txt
```
We can run below scripts to check list on SFTP **source** server
```
make sftp_check_files SFTP_CONTAINER="sftp_source"
```
The output of source -> 
```
docker exec -it sftp_source ls -Rtl /home/sftpuser/
/home/sftpuser/:
total 0
drwxr-xr-x 3 root root 96 Jan  2 03:46 a

/home/sftpuser/a:
total 0
drwxr-xr-x 3 root root 96 Jan  2 03:46 b

/home/sftpuser/a/b:
total 0
drwxr-xr-x 3 root root 96 Jan  2 03:46 c

/home/sftpuser/a/b/c:
total 4
-rw-r--r-- 1 root root 4 Jan  2 03:46 file_1.txt
```
5. Now we can trigger DAG to verify file transfer.

```
make airflow_trigger_dag
```
> You can go to: http://localhost:8080/dags/sftp_data_file_transfer to check the DAG processing status. User:Password - airflow:airflow

We can run below scripts to check list on SFTP **target** server
```
make sftp_check_files SFTP_CONTAINER="sftp_target"
```
The output of target-> 
```
/home/sftpuser/:
total 0
drwxr-xr-x 3 root root 96 Jan  2 03:52 a

/home/sftpuser/a:
total 0
drwxr-xr-x 3 root root 96 Jan  2 03:52 b

/home/sftpuser/a/b:
total 0
drwxr-xr-x 3 root root 96 Jan  2 03:52 c

/home/sftpuser/a/b/c:
total 4
-rw-r--r-- 1 root root 4 Jan  2 03:52 file_1.txt
```

Now /a/b/c/file_1.txt has been transferred to target. We can add two more files to the SFTP *source* to verify that *2 new files will be transferred to the target* and *modification time of file_1.txt will not be changed.*

```
mkdir -p data/source/a/b/c && echo "abcdef" > data/source/a/b/c/file_2.txt
mkdir -p data/source/a/b/c && cat README.md > data/source/a/b/c/file_3.txt
```
Trigger DAG again.
```
make airflow_trigger_dag
```
Wait a few minutes and you can check the DAG processing status. Once the DAG runs successfully, proceed with verification.

```
make sftp_check_files SFTP_CONTAINER="sftp_target"
```

```
docker exec -it sftp_target ls -Rtl /home/sftpuser/
/home/sftpuser/:
total 0
drwxr-xr-x 3 root root 96 Jan  2 03:52 a

/home/sftpuser/a:
total 0
drwxr-xr-x 3 root root 96 Jan  2 03:52 b

/home/sftpuser/a/b:
total 0
drwxr-xr-x 5 sftpuser users 160 Jan  2 03:59 c

/home/sftpuser/a/b/c:
total 16
-rw-r--r-- 1 root root 6555 Jan  2 03:59 file_3.txt
-rw-r--r-- 1 root root    7 Jan  2 03:59 file_2.txt
-rw-r--r-- 1 root root    4 Jan  2 03:52 file_1.txt
```
As you can see, file_1 has a modified time that doesn't change on the target server.

#### Cleanup resources
```
make clean_up
```