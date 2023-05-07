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
logger.setLevel(logging.INFO)
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
        if auth.is_password_correct(username, password):
            if auth.is_session_by_username(username):
                sessions_by_user_list = auth.db.get_session_by_username(username)
                self.write(json.dumps(sessions_by_user_list))
            else:
                self.finish(json.dumps([]))
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
        if auth.is_session_by_username(username):
            if auth.is_session(session_id):
                auth.delete_session(session_id)
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
            if auth.is_session_by_username(username):
                self.write(json.dumps({'session_id': auth.db.get_session_by_username(username)[0].id}))
            else:
                new_session_id = auth.add_session(username)
                self.write(json.dumps({'session_id': new_session_id}))
        else:
            self.set_status(404)
            self.finish('404')
            return


class SpawnHandler(tornado.web.RequestHandler):
    def post(self):  # post
        session_id = self.get_argument('session_id')
        start_frame = self.get_argument('start_frame')
        end_frame = self.get_argument('end_frame')
        if not auth.is_session(session_id) or not start_frame.isdigit() or not end_frame.isdigit():
            self.set_status(404)
            self.finish('Unauthorized')
            return
        blend_file = self.request.files['file'][0]
        new_task_id = auth.add_task(session_id, blend_file, start_frame, end_frame)
        self.write(json.dumps({'task_id': new_task_id}))


class StatHandler(tornado.web.RequestHandler):
    def get(self):
        session_id = self.get_argument('session_id')
        task_id = self.get_argument('task_id')
        if auth.is_session(session_id) and auth.is_task(task_id):
            task = auth.db.get_task_by_id(task_id)
            task_data = task[0]._asdict()
            progress = str(auth.tasks_by_id[task_id].last_line)
            task_data.update({'progress': progress})
            self.write(json.dumps(task_data))
        else:
            self.set_status(404)
            self.finish('404')
            return


class ResultHandler(tornado.web.RequestHandler):
    def get(self):
        session_id = self.get_argument('session_id')
        task_id = self.get_argument('task_id')
        self.write(f'200')


class KillHandler(tornado.web.RequestHandler):
    def get(self):
        session_id = self.get_argument('session_id')
        task_id = self.get_argument('task_id')
        if auth.is_session(session_id) and auth.is_task(task_id):
            auth.tasks_by_id[task_id].kill()


class ListHandler(tornado.web.RequestHandler):
    def get(self):
        session_id = self.get_argument('session_id')
        if auth.is_session(session_id):
            if auth.is_task_by_session_id(session_id):
                self.write(json.dumps(auth.db.get_task_by_session_id(session_id)._asdict()))
                return
            else:
                self.write(json.dumps([]))
                return
        self.set_status(404)
        self.finish('404')


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
    app.listen(8888)
    await asyncio.Event().wait()


async def main():
    loop = asyncio.get_event_loop()
    await asyncio.gather(loop.run_in_executor(None, auth.render_bus.scheduler), main_server())


if __name__ == "__main__":
    asyncio.run(main())
