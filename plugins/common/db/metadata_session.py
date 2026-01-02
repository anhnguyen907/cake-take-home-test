from airflow.providers.postgres.hooks.postgres import PostgresHook
from sqlalchemy.orm import sessionmaker


def get_metadata_session(conn_id: str):
    """
    Create a session with conn_id.
    The expected connection type is a Database. Current database type is Postgres.
    """
    hook = PostgresHook(postgres_conn_id=conn_id)
    engine = hook.get_sqlalchemy_engine()
    Session = sessionmaker(bind=engine)
    return Session()
