import dataclasses
import logging
import socket
import time
import typing
from typing import Optional

import sqlalchemy
from sqlalchemy.orm import Mapped, mapped_column

from config import DatabaseConfig


def wait_for_database_up() -> None:
    config = DatabaseConfig()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    total_seconds_awaited = 0
    timeout = 180
    while True:
        try:
            s.connect((config.db_host, config.db_port))
            s.close()
            break
        except socket.error:
            if total_seconds_awaited > timeout:
                raise Exception(f'Database is not up after {total_seconds_awaited}s')
            time.sleep(0.5)
            total_seconds_awaited += 0.5


logger = logging.getLogger(__name__)


class Base(sqlalchemy.orm.DeclarativeBase):
    def as_dict(self):
        data_dict = {}
        for field in dataclasses.fields(self):
            value = getattr(self, field.name)
            data_dict.update({field.name: value})
        return data_dict


@dataclasses.dataclass
class User(Base):
    __tablename__ = "user_table"

    username: Mapped[Optional[str]] = mapped_column(primary_key=True)
    password_hash: Mapped[Optional[str]]

    def __repr__(self) -> str:
        return f"User(username={self.username!r}, " \
               f"password_hash={self.password_hash!r})"


@dataclasses.dataclass
class Session(Base):
    __tablename__ = "session_table"

    username: Mapped[Optional[str]]
    session_id: Mapped[Optional[str]] = mapped_column(primary_key=True)
    creation_time: Mapped[Optional[str]]

    def __repr__(self) -> str:
        return f"Session(username={self.username!r}, " \
               f"session_id={self.session_id!r}, " \
               f"creation_time={self.creation_time!r})"


@dataclasses.dataclass
class Task(Base):
    __tablename__ = "task_table"

    task_name: Mapped[Optional[str]]
    task_id: Mapped[Optional[str]] = mapped_column(primary_key=True)
    parent_session_id: Mapped[Optional[str]]
    username: Mapped[Optional[str]]
    blend_file_path: Mapped[Optional[str]]
    state: Mapped[Optional[str]]

    def __repr__(self) -> str:
        return f"Task(task_name={self.task_name!r}, " \
               f"task_id={self.task_id!r}, " \
               f"parent_session_id={self.parent_session_id!r}, " \
               f"username={self.username!r}, " \
               f"blend_file_path={self.blend_file_path!r}, " \
               f"state={self.state!r})"


database_types_union = typing.Union[type(User),
                                    type(Session),
                                    type(Task)]


class DatabaseConnector(DatabaseConfig):
    def __init__(self):
        super().__init__()
        self.engine = sqlalchemy.create_engine(f'postgresql+psycopg2://'
                                               f'{self.db_user}:{self.db_pass}'
                                               f'@{self.db_host}:{self.db_port}/'
                                               f'{self.db_name}')


class DatabaseOperator:
    def __init__(self):
        self.engine = DatabaseConnector().engine
        Base.metadata.create_all(self.engine)

    # database_operator_instance.insert_rows([Session(username, id, creation_time)])
    def insert_rows(self, data: list) -> bool:
        with sqlalchemy.orm.Session(self.engine) as database_session:
            database_session.add_all(data)
            database_session.commit()
        return True

    def query_row_by_primary_field(self, object_class: database_types_union, value):
        with sqlalchemy.orm.Session(self.engine) as database_session:
            row = database_session.get(object_class, value)
        return row

    def query_rows(self, object_class: database_types_union, object_class_column_filter):
        with sqlalchemy.orm.Session(self.engine) as database_session:
            rows = database_session.execute(
                sqlalchemy.select(object_class)
                .where(object_class_column_filter)).fetchall()
        if rows:
            rows = rows[0]
        return rows

    # database_operator_instance.update_row(Session, Session.username == 'Spongebob', id='1x1')
    def update_row(self, object_class: database_types_union, object_class_column_filter, **kwvalues) -> bool:
        with sqlalchemy.orm.Session(self.engine) as database_session:
            database_session.execute(
                sqlalchemy.update(object_class)
                .where(object_class_column_filter)
                .values(kwvalues))
            database_session.commit()
        return True

    def delete_row(self, object_class: database_types_union, object_class_column_filter) -> bool:
        with sqlalchemy.orm.Session(self.engine) as database_session:
            database_session.execute(
                sqlalchemy.delete(object_class)
                .where(object_class_column_filter))
            database_session.commit()
        return True


class OperatorAliases(DatabaseOperator):
    def __init__(self):
        super().__init__()

    def add_user(self, **kwvalues) -> bool:
        return self.insert_rows([User(**kwvalues)])

    def get_user_by_username(self, username: str):
        return self.query_row_by_primary_field(User, username)

    def add_session(self, **kwvalues) -> bool:
        return self.insert_rows([Session(**kwvalues)])

    def get_sessions_by_username(self, username: str):
        return self.query_rows(Session, Session.username == username)

    def get_session_by_id(self, session_id: str):
        return self.query_row_by_primary_field(Session, session_id)

    def delete_session_by_id(self, session_id: str) -> bool:
        return self.delete_row(Session, Session.session_id == session_id)

    def add_task(self, **kwvalues) -> bool:
        return self.insert_rows([Task(**kwvalues)])

    def update_task_state(self, task_id: str, new_state: str) -> bool:
        return self.update_row(Task, Task.task_id == task_id, state=new_state)

    def get_task_by_id(self, task_id: str):
        return self.query_row_by_primary_field(Task, task_id)

    def get_tasks_by_session_id(self, session_id: str):
        return self.query_rows(Task, Task.parent_session_id == session_id)

    def delete_task_by_id(self, task_id: str) -> bool:
        return self.delete_row(Task, Task.task_id == task_id)

    def delete_task_by_session_id(self, session_id: str) -> bool:
        return self.delete_row(Task, Task.parent_session_id == session_id)


wait_for_database_up()
