import asyncio
import json
import logging
import sys

import tornado
from authenticator import AuthManager

auth = AuthManager()


def setup_logging():
    logging.basicConfig(stream=sys.stdout,
                        level=logging.INFO,
                        format='%(asctime)s %(levelname)-8s %(name)-16s: %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    logging.getLogger('tornado.access').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy').setLevel(logging.WARNING)


logger = logging.getLogger(__name__)


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
        if auth.is_session_id(session_id):
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
        self.write(json.dumps({'session_id': auth.db.get_sessions_by_username(username)[0][0].session_id}))


class SpawnHandler(tornado.web.RequestHandler):
    def post(self):  # post
        session_id = self.get_argument('session_id')
        start_frame = self.get_argument('start_frame')
        end_frame = self.get_argument('end_frame')
        task_name = self.get_argument('task_name')
        if not auth.is_session_id(session_id):
            self.set_status(401)
            self.finish('Unauthorized')
            return
        if not start_frame.isdigit() or not end_frame.isdigit():
            self.set_status(403)
            self.finish('Non-digit frames')
            return
        blend_file = self.request.files['file'][0]['body']
        new_task_id = auth.add_task(task_name, session_id, blend_file, start_frame, end_frame)
        self.write(json.dumps({'task_id': new_task_id}))


class StatHandler(tornado.web.RequestHandler):
    def get(self):
        session_id = self.get_argument('session_id')
        task_id = self.get_argument('task_id')
        if not auth.is_session_id(session_id) or not auth.is_task_id(task_id):
            self.set_status(401)
            self.finish('Unauthorized')
            return
        task = auth.db.get_task_by_id(task_id)
        task_data = task.as_dict()
        progress = str(auth.render_bus.tasks_by_id[task_id].last_line)
        task_data.update({'progress': progress})
        self.write(json.dumps(task_data))


class ResultHandler(tornado.web.RequestHandler):
    def get(self):
        session_id = self.get_argument('session_id')
        task_id = self.get_argument('task_id')
        if not auth.is_session_id(session_id) or not auth.is_task_id(task_id):
            self.set_status(401)
            self.finish('Unauthorized')
            return
        tar_path = auth.render_bus.tasks_by_id[task_id].tar_path
        if not tar_path:
            self.set_status(400)
            self.finish('Task is not complete')
            return
        with open(tar_path, 'rb') as f:
            data = f.read()
            self.write(data)
        auth.render_bus.tasks_by_id[task_id].done()
        self.finish()


class KillHandler(tornado.web.RequestHandler):
    def get(self):
        session_id = self.get_argument('session_id')
        task_id = self.get_argument('task_id')
        if not auth.is_session_id(session_id):
            self.set_status(401)
            self.finish('Unauthorized')
            return
        if not auth.is_task_id(task_id):
            self.set_status(404)
            self.finish('Task does not exist')
            return
        auth.render_bus.tasks_by_id[task_id].kill()
        self.write(json.dumps({'task_id': task_id}))


class ListHandler(tornado.web.RequestHandler):
    def get(self):
        session_id = self.get_argument('session_id')
        if not auth.is_session_id(session_id):
            self.set_status(401)
            self.finish('Unauthorized')
            return
        if not auth.is_task_by_session_id(session_id):
            self.write(json.dumps([]))
            return
        task_list = [task[0].as_dict() for task in auth.db.get_tasks_by_session_id(session_id)]
        for task in task_list:
            task_id = task['task_id']
            progress = str(auth.render_bus.tasks_by_id[task_id].last_line)
            task.update({'progress': progress})
        self.write(json.dumps(task_list))


class DeleteHandler(tornado.web.RequestHandler):
    def get(self):
        session_id = self.get_argument('session_id')
        task_id = self.get_argument('task_id')
        if not auth.is_session_id(session_id):
            self.set_status(401)
            self.finish('Unauthorized')
            return
        if not auth.is_task_id(task_id):
            self.set_status(404)
            self.finish('Task does not exist')
            return
        auth.delete_task(task_id)
        self.write(json.dumps({'task_id': task_id}))


def make_app():
    return tornado.web.Application([
        (r'/login',             AuthHandler),           # username   & password
        (r'/task/request',      SpawnHandler),          # session_id
        (r'/task/stat',         StatHandler),           # session_id & task_id
        (r'/task/result',       ResultHandler),         # session_id & task_id
        (r'/task/kill',         KillHandler),           # session_id & task_id
        (r'/task/list',         ListHandler),           # session_id
        (r'/task/delete',       DeleteHandler),         # session_id & task_id
        (r'/session/list',      SessionListHandler),    # username   & password
        (r'/session/remove',    SessionRemoveHandler)   # username   & password   & session_id
    ])


async def main_server():
    app = make_app()
    logger.info('ready to accept connections')
    app.listen(8888)
    await asyncio.Event().wait()


async def main():
    setup_logging()
    loop = asyncio.get_event_loop()
    await asyncio.gather(loop.run_in_executor(None, auth.render_bus.scheduler), main_server())


if __name__ == "__main__":
    asyncio.run(main())
