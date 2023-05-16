from frontend import Backend
import time
import os
host = 'localhost:8888'
user = 'qwerty'
password = '12345'
test_blend_file_path = '../Blends/cube.blend'
start_frame = 1
end_frame = 5
output_dir = './tmp'
poll_delay = 0.5


def test_all():
    backend = Backend(no_write=True)
    backend.connect(host, user, password)
    test_task_id = backend.render('Cube', test_blend_file_path, start_frame, end_frame)['task_id']
    state = ''
    previous_progress = ''
    time.sleep(1)
    print(backend.list_session_tasks())
    while state != 'PACKED':
        response = backend.stat(test_task_id)
        state = response['state']
        progress = response['progress']
        name = response['task_name']
        if progress != previous_progress:
            print(f'{name}: {progress}')
            previous_progress = progress
        time.sleep(poll_delay)
    backend.fetch(test_task_id, output_dir)


if __name__ == '__main__':
    test_all()
