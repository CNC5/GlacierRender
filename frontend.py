import requests, json


class Backend:
    def __init__(self):
        self.is_alive = 0
        self.tasks = []
        self.schema = 'http://'
        self.address = ''
        self.session_id = ''
        self.username = ''
        self.password = ''

    def connect(self, address, username, password):
        self.address = address
        self.username = username
        self.password = password
        response = requests.get(f'{self.schema}{address}/login?'
                                f'username={username}&'
                                f'password={password}')
        if response.status_code == 200:
            self.session_id = json.loads(response.text)['session_id']
            self.is_alive = 1
        else:
            raise Exception(response.text)

    def render(self, blend_file_path, start_frame, end_frame):
        if self.is_alive:
            response = requests.post(f'{self.schema}{self.address}/task/request?'
                                     f'session_id={self.session_id}&'
                                     f'start_frame={start_frame}&'
                                     f'end_frame={end_frame}',
                                     files={'file': open(blend_file_path, 'rb')})
            if response.status_code == 200:
                return json.loads(response.text)
            raise Exception(response.text)

    def stat(self, id):
        if self.is_alive:
            response = requests.get(f'{self.schema}{self.address}/task/stat?'
                                           f'session_id={self.session_id}&'
                                           f'task_id={id}')
            if response.status_code == 200:
                return json.loads(response.text)
            else:
                raise Exception(response.text)

    def delete_session(self, id):
        if self.is_alive:
            response = requests.get(f'{self.schema}{self.address}/session/remove?'
                                    f'username={self.username}&'
                                    f'password={self.password}&'
                                    f'session_id={id}')


if __name__ == '__main__':
    backend = Backend()
