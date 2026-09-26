import os
import pytest
from unittest.mock import patch
import app.config

def test_dotnet_to_psycopg2():
    # Arrange
    dotnet_str = "Host=localhost;Port=5432;Database=aihouse;Username=postgres;Password=secret;SSL Mode=Require"
    # Act
    psycopg2_dsn = app.config._dotnet_to_psycopg2(dotnet_str)
    # Assert
    assert "host=localhost" in psycopg2_dsn
    assert "port=5432" in psycopg2_dsn
    assert "dbname=aihouse" in psycopg2_dsn
    assert "user=postgres" in psycopg2_dsn
    assert "password=secret" in psycopg2_dsn
    assert "sslmode=require" in psycopg2_dsn

def test_get_db_connection_string_found():
    # Arrange
    with patch.dict(os.environ, {"DATABASE_CONNECTION_STRING": "Host=testhost;Database=testdb"}, clear=True):
        # Act
        dsn = app.config.get_db_connection_string()
        # Assert
        assert "host=testhost" in dsn
        assert "dbname=testdb" in dsn

def test_get_db_connection_string_missing():
    # Arrange
    with patch.dict(os.environ, {}, clear=True):
        if "DATABASE_CONNECTION_STRING" in os.environ:
            del os.environ["DATABASE_CONNECTION_STRING"]
        # Act & Assert
        with pytest.raises(RuntimeError, match="DATABASE_CONNECTION_STRING not found"):
            app.config.get_db_connection_string()
