import json
import requests
import io
import tarfile


class Backend:
    def __init__(self, no_write=False):
        self.no_write = no_write
        self.is_alive = 0
        self.tasks = []
        self.schema = 'http://'
        self.address = ''
        self.session_id = ''
        self.username = ''
        self.password = ''
        self.base_url = ''

    def connect(self, address, username, password):
        self.address = address
        self.username = username
        self.password = password
        self.base_url = self.schema + self.address
        response = requests.get(f'{self.base_url}/login?'
                                f'username={username}&'
                                f'password={password}')
        if response.status_code != 200:
            raise Exception(response.text)
        self.session_id = json.loads(response.text)['session_id']
        self.is_alive = 1
        return True

    def render(self, blend_file_path, start_frame, end_frame):
        if not self.is_alive:
            raise Exception('Connection is not alive')
        response = requests.post(f'{self.base_url}/task/request?'
                                 f'session_id={self.session_id}&'
                                 f'start_frame={start_frame}&'
                                 f'end_frame={end_frame}',
                                 files={'file': open(blend_file_path, 'rb')})
        if response.status_code != 200:
            raise Exception(response.text)
        return json.loads(response.text)

    def stat(self, task_id):
        if not self.is_alive:
            raise Exception('Connection is not alive')
        response = requests.get(f'{self.base_url}/task/stat?'
                                f'session_id={self.session_id}&'
                                f'task_id={task_id}')
        if response.status_code != 200:
            raise Exception(response.text)
        return json.loads(response.text)

    def fetch(self, task_id, load_dir):
        if self.no_write:
            print('no_write=True, fetching to RAM')
        if not self.is_alive:
            raise Exception('Connection is not alive')
        response = requests.get(f'{self.base_url}/task/result?'
                                f'session_id={self.session_id}&'
                                f'task_id={task_id}', stream=True)
        if response.status_code != 200:
            raise Exception(response.status_code)
        if self.no_write:
            return True
        with io.BytesIO(response.content) as tarball:
            tarfile.open(fileobj=tarball, format=tarfile.GNU_FORMAT).extractall(load_dir)
        return True

    def kill(self, task_id):
        if not self.is_alive:
            raise Exception('Connection is not alive')
        response = requests.get(f'{self.base_url}/task/kill?'
                                f'session_id={self.session_id}&'
                                f'task_id={task_id}')
        if response.status_code != 200:
            raise Exception(response.text)
        return task_id == json.loads(response.text)['task_id']

    def delete_session(self, session_id):
        if not self.is_alive:
            raise Exception('Connection is not alive')
        response = requests.get(f'{self.base_url}/session/remove?'
                                f'username={self.username}&'
                                f'password={self.password}&'
                                f'session_id={session_id}')
        if response.status_code != 200:
            raise Exception(response.text)
        return session_id == json.loads(response.text)['session_id']


if __name__ == '__main__':
    backend = Backend()
