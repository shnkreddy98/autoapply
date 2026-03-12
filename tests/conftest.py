import pytest
import psycopg2

from psycopg2.extras import RealDictCursor

from autoapply.services.db import AutoApply


TEST_CONNINFO = "host=localhost port=25432 dbname=jobs-db user=admin password=password"


@pytest.fixture(scope="session")
def db_conn():
    conn = psycopg2.connect(TEST_CONNINFO)
    conn.autocommit = False
    yield conn
    conn.rollback()
    conn.close()


@pytest.fixture
def repo(db_conn):
    cur = db_conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SAVEPOINT test_sp")
    r = AutoApply(cur, db_conn)
    yield r
    cur.execute("ROLLBACK TO SAVEPOINT test_sp")
    cur.close()
