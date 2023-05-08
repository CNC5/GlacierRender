import json
import logging
import os
import socket
import time
from typing import Optional

import sqlalchemy
from sqlalchemy import select, delete, update
from sqlalchemy.orm import Mapped, mapped_column


def wait_for_database_up():
    db_host = os.environ['DB_HOST']
    db_port = int(os.environ['DB_PORT'])
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    while True:
        try:
            s.connect((db_host, db_port))
            s.close()
            break
        except socket.error as ex:
            time.sleep(0.5)


wait_for_database_up()
logger = logging.getLogger(__name__)


class Base(sqlalchemy.orm.DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "user_table"

    username: Mapped[Optional[str]] = mapped_column(primary_key=True)
    password_hash: Mapped[Optional[str]]
    salt: Mapped[Optional[str]]

    def __repr__(self) -> str:
        return f"User(username={self.username!r}, " \
               f"password_hash={self.password_hash!r}, " \
               f"salt={self.salt!r})"


class Session(Base):
    __tablename__ = "session_table"

    username: Mapped[Optional[str]]
    id: Mapped[Optional[str]] = mapped_column(primary_key=True)
    creation_time: Mapped[Optional[str]]

    def __repr__(self) -> str:
        return f"Session(username={self.username!r}, " \
               f"id={self.id!r}, " \
               f"creation_time={self.creation_time!r}, " \



class Task(Base):
    __tablename__ = "task_table"

    id: Mapped[Optional[str]] = mapped_column(primary_key=True)
    parent_session_id: Mapped[Optional[str]]
    username: Mapped[Optional[str]]
    blend_file_path: Mapped[Optional[str]]
    state: Mapped[Optional[str]]

    def __repr__(self) -> str:
        return f"Task(id={self.id!r}, " \
               f"parent_session_id={self.parent_session_id!r}, " \
               f"username={self.username!r}" \
               f"blend_file_path={self.blend_file_path!r}" \
               f"state={self.state!r})"


class UserDatabase:
    def __init__(self):
        environment = os.environ
        if 'DB_HOST' not in environment:
            logger.error(f'No dbhost variable found')
        if 'DB_PORT' not in environment:
            logger.error(f'No dbport variable found')
        if 'DB_NAME' not in environment:
            logger.error(f'No dbname variable found')
        if 'DB_USER' not in environment:
            logger.error(f'No dbuser variable found')
        if 'DB_PASS' not in environment:
            logger.error(f'No dbpass variable found')
        if 'UPLOAD_FACILITY' not in environment:
            self.upload_facility = '/tmp'
        else:
            self.upload_facility = environment['UPLOAD_FACILITY']

        self.dbhost = environment['DB_HOST']
        self.dbport = environment['DB_PORT']
        self.dbname = environment['DB_NAME']
        self.dbuser = environment['DB_USER']
        self.dbpass = environment['DB_PASS']
        self.engine = sqlalchemy.create_engine(f'postgresql+psycopg2://'
                                               f'{self.dbuser}:{self.dbpass}@{self.dbhost}:{self.dbport}/'
                                               f'{self.dbname}')
        self.session = sqlalchemy.orm.Session(self.engine)

        metadata_root_object = sqlalchemy.MetaData()
        self.user_table = sqlalchemy.Table(
            'user_table',
            metadata_root_object,
            sqlalchemy.Column('username', sqlalchemy.String, primary_key=True),
            sqlalchemy.Column('password_hash', sqlalchemy.String),
            sqlalchemy.Column('salt', sqlalchemy.String),
        )
        self.session_table = sqlalchemy.Table(
            'session_table',
            metadata_root_object,
            sqlalchemy.Column('username', sqlalchemy.String),
            sqlalchemy.Column('id', sqlalchemy.String, primary_key=True),
            sqlalchemy.Column('creation_time', sqlalchemy.String),
        )
        self.task_table = sqlalchemy.Table(
            'task_table',
            metadata_root_object,
            sqlalchemy.Column('id', sqlalchemy.String, primary_key=True),
            sqlalchemy.Column('parent_session_id', sqlalchemy.String),
            sqlalchemy.Column('username', sqlalchemy.String),
            sqlalchemy.Column('blend_file_path', sqlalchemy.String),
            sqlalchemy.Column('state', sqlalchemy.String)
        )
        metadata_root_object.create_all(self.engine)

    def insert_data(self, *data):
        for data_object in data:
            self.session.add(data_object)
        self.session.commit()

    def add_user(self, username, password_hash, salt):
        self.insert_data(User(username=username,
                              password_hash=password_hash,
                              salt=salt))

    def get_user_by_username(self, username):
        return self.session.execute(select(self.user_table).where(self.user_table.c.username == username)).fetchall()

    def add_session(self, username, id, creation_time):
        self.insert_data(Session(username=username,
                                 id=str(id),
                                 creation_time=str(creation_time)))

    def get_session_by_username(self, username):
        return self.session.execute(select(self.session_table).where(self.session_table.c.username == username)).fetchall()

    def get_session_by_id(self, id):
        return self.session.execute(select(self.session_table).where(self.session_table.c.id == id)).fetchall()

    def is_session(self, id):
        return bool(self.get_session_by_id(id))

    def delete_session_by_id(self, id):
        self.session.execute(delete(self.session_table).where(self.session_table.c.id == id))
        self.session.commit()

    def list_sessions(self):
        data = self.session.execute(select(self.session_table)).fetchall()
        if not data:
            return []
        return [session[0] for session in data]

    def get_session_tasks_by_id(self, id):
        data = self.session.execute(select(self.session_table).where(self.session_table.c.id == str(id))).fetchall()
        if data:
            data = json.loads(data[0].task_ids)
        else:
            data = []
        return data

    def add_task(self, id, parent_session_id, username, blend_file_path, state):
        self.insert_data(Task(id=id,
                              parent_session_id=parent_session_id,
                              username=username,
                              blend_file_path=blend_file_path,
                              state=state))

    def update_task_state(self, task_id, new_state):
        self.session.execute(update(self.task_table).where(self.task_table.c.id == task_id).values(state=new_state))

    def get_task_by_id(self, id):
        return self.session.execute(select(self.task_table).where(self.task_table.c.id == id)).fetchall()

    def is_task(self, id):
        return bool(self.get_task_by_id(id))

    def delete_task_by_id(self, id):
        self.session.execute(delete(self.task_table).where(self.task_table.c.id == id))
        self.session.commit()

    def delete_task_by_session_id(self, id):
        self.session.execute(delete(self.task_table).where(self.task_table.c.parent_session_id == id))
        self.session.commit()

    def get_task_by_session_id(self, parent_session_id):
        return self.session.execute(select(self.task_table).where(self.task_table.c.parent_session_id == parent_session_id)).fetchall()

    def list_tasks(self):
        data = self.session.execute(select(self.task_table)).fetchall()
        if not data:
            return []
        return [task[0] for task in data]

    def __del__(self):
        self.session.close()


class DatabaseManager:
    def __init__(self):
        print('not implemented')


if __name__ == '__main__':
    db = UserDatabase()
