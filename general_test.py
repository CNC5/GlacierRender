from frontend import Backend
import time
import os
host = 'localhost:8888'
user = 'qwerty'
password = '12345'
test_blend_file_path = '../Blends/cube.blend'
start_frame = 1
end_frame = 1
output_dir = './tmp'


def test_all():
    backend = Backend(no_write=True)
    backend.connect(host, user, password)
    test_task_id = backend.render(test_blend_file_path, start_frame, end_frame)['task_id']
    state = ''
    previous_progress = ''
    while state != 'PACKED':
        response = backend.stat(test_task_id)
        state = response['state']
        progress = response['progress']
        if progress != previous_progress:
            print(progress)
            previous_progress = progress
        time.sleep(1)
    backend.fetch(test_task_id, output_dir)


if __name__ == '__main__':
    test_all()
