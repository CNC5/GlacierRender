import hashlib
import logging
import time
from secrets import token_hex

import render
from database import UserDatabase

logger = logging.getLogger(__name__)


def hash_string(plaintext, salt):
    hashed_text = hashlib.sha3_256()
    hashed_text.update(f'{plaintext}{salt}'.encode())
    return hashed_text.hexdigest()


class Authman:
    def __init__(self):
        self.tasks_by_id = {}
        self.db = UserDatabase()
        self.render_bus = render.render_bus

    def is_user(self, username):
        return bool(self.db.get_user_by_username(username))

    def is_password_correct(self, username, password):
        if not self.is_user(username):
            return False
        user = self.db.get_user_by_username(username)[0]
        hashed_password = hash_string(password, user[2])
        if hashed_password == user.password_hash:
            return True
        return False

    def add_user(self, username, password):
        if self.is_user(username):
            return False
        salt = token_hex(10)
        password_hash = hash_string(password, salt)
        self.db.add_user(username, password_hash, salt)
        return True

    def add_session(self, username):
        session_id = token_hex(16)
        creation_time = time.time()
        self.db.add_session(username, session_id, creation_time)
        return session_id

    def is_session_by_username(self, username):
        return bool(self.db.get_session_by_username(username))

    def is_session(self, session_id):
        return bool(self.db.get_session_by_id(session_id))

    def delete_session(self, session_id):
        self.db.delete_task_by_session_id(session_id)
        self.db.delete_session_by_id(session_id)

    def add_task(self, parent_session_id, blend_file, start_frame, end_frame):
        task_id = token_hex(18)
        state = 'CREATED'
        file_path = f'{self.db.upload_facility}/{task_id}.blend'
        username = self.db.get_session_by_id(parent_session_id)[0].username
        with open(file_path, 'wb') as blend_file_on_disk:
            blend_file_on_disk.write(blend_file['body'])
        self.db.add_task(task_id, parent_session_id, username, file_path, state)
        new_task = render.Renderer(task_id, file_path, start_frame, end_frame, self.task_updater)
        self.tasks_by_id.update({task_id: new_task})
        return task_id

    def task_updater(self, task_id, new_state):
        logger.info(f'task {task_id} state changed to {new_state}')
        self.db.update_task_state(task_id, new_state)

    def is_task(self, task_id):
        return bool(self.db.get_task_by_id(task_id))

    def is_task_by_session_id(self, session_id):
        return bool(self.db.get_task_by_session_id(session_id))

    def delete_task(self, task_id):
        self.db.delete_task_by_id(task_id)

    def __del__(self):
        del self.db


if __name__ == '__main__':
    auth = Authman()
