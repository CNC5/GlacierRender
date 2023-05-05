import os
import subprocess
import pynvml


class Renderer:
    def __init__(self, blend_file_path, start_frame, end_frame, output_dir):
        self.killed = 0
        self.render_engine = 'CYCLES'
        self.cycles_device = 'CUDA'
        self.blender_args = ['-E', self.render_engine,
                             '-o', output_dir, '-noaudio',
                             '-s', start_frame, '-e', end_frame,
                             '-a', '--', '--cycles-device', self.cycles_device]
        self.blender_bin = os.environ['BLENDER_BIN']
        self.is_nvidia_gpu_capable = os.path.isfile('/usr/bin/nvidia-smi')
        self.is_radeon_gpu_capable = 0  # not implemented
        self.blend_file_path = blend_file_path
        self.last_line = ''
        self.status = 'SCHEDULED'

        if self.is_nvidia_gpu_capable:
            self.render = self.render_gpu_nvidia
        if self.is_radeon_gpu_capable:
            pass  # not implemented
        if not self.is_radeon_gpu_capable and not self.is_nvidia_gpu_capable:
            self.render = self.render_cpu

    def kill(self):
        self.killed = 1

    def render_cpu(self, blend_file_path):
        pass

    def render_gpu_nvidia(self):
        blender_process = subprocess.Popen(
            [self.blender_bin, '-b', self.blend_file_path] + self.blender_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
        while True:
            if self.killed:
                blender_process.kill()
                self.status = 'KILLED'
                break
            return_code = blender_process.poll()
            line = blender_process.stdout.readline()
            if line:
                self.last_line = line
            if return_code is not None:
                self.status = 'COMPLETED'
                break
