import json
import time

import requests
import io
import tarfile


class Backend:
    def __init__(self, no_write=False):
        self.no_write = no_write
        self.is_alive = 0
        self.killed = False
        self.schema = 'http://'
        self.address = ''
        self.session_id = ''
        self.username = ''
        self.password = ''
        self.base_url = ''
        self.command_queue = []
        self.task_list = None

    def task_list_to_id_dict(self, task_list):
        task_dict = {}
        for task in task_list:
            task_dict.update({task['task_id']: task})
        return task_dict

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

    def render(self, task_name, blend_file_path, start_frame, end_frame):
        if not self.is_alive:
            raise Exception('Connection is not alive')
        response = requests.post(f'{self.base_url}/task/request?'
                                 f'session_id={self.session_id}&'
                                 f'start_frame={start_frame}&'
                                 f'end_frame={end_frame}&'
                                 f'task_name={task_name}',
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

    def list_session_tasks(self):
        if not self.is_alive:
            raise Exception('Connection is not alive')
        response = requests.get(f'{self.base_url}/task/list?'
                                f'session_id={self.session_id}')
        if response.status_code != 200:
            raise Exception(response.text)
        return self.task_list_to_id_dict(json.loads(response.text))

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

    def command_queue_processor(self):
        while not self.killed:
            if self.command_queue:
                command = self.command_queue.pop(0)
                func = command.pop(0)
                args = command
                if func == 'connect':
                    self.connect(*args)
                elif func == 'render':
                    self.render(*args)
                elif func == 'fetch':
                    self.fetch(*args)
                elif func == 'kill':
                    self.kill(*args)
                else:
                    pass
            else:
                time.sleep(0.05)

    def task_list_updater(self):
        while not self.is_alive:
            time.sleep(0.1)
        while not self.killed:
            task_dict_raw = self.list_session_tasks()
            index = 0
            while True:
                max_index = len(self.task_list) - 1
                task = self.task_list[index]
                if index == max_index:
                    if task_dict_raw:
                        for new_task_data in task_dict_raw:
                            self.task_list.add()
                            new_task = self.task_list[index]
                            new_task.id = new_task_data['task_id']
                            new_task.name = new_task_data['task_name']
                            new_task.state = new_task_data['state']
                        break
                    else:
                        break
                else:
                    if task.id not in task_dict_raw:
                        self.task_list.remove(index)
                        continue
                    else:
                        new_task_data = task_dict_raw.pop(task.id)
                        task.state = new_task_data['state']
                        task.progress = new_task_data['progress']
                        index += 1
                        continue


if __name__ == '__main__':
    backend = Backend()
