import configparser
import os
import subprocess
import threading
import time
import logging

logger = logging.Logger('glacier-renderer')

config_path = 'config.ini'
config = configparser.ConfigParser()
config.read(config_path)
general_config = config['database.general']
if 'upload_facility' not in general_config:
    upload_facility = '/tmp'
else:
    upload_facility = general_config['upload_facility']
del config
del general_config


def info_msg(message):
    logger.info(message)


def warn_msg(message):
    logger.warning(message)


def error_msg(message):
    logger.error(message)


class RenderBus:
    def __init__(self):
        self.tasks = []

    def scheduler(self):
        while True:
            if self.tasks:
                info_msg('full scheduler cycle')
                for task in self.tasks:
                    if task.state == 'SCHEDULED':
                        task.render()
                    elif task.state == 'COMPLETE':
                        task.pack_output()
            else:
                info_msg('empty scheduler cycle')
                time.sleep(0.5)


render_bus = RenderBus()


class Renderer:
    def __init__(self, task_id, blend_file_path, start_frame, end_frame, update_callback):
        self.id = task_id
        self.update_callback = update_callback
        self.output_dir = f'{upload_facility}/{task_id}'
        self.killed = 0
        self.render_engine = 'CYCLES'
        self.cycles_device = ''
        self.blender_args = ['-E', self.render_engine,
                             '-o', self.output_dir, '-noaudio',
                             '-s', start_frame, '-e', end_frame,
                             '-a', '--', '--cycles-device', self.cycles_device]
        self.thread = None
        self.blender_bin = os.environ['BLENDER_BIN']
        self.is_nvidia_gpu_capable = os.path.isfile('/usr/bin/nvidia-smi')
        self.is_radeon_gpu_capable = 0  # not implemented
        self.blend_file_path = blend_file_path
        self.last_line = ''
        self.state = 'SCHEDULED'
        self.update_callback(self.id)

        if self.is_nvidia_gpu_capable:
            self.render = self.render_gpu_nvidia_in_thread
        if self.is_radeon_gpu_capable:
            pass  # not implemented
        if not self.is_radeon_gpu_capable and not self.is_nvidia_gpu_capable:
            self.render = self.render_cpu_in_thread

        os.mkdir(f'{upload_facility}/{self.id}')
        render_bus.tasks.append(self)

    def kill(self):
        self.killed = 1

    def render_cpu(self):
        self.cycles_device = 'CPU'
        blender_process = subprocess.Popen(
            [self.blender_bin, '-b', self.blend_file_path] + self.blender_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
        self.state = 'RUNNING'
        while True:
            if self.killed:
                blender_process.kill()
                self.state = 'KILLED'
                break
            return_code = blender_process.poll()
            line = blender_process.stdout.readline()
            if line:
                self.last_line = line
            if return_code is not None:
                self.state = 'COMPLETED'
                break
        self.update_callback(self.id)

    def render_gpu_nvidia(self):
        self.cycles_device = 'CUDA'
        blender_process = subprocess.Popen(
            [self.blender_bin, '-b', self.blend_file_path] + self.blender_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
        self.state = 'RUNNING'
        while True:
            if self.killed:
                blender_process.kill()
                self.state = 'KILLED'
                break
            return_code = blender_process.poll()
            line = blender_process.stdout.readline()
            if line:
                self.last_line = line
            if return_code is not None:
                self.state = 'COMPLETED'
                break
        self.update_callback(self.id)

    def render_gpu_nvidia_in_thread(self):
        self.thread = threading.Thread(target=self.render_gpu_nvidia)
        self.thread.start()

    def render_cpu_in_thread(self):
        self.thread = threading.Thread(target=self.render_cpu)
        self.thread.start()

    def interactive_render(self):
        self.render()
        prev_line = ''
        while self.state not in ['COMPLETED', 'KILLED']:
            if self.last_line != prev_line:
                print(self.last_line)
            time.sleep(0.5)
        print(self.state)

    def pack_output(self):
        result = subprocess.run(['tar', '-zcpvf', f'{upload_facility}/{self.id}.tar.gz', self.output_dir])
        if result.returncode == 0:
            self.state = 'PACKED'
        else:
            self.state = 'FAILED'
        self.update_callback(self.id)
