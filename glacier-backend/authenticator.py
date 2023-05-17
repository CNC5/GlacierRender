import logging
import time
from secrets import token_hex
from uuid import uuid4

import argon2

import render
from database import OperatorAliases

logger = logging.getLogger(__name__)


class AuthManager:
    def __init__(self):
        self.tasks_by_id = {}
        self.db = OperatorAliases()
        self.render_bus = render.render_bus
        self.argon_hasher = argon2.PasswordHasher()

    def is_user(self, username):
        return bool(self.db.get_user_by_username(username))

    def is_password_correct(self, username, candidate_password):
        expected_end_time = time.time() + 5
        user = self.db.get_user_by_username(username)
        is_password_correct = False
        if user:
            password_hash = user.password_hash
            user_exists = True
        else:
            user_exists = False
        if user_exists:
            try:
                self.argon_hasher.verify(password_hash, candidate_password)
                is_password_correct = True
            except argon2.exceptions.VerifyMismatchError:
                pass
        if user_exists:
            if is_password_correct:
                auth_result = True
        else:
            auth_result = False
        time.sleep(expected_end_time - time.time())
        return auth_result

    def add_user(self, username, password):
        if self.is_user(username):
            return False
        password_hash = self.argon_hasher.hash(password)
        return self.db.add_user(username=username,
                                password_hash=password_hash)

    def add_session(self, username):
        session_id = token_hex(16)
        creation_time = time.time()
        self.db.add_session(username=username,
                            session_id=session_id,
                            creation_time=creation_time)
        return session_id

    def is_session_by_username(self, username):
        return bool(self.db.get_sessions_by_username(username))

    def is_session(self, session_id):
        return bool(self.db.get_session_by_id(session_id))

    def delete_session(self, session_id):
        self.db.delete_task_by_session_id(session_id)
        self.db.delete_session_by_id(session_id)

    def add_task(self, task_name, parent_session_id, blend_file, start_frame, end_frame):
        task_id = uuid4().hex
        state = 'CREATED'
        file_path = f'{self.render_bus.upload_facility}/{task_id}.blend'
        username = self.db.get_session_by_id(parent_session_id).username
        with open(file_path, 'wb') as blend_file_on_disk:
            blend_file_on_disk.write(blend_file)
        self.db.add_task(task_name=task_name,
                         task_id=task_id,
                         parent_session_id=parent_session_id,
                         username=username,
                         blend_file_path=file_path,
                         state=state)
        new_task = render.Renderer(task_id, file_path, start_frame, end_frame, self.task_updater)
        self.tasks_by_id.update({task_id: new_task})
        return task_id

    def task_updater(self, task_id, new_state):
        logger.info(f'task {task_id} state changed to {new_state}')
        self.db.update_task_state(task_id, new_state)

    def is_task(self, task_id):
        return bool(self.db.get_task_by_id(task_id))

    def is_task_by_session_id(self, session_id):
        return bool(self.db.get_tasks_by_session_id(session_id))

    def delete_task(self, task_id):
        self.db.delete_task_by_id(task_id)
        self.render_bus.delete_task(task_id)

    def __del__(self):
        del self.db


if __name__ == '__main__':
    auth = AuthManager()
