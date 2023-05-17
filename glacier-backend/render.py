import subprocess
import threading
import time
import logging
import os
from config import RenderConfig

logger = logging.getLogger(__name__)


class RenderBus(RenderConfig):
    def __init__(self):
        super().__init__()
        self.tasks_by_id = {}

    def scheduler(self):
        is_last_cycle_full = False
        logger.info('task scheduler start')
        while True:
            if self.tasks_by_id:
                if not is_last_cycle_full:
                    logger.info('full scheduler cycle')
                for task in self.tasks_by_id.values():
                    if task.state == 'SCHEDULED':
                        is_last_cycle_full = True
                        task.render()
                    elif task.state == 'COMPLETED':
                        is_last_cycle_full = True
                        task.pack_output()
                time.sleep(0.5)
            else:
                if is_last_cycle_full:
                    logger.info('empty scheduler cycle')
                is_last_cycle_full = False
                time.sleep(0.5)

    def delete_task(self, task_id):
        task = self.tasks_by_id.pop(task_id)
        task.cleanup()
        return True


render_bus = RenderBus()


class Renderer(RenderConfig):
    def __init__(self, task_id, blend_file_path, start_frame, end_frame, update_callback):
        super().__init__()
        self.id = task_id
        self.update_callback = update_callback
        self.output_dir = f'{self.upload_facility}/{task_id}/'
        self.killed = 0
        self.render_engine = 'CYCLES'
        self.cycles_device = 'CUDA'
        self.blender_args = ['-E', self.render_engine,
                             '-o', self.output_dir, '-noaudio',
                             '-s', start_frame, '-e', end_frame,
                             '-a', '--', '--cycles-device', self.cycles_device]
        self.thread = None
        self.blend_file_path = blend_file_path
        self.last_line = ''
        self.state = 'SCHEDULED'
        self.update_callback(self.id, self.state)
        self.tar_path = ''
        self.render = self.render_gpu_nvidia_in_thread

        os.mkdir(f'{self.upload_facility}/{self.id}')
        render_bus.tasks_by_id.update({task_id: self})

    def kill(self):
        self.killed = 1

    def render_gpu_nvidia(self):
        blender_process = subprocess.Popen(
            [self.blender_bin, '-b', self.blend_file_path] + self.blender_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
        self.state = 'RUNNING'
        self.update_callback(self.id, self.state)
        while True:
            if self.killed:
                blender_process.kill()
                self.state = 'KILLED'
                break
            return_code = blender_process.poll()
            line = blender_process.stdout.readline()
            if line:
                self.last_line = line.decode().strip()
            if return_code is not None:
                if return_code == 0:
                    self.state = 'COMPLETED'
                else:
                    self.state = 'FAILED(BLENDER)'
                break
        self.update_callback(self.id, self.state)

    def render_gpu_nvidia_in_thread(self):
        self.thread = threading.Thread(target=self.render_gpu_nvidia)
        self.thread.start()

    def pack_output(self):
        self.state = 'COMPRESSING'
        self.update_callback(self.id, self.state)
        self.tar_path = f'{self.upload_facility}/{self.id}.tar.gz'
        result = subprocess.run(['tar', '-zcf', self.tar_path, '--directory', self.output_dir, '.'],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
        if result.returncode == 0:
            self.state = 'PACKED'
        else:
            self.state = 'FAILED(TAR)'
        self.update_callback(self.id, self.state)

    def done(self):
        self.state = 'DONE'
        self.update_callback(self.id, self.state)

    def cleanup(self):
        os.rmdir(self.blend_file_path)
        os.rmdir(self.output_dir)
        if self.tar_path:
            os.rmdir(self.tar_path)
