import asyncio
import tornado
from secrets import token_hex
from authenticator import Authman
import time
import logging

auth = Authman()
users = {'cnc': 'lol'}  # WIP
tasks_by_session_id = {}
tasks_by_id = {}
sessions_by_user = {}
sessions_by_id = {}

logger = logging.Logger('glacier-server')
logger.setLevel(logging.WARNING)


def info_msg(message):
    logger.info(message)


def warn_msg(message):
    logger.warning(message)


def error_msg(message):
    logger.error(message)


class Task:
    def __init__(self, blend_file_path, parent_session):
        self.id = token_hex(16)
        self.blend_file_path = blend_file_path
        self.parent_session = parent_session
        self.state = 'CREATED'
        info_msg(f'task {self.id} from user {self.parent_session.username} created')

    def render(self):
        info_msg(f'task {self.id} from user {self.parent_session.username} called to render')


class Session:
    def __init__(self, username, password):
        self.id = token_hex(20)
        self.username = username
        self.creation_time = time.time()
        info_msg(f'session {self.id} for user {self.username} created')

    def __del__(self):
        if self.id in tasks_by_session_id:
            for task in tasks_by_session_id[self.id]:
                task_id = task.id
                tasks_by_id.pop(task_id)
                del task
            tasks_by_session_id.pop(self.id)
            info_msg(f'session {self.id} for user {self.username} deleted')


class SessionListHandler(tornado.web.RequestHandler):
    def get(self):
        username = self.get_argument('username')
        password = self.get_argument('password')
        if auth.is_password_correct(username, password):
            if username in sessions_by_user:
                sessions_by_user_list = [session.id for session in sessions_by_user[username]]
                self.write(f'{sessions_by_user_list}')
            else:
                self.set_status(404)
                self.finish('[]')
        else:
            self.set_status(400)
            self.finish('400')
            return


class SessionRemoveHandler(tornado.web.RequestHandler):
    def get(self):
        username = self.get_argument('username')
        password = self.get_argument('password')
        session_id = self.get_argument('session_id')
        if not auth.is_password_correct(username, password):
            self.set_status(404)
            self.finish('404')
            return
        if username in sessions_by_user:
            if session_id in sessions_by_user[username]:
                sessions_by_user.pop(username)
                sessions_by_id.pop(session_id)
                self.write('200')
        else:
            self.set_status(404)
            self.finish('404')
            return


class AuthHandler(tornado.web.RequestHandler):
    def get(self):
        username = self.get_argument('username')
        password = self.get_argument('password')
        if auth.is_password_correct(username, password):
            new_session = Session(username, password)
            if username in sessions_by_user:
                sessions_by_user[username].append(new_session)
            else:
                sessions_by_user.update({username: [new_session]})
            sessions_by_id.update({new_session.id: new_session})
            self.write(f'{new_session.id}')
        else:
            self.set_status(404)
            self.finish('404')
            return


class SpawnHandler(tornado.web.RequestHandler):
    def get(self):  # post
        session_id = self.get_argument('session_id')
        blend_file_path = 'blend'  # ####
        if session_id not in sessions_by_id:
            self.set_status(404)
            self.finish('404')
            return
        new_task = Task(blend_file_path, sessions_by_id[session_id])
        self.write(f'{new_task.id}')
        if session_id in tasks_by_session_id and session_id in sessions_by_id:
            tasks_by_session_id[session_id].append(new_task)
        else:
            tasks_by_session_id.update({session_id: [new_task]})
        tasks_by_id.update({new_task.id: new_task})


class StatHandler(tornado.web.RequestHandler):
    def get(self):
        session_id = self.get_argument('session_id')
        task_id = self.get_argument('task_id')
        if session_id in sessions_by_id and task_id in tasks_by_id:
            task = tasks_by_id[task_id]
            self.write(f'{task.state}')
        else:
            self.set_status(404)
            self.finish('404')
            return


class ResultHandler(tornado.web.RequestHandler):
    def get(self):
        session_id = self.get_argument('session_id')
        task_id = self.get_argument('task_id')
        self.write(f'200')


class ListHandler(tornado.web.RequestHandler):
    def get(self):
        session_id = self.get_argument('session_id')
        if session_id in sessions_by_id:
            if session_id in tasks_by_session_id:
                self.write(f'{[ task.id for task in tasks_by_session_id[session_id]]}')
                return
            else:
                self.write('[]')
                return
        self.set_status(404)
        self.finish('404')


def make_app():
    return tornado.web.Application([
        (r'/login',             AuthHandler),           # username   & password
        (r'/task/request',      SpawnHandler),          # session_id
        (r'/task/stat',         StatHandler),           # session_id & task_id
        (r'/task/result',       ResultHandler),         # session_id & task_id
        (r'/task/list',         ListHandler),           # session_id
        (r'/session/list',      SessionListHandler),    # username   & password
        (r'/session/remove',    SessionRemoveHandler)   # username   & password   & session_id
    ])


async def main():
    app = make_app()
    app.listen(8888)
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
