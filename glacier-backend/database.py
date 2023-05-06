from sqlalchemy import text, select, delete, update
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
import sqlalchemy, configparser, logging, json
from secrets import token_hex

config_path = 'config.ini'
logger = logging.Logger('glacier-database')


def info_msg(message):
    logger.info(message)


def warn_msg(message):
    logger.warning(message)


def error_msg(message):
    logger.error(message)


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
    def __init__(self, config_path):
        config = configparser.ConfigParser()
        config.read(config_path)

        if 'database.credentials' not in config:
            error_msg(f'No database.credentials section in {config_path}')
        credentials = config['database.credentials']
        general_config = config['database.general']

        if 'dbhost' not in credentials:
            error_msg(f'No dbhost variable found in {config_path}')
        if 'dbport' not in credentials:
            error_msg(f'No dbport variable found in {config_path}')
        if 'dbname' not in credentials:
            error_msg(f'No dbname variable found in {config_path}')
        if 'dbuser' not in credentials:
            error_msg(f'No dbuser variable found in {config_path}')
        if 'dbpass' not in credentials:
            error_msg(f'No dbpass variable found in {config_path}')
        if 'upload_facility' not in general_config:
            self.upload_facility = '/tmp'
        else:
            self.upload_facility = general_config['upload_facility']

        self.dbhost = credentials['dbhost']
        self.dbport = credentials['dbport']
        self.dbname = credentials['dbname']
        self.dbuser = credentials['dbuser']
        self.dbpass = credentials['dbpass']
        self.engine = sqlalchemy.create_engine(f'postgresql+psycopg2://{self.dbuser}:{self.dbpass}@{self.dbhost}:{self.dbport}/{self.dbname}', echo=True)
        del self.dbpass
        del credentials
        del config
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

    def add_task(self, id, parent_session_id, blend_file_path, state):
        self.insert_data(Task(id=id,
                              parent_session_id=parent_session_id,
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
    db = UserDatabase(config_path)
