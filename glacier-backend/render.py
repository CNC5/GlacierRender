import configparser
import os
import subprocess
import threading
import time
import logging

logger = logging.Logger(__name__)
logger.setLevel(logging.INFO)
environment = os.environ
if 'UPLOAD_FACILITY' not in environment:
    upload_facility = '/tmp'
else:
    upload_facility = environment['UPLOAD_FACILITY']
del environment


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
        self.output_dir = f'{upload_facility}/{task_id}/'
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
        self.update_callback(self.id, self.state)

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

    def render_any(self, cycles_device):
        self.cycles_device = cycles_device
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
                self.last_line = line
            if return_code is not None:
                if return_code == 0:
                    self.state = 'COMPLETED'
                else:
                    self.state = 'FAILED(BLENDER)'
                break
        self.update_callback(self.id, self.state)

    def render_gpu_nvidia_in_thread(self):
        self.thread = threading.Thread(target=self.render_any, args=['CUDA'])
        self.thread.start()

    def render_cpu_in_thread(self):
        self.thread = threading.Thread(target=self.render_any, args=['CPU'])
        self.thread.start()

    def pack_output(self):
        self.state = 'COMPRESSING'
        self.update_callback(self.id, self.state)
        result = subprocess.run(['tar', '-zcpvf', f'{upload_facility}/{self.id}.tar.gz', self.output_dir])
        if result.returncode == 0:
            self.state = 'PACKED'
        else:
            self.state = 'FAILED(TAR)'
        self.update_callback(self.id, self.state)
