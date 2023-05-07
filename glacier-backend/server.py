import asyncio
import json
import logging
import sys

import tornado
from authenticator import Authman

auth = Authman()

logging.basicConfig(stream=sys.stdout,
                    level=logging.INFO,
                    format='%(asctime)s %(levelname)-8s %(name)-16s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)
tornado_logger = logging.getLogger('tornado.access')
tornado_logger.setLevel(logging.WARNING)
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)


def info_msg(message):
    logger.info(message)


def warn_msg(message):
    logger.warning(message)


def error_msg(message):
    logger.error(message)


class SessionListHandler(tornado.web.RequestHandler):
    def get(self):
        username = self.get_argument('username')
        password = self.get_argument('password')
        if not auth.is_password_correct(username, password):
            self.set_status(401)
            self.finish('Unauthorized')
            return
        if not auth.is_session_by_username(username):
            self.finish(json.dumps({'sessions': []}))
            return
        sessions_by_user_list = auth.db.get_session_by_username(username)
        self.write(json.dumps({'sessions': sessions_by_user_list}))


class SessionRemoveHandler(tornado.web.RequestHandler):
    def get(self):
        username = self.get_argument('username')
        password = self.get_argument('password')
        session_id = self.get_argument('session_id')
        if not auth.is_password_correct(username, password):
            self.set_status(401)
            self.finish('Unauthorized')
            return
        if not auth.is_session_by_username(username):
            self.set_status(404)
            self.finish('Session does not exist')
            return
        if auth.is_session(session_id):
            auth.delete_session(session_id)
            self.write(json.dumps({'session_id': session_id}))


class AuthHandler(tornado.web.RequestHandler):
    def get(self):
        username = self.get_argument('username')
        password = self.get_argument('password')
        if not auth.is_password_correct(username, password):
            self.set_status(401)
            self.finish('Unauthorized')
            return
        if not auth.is_session_by_username(username):
            new_session_id = auth.add_session(username)
            self.write(json.dumps({'session_id': new_session_id}))
            return
        self.write(json.dumps({'session_id': auth.db.get_session_by_username(username)[0].id}))


class SpawnHandler(tornado.web.RequestHandler):
    def post(self):  # post
        session_id = self.get_argument('session_id')
        start_frame = self.get_argument('start_frame')
        end_frame = self.get_argument('end_frame')
        if not auth.is_session(session_id):
            self.set_status(401)
            self.finish('Unauthorized')
            return
        if not start_frame.isdigit() or not end_frame.isdigit():
            self.set_status(403)
            self.finish('Non-digit frames')
            return
        blend_file = self.request.files['file'][0]
        new_task_id = auth.add_task(session_id, blend_file, start_frame, end_frame)
        self.write(json.dumps({'task_id': new_task_id}))


class StatHandler(tornado.web.RequestHandler):
    def get(self):
        session_id = self.get_argument('session_id')
        task_id = self.get_argument('task_id')
        if not auth.is_session(session_id) or not auth.is_task(task_id):
            self.set_status(401)
            self.finish('Unauthorized')
            return
        task = auth.db.get_task_by_id(task_id)
        task_data = task[0]._asdict()
        progress = str(auth.tasks_by_id[task_id].last_line)
        task_data.update({'progress': progress})
        self.write(json.dumps(task_data))


class ResultHandler(tornado.web.RequestHandler):
    def get(self):
        session_id = self.get_argument('session_id')
        task_id = self.get_argument('task_id')
        if not auth.is_session(session_id) or not auth.is_task(task_id):
            self.set_status(401)
            self.finish('Unauthorized')
            return
        tar_path = auth.tasks_by_id[task_id].tar_path
        with open(tar_path, 'rb') as f:
            data = f.read()
            self.write(data)
        self.finish()


class KillHandler(tornado.web.RequestHandler):
    def get(self):
        session_id = self.get_argument('session_id')
        task_id = self.get_argument('task_id')
        if not auth.is_session(session_id):
            self.set_status(401)
            self.finish('Unauthorized')
            return
        if not auth.is_task(task_id):
            self.set_status(404)
            self.finish('Task does not exist')
            return
        auth.tasks_by_id[task_id].kill()
        self.write(json.dumps({'task_id': task_id}))


class ListHandler(tornado.web.RequestHandler):
    def get(self):
        session_id = self.get_argument('session_id')
        if not auth.is_session(session_id):
            self.set_status(401)
            self.finish('Unauthorized')
            return
        if not auth.is_task_by_session_id(session_id):
            self.write(json.dumps({}))
            return
        self.write(json.dumps(auth.db.get_task_by_session_id(session_id)._asdict()))


def make_app():
    return tornado.web.Application([
        (r'/login',             AuthHandler),           # username   & password
        (r'/task/request',      SpawnHandler),          # session_id
        (r'/task/stat',         StatHandler),           # session_id & task_id
        (r'/task/result',       ResultHandler),         # session_id & task_id
        (r'/task/kill',         KillHandler),           # session_id & task_id
        (r'/task/list',         ListHandler),           # session_id
        (r'/session/list',      SessionListHandler),    # username   & password
        (r'/session/remove',    SessionRemoveHandler)   # username   & password   & session_id
    ])


async def main_server():
    app = make_app()
    info_msg('ready to accept connections')
    app.listen(8888)
    await asyncio.Event().wait()


async def main():
    loop = asyncio.get_event_loop()
    await asyncio.gather(loop.run_in_executor(None, auth.render_bus.scheduler), main_server())


if __name__ == "__main__":
    asyncio.run(main())
