from database import UserDatabase
import hashlib, logging, time, json
from secrets import token_hex

logger = logging.Logger('glacier-auth')
logger.setLevel(logging.WARNING)


class Authman:
    def __init__(self):
        self.db = UserDatabase('config.ini')

    def hash(self, plaintext, salt):
        hashed_text = hashlib.sha3_256()
        hashed_text.update(f'{plaintext}{salt}'.encode())
        return hashed_text.hexdigest()

    def is_user(self, username):
        return self.db.is_user(username)

    def is_password_correct(self, username, password):
        if not self.is_user(username):
            return False
        user = self.db.get_user_by_username(username)[0]
        hashed_password = self.hash(password, user[2])
        if hashed_password == user[1]:
            return True
        return False

    def add_user(self, username, password):
        if self.is_user(username):
            return False
        salt = token_hex(10)
        password_hash = self.hash(password, salt)
        self.db.add_user(username, password_hash, salt)
        self.sync()
        return True

    def add_session(self, username):
        session_id = token_hex(16)
        creation_time = time.time()
        task_ids = []
        self.db.add_session(username, session_id, creation_time, task_ids)

    def add_task(self, parent_session_id, blend_file_path):
        id = token_hex(18)
        state = 'CREATED'
        progress = '0'
        self.db.add_task(id, parent_session_id, blend_file_path, state, progress)
        new_tasks_list = self.db.get_session_tasks_by_id(parent_session_id).append(id)
        self.db.update_session_tasks_by_id(parent_session_id, new_tasks_list)

    def delete_task(self, id):
        parent_session_id = self.db.get_task_by_id(id)[0][1]
        tasks_list = self.db.get_session_tasks_by_id(parent_session_id)
        self.db.update_session_tasks_by_id(parent_session_id, tasks_list.remove(id))
        self.db.delete_task_by_id(id)

    def __del__(self):
        del self.db