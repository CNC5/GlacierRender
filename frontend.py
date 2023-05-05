import requests


class Backend:
    def __init__(self):
        self.is_alive = 0

    def connect(self, address, username, password):
        if not self.is_alive:
            self.address = address
            self.username = username
            self.password = password
            response = requests.get(f'{address}/login?'
                                    f'username={username}&'
                                    f'password={password}')
            if response.status_code == 200:
                self.is_alive = 1
                self.session_id = response.text

    def disconnect(self):
        if self.is_alive:
            response = requests.get(f'{self.address}/session/remove?'
                                    f'username={self.username}&'
                                    f'password={self.password}&'
                                    f'session_id={self.session_id}')
            if response.status_code == 200:
                self.is_alive = 0