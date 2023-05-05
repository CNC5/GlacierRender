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
    task_ids: Mapped[Optional[str]]

    def __repr__(self) -> str:
        return f"Session(username={self.username!r}, " \
               f"id={self.id!r}, " \
               f"creation_time={self.creation_time!r}, " \
               f"task_ids={self.task_ids!r})"


class Task(Base):
    __tablename__ = "task_table"

    id: Mapped[Optional[str]] = mapped_column(primary_key=True)
    parent_session_id: Mapped[Optional[str]]
    blend_file_path: Mapped[Optional[str]]
    state: Mapped[Optional[str]]
    progress: Mapped[Optional[str]]

    def __repr__(self) -> str:
        return f"Task(id={self.id!r}, " \
               f"parent_session_id={self.parent_session_id!r}, " \
               f"blend_file_path={self.blend_file_path!r}, " \
               f"state={self.state!r}, " \
               f"progress={self.progress!r})"


class UserDatabase:
    def __init__(self, config_path):
        config = configparser.ConfigParser()
        config.read(config_path)

        if 'database.credentials' not in config:
            error_msg(f'No database.credentials section in {config_path}')
        credentials = config['database.credentials']

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
            sqlalchemy.Column('username', sqlalchemy.String(30), primary_key=True),
            sqlalchemy.Column('password_hash', sqlalchemy.String),
            sqlalchemy.Column('salt', sqlalchemy.String),
        )
        self.session_table = sqlalchemy.Table(
            'session_table',
            metadata_root_object,
            sqlalchemy.Column('username', sqlalchemy.String(30)),
            sqlalchemy.Column('id', sqlalchemy.String, primary_key=True),
            sqlalchemy.Column('creation_time', sqlalchemy.String),
            sqlalchemy.Column('task_ids', sqlalchemy.String),
        )
        self.task_table = sqlalchemy.Table(
            'task_table',
            metadata_root_object,
            sqlalchemy.Column('id', sqlalchemy.String(30), primary_key=True),
            sqlalchemy.Column('parent_session_id', sqlalchemy.String),
            sqlalchemy.Column('blend_file_path', sqlalchemy.String),
            sqlalchemy.Column('state', sqlalchemy.String),
            sqlalchemy.Column('progress', sqlalchemy.String),
        )
        metadata_root_object.create_all(self.engine)

    def insert_data(self, *data):
        for data_object in data:
            self.session.add(data_object)
        self.session.commit()

    def add_user(self, username, password_hash, salt):
        try:
            self.insert_data(User(username=username, password_hash=password_hash, salt=salt))
        except:
            error_msg('useradd failed (likely due to a duplicate username)')
            self.session.rollback()

    def get_user_by_username(self, username):
        return self.session.execute(select(self.user_table).where(self.user_table.c.username == username)).fetchall()

    def is_user(self, username):
        return bool(self.session.execute(select(self.user_table).where(self.user_table.c.username == username)).fetchall())

#    def all_user_data(self):
#        return self.session.execute(select(self.user_table)).fetchall()

#    def list_users(self):
#        data = self.session.execute(select(self.user_table)).fetchall()
#        if not data:
#            return []
#        return [user[0] for user in data]

    def add_session(self, username, id, creation_time, task_ids):
        self.insert_data(Session(username=username, id=str(id), creation_time=str(creation_time), task_ids=json.dumps(task_ids)))

    def get_session_by_username(self, username):
        return self.session.execute(select(self.session_table).where(self.session_table.c.username == username)).fetchall()

    def get_session_by_id(self, id):
        return self.session.execute(select(self.session_table).where(self.session_table.c.id == id)).fetchall()

    def is_session(self, id):
        return bool(self.get_session_by_id(id))

    def delete_session_by_id(self, id):
        return self.session.execute(delete(self.session_table).where(self.session_table.c.id == id))

    def list_sessions(self):
        data = self.session.execute(select(self.session_table)).fetchall()
        if not data:
            return []
        return [session[0] for session in data]

#    def all_session_data(self):
#        return self.session.execute(select(self.user_table)).fetchall()

    def get_session_tasks_by_id(self, id):
        return json.loads(self.session.execute(select(self.session_table).where(self.session_table.c.id == str(id))).fetchall()[0][3])

    def update_session_tasks_by_id(self, id, new_tasks_list):
        task_ids = json.dumps(new_tasks_list)
        self.session.execute(update(self.session_table).where(self.session_table.c.id == str(id)).values(task_ids=task_ids))

    def add_task(self, id, parent_session_id, blend_file_path, state, progress):
        try:
            self.insert_data(Task(id=id, parent_session_id=parent_session_id, blend_file_path=blend_file_path, state=state, progress=progress))
        except:
            error_msg('taskadd failed (likely due to a duplicate id)')
            self.session.rollback()

    def get_task_by_id(self, id):
        return self.session.execute(select(self.task_table).where(self.task_table.c.id == id)).fetchall()

    def is_task(self, id):
        return bool(self.get_task_by_id(id))

    def delete_task_by_id(self, id):
        return self.session.execute(delete(self.task_table).where(self.task_table.c.id == id))

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
