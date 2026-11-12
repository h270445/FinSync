"""Alembic environment: migrations run on the connection FinSyncStorage hands over, never from a config file."""

from alembic import context

connection = context.config.attributes["connection"]
context.configure(connection=connection, render_as_batch=connection.dialect.name == "sqlite")
with context.begin_transaction():
    context.run_migrations()
