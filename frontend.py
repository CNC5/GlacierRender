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
        if not self.is_alive:
            self.address = address
            self.username = username
            self.password = password
            response = requests.get(f'{self.schema}{address}/login?'
                                    f'username={username}&'
                                    f'password={password}')
            if response.status_code == 200:
                self.is_alive = 1
                self.session_id = json.loads(response.text)
            else:
                raise Exception(response.text)

    def render(self, blend_file_path):
        if self.is_alive:
            response = requests.post(f'{self.schema}{self.address}/task/request?'
                                               f'session_id={self.session_id}',
                                               files={'file': open(blend_file_path, 'rb')})
            if response.status_code == 200:
                return json.loads(response.text)
            raise Exception('non 200 response')

    def stat(self, id):
        if self.is_alive:
            return json.loads(requests.get(f'{self.schema}{self.address}/task/stat?'
                                           f'session_id={self.session_id}&'
                                           f'task_id={id}').text)

    def delete_session(self, id):
        if self.is_alive:
            response = requests.get(f'{self.schema}{self.address}/session/remove?'
                                    f'username={self.username}&'
                                    f'password={self.password}&'
                                    f'session_id={id}')


if __name__ == '__main__':
    backend = Backend()
