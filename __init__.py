import logging
import sys

import bpy
import json
import time
import requests
import io
import tarfile
from bpy.props import (StringProperty,
                       BoolProperty,
                       PointerProperty,
                       IntProperty,
                       CollectionProperty)
from bpy.types import (Panel,
                       Menu,
                       Operator,
                       PropertyGroup,
                       UIList)

import threading

bl_info = {
    'name': 'Glacier Render',
    'description': '',
    'author': 'CNC5',
    'version': (0, 1, 0),
    'blender': (2, 80, 0),
    'location': 'Properties > Render',
    'warning': '',  # used for warning icon and text in addons panel
    'wiki_url': '',
    'tracker_url': '',
    'category': 'Render'
}

logging.basicConfig(stream=sys.stdout,
                    level=logging.DEBUG,
                    format='%(asctime)s %(levelname)-8s %(name)-16s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)


class Backend:
    def __init__(self, no_write=False, insecure=False):
        self.task_refresh_delay = 0.2
        self.cmd_refresh_delay = 0.1
        self.no_write = no_write
        self.is_alive = False
        self.killed = False
        if insecure:
            self.schema = 'http://'
        else:
            self.schema = 'https://'
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
        self.is_alive = True
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
        logger.debug(response.text)
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

    def delete_task(self, task_id):
        if not self.is_alive:
            raise Exception('Connection is not alive')
        response = requests.get(f'{self.base_url}/task/delete?'
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
                if not self.is_alive and func != 'connect':
                    logger.error('Connection is not alive')
                    continue
                try:
                    if func == 'connect':
                        self.connect(*args)
                    elif func == 'render':
                        self.render(*args)
                    elif func == 'fetch':
                        self.fetch(*args)
                    elif func == 'kill':
                        self.kill(*args)
                    elif func == 'delete':
                        self.delete_task(*args)
                    else:
                        pass
                except requests.exceptions.ConnectionError:
                    logger.error('Connection refused')
                except Exception as e:
                    logger.error(e)
            time.sleep(self.cmd_refresh_delay)
        logger.info('Cmd processor stopped')
        exit()

    def task_list_updater(self):
        while not self.is_alive:
            time.sleep(0.1)
        while not self.killed:
            try:
                remote_task_dict = self.list_session_tasks()
            except Exception as e:
                logger.error(e)
                time.sleep(self.task_refresh_delay)
                continue
            if remote_task_dict:
                self.task_list.clear()
                logger.debug(f'rebuild from {remote_task_dict}')
                for new_task_data in remote_task_dict.values():
                    self.task_list.add()
                    new_task = self.task_list[-1]
                    new_task.id = new_task_data['task_id']
                    new_task.name = new_task_data['task_name']
                    new_task.state = new_task_data['state']
                    new_task.progress = new_task_data['progress']
                    new_task.time_left = '00:00:10'
                    logger.debug(f'+task {new_task}')
            else:
                self.task_list.clear()
            time.sleep(self.task_refresh_delay)
        logger.info('Task list updater stopped')
        exit()


class ListItem(PropertyGroup):
    id: StringProperty(
           name='Id',
           description='Backend id',
           default='')

    name: StringProperty(
           name='Name',
           description='A name for this task',
           default='Untitled')

    state: StringProperty(
           name='State',
           description='This task state',
           default='PLANNED')

    progress: StringProperty(
           name='Progress',
           description='This task progress',
           default='0/0')


class WM_OT_ScheduleTask(Operator):
    bl_idname = 'wm.schedule_task'
    bl_label = 'Render'
    bl_description = 'Render current blend file'

    def execute(self, context):
        if not backend.is_alive:
            self.report({'ERROR'}, 'Backend is not connected')
            return {'CANCELLED'}
        if not bpy.data.is_saved:
            self.report({'ERROR'}, 'Current blend file is not saved')
            return {'CANCELLED'}
        task_name = bpy.path.basename(bpy.data.filepath)
        task_name = str(task_name).split('.')[0]
        blend_file_path = bpy.path.abspath(bpy.data.filepath)
        bpy.ops.file.pack_all()
        bpy.ops.wm.save_as_mainfile(filepath=blend_file_path)
        scene = context.scene
        if context.scene.glacier.is_animation:
            frame_start = scene.frame_start
            frame_end = scene.frame_end
        else:
            frame_start = scene.frame_current
            frame_end = scene.frame_current
        backend.command_queue.append(['render', task_name, blend_file_path, frame_start, frame_end])
        return{'FINISHED'}


class WM_OT_CancelTask(Operator):
    bl_label = 'Cancel'
    bl_idname = 'wm.cancel_task'
    bl_description = 'Terminate the task'

    @classmethod
    def poll(cls, context):
        return context.scene.task_list

    def execute(self, context):
        if not backend.is_alive:
            self.report({'ERROR'}, 'Backend is not connected')
            return {'CANCELLED'}
        selected_task = context.scene.task_list[bpy.context.scene.list_index]
        backend.command_queue.append(['kill', selected_task.id])
        return{'FINISHED'}


class WM_OT_DeleteTask(Operator):
    bl_label = 'Delete'
    bl_idname = 'wm.delete_task'
    bl_description = 'Delete the task'

    @classmethod
    def poll(cls, context):
        return context.scene.task_list

    def execute(self, context):
        if not backend.is_alive:
            self.report({'ERROR'}, 'Backend is not connected')
            return {'CANCELLED'}
        selected_task = context.scene.task_list[bpy.context.scene.list_index]
        backend.command_queue.append(['delete', selected_task.id])
        return{'FINISHED'}


class WM_OT_DownloadTaskResult(Operator):
    bl_label = 'Download'
    bl_idname = 'wm.download_task_result'
    bl_description = 'Download rendered frames'

    def execute(self, context):
        if not backend.is_alive:
            self.report({'ERROR'}, 'Backend is not connected')
            return {'CANCELLED'}
        selected_task = context.scene.task_list[bpy.context.scene.list_index]
        if selected_task.state not in ['PACKED', 'DONE']:
            self.report({'ERROR'}, 'Task is not complete')
            return {'CANCELLED'}
        download_dir = bpy.path.abspath(bpy.context.scene.render.filepath)
        backend.command_queue.append(['fetch', selected_task.id, download_dir])
        return {'FINISHED'}


class MY_UL_List(UIList):
    def draw_item(self, context, layout, data, task, icon, active_data,
                  active_propname, index):

        if task.state == 'PLANNED':
            custom_icon = 'TIME'
        elif task.state == 'SCHEDULED':
            custom_icon = 'THREE_DOTS'
        elif task.state == 'RUNNING':
            custom_icon = 'PLAY'
        elif task.state == 'COMPLETED':
            custom_icon = 'PACKAGE'
        elif task.state == 'COMPRESSING':
            custom_icon = 'TIME'
        elif task.state == 'PACKED':
            custom_icon = 'OBJECT_DATAMODE'
        elif task.state == 'DONE':
            custom_icon = 'CHECKMARK'
        elif task.state == 'KILLED':
            custom_icon = 'X'
        else:
            custom_icon = 'ERROR'

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(text=task.name, icon=custom_icon)
            layout.label(text=task.progress)
            layout.label(text=task.state)

        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text='', icon=custom_icon)


class RENDER_PT_Any:
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'render'


class RENDER_PT_MainPanel(Panel, RENDER_PT_Any):
    bl_label = 'Glacier Render'
    bl_idname = 'RENDER_PT_main_panel'

    def draw(self, context):
        if bpy.context.engine == 'CYCLES':
            self.glacier_enabled(context)
        else:
            self.glacier_disabled()

    def glacier_enabled(self, context):
        layout = self.layout
        scene = context.scene
        glacier = scene.glacier

        layout.prop(glacier, 'key_profile_path')
        if glacier.is_animation:
            layout.split(factor=0.5).prop(glacier, 'is_animation', icon='RENDER_ANIMATION')
        else:
            layout.split(factor=0.5).prop(glacier, 'is_animation', icon='RENDER_STILL')
        row = layout.row(align=True)
        if glacier.is_animation:
            row.prop(scene, 'frame_start')
            row.prop(scene, 'frame_end')
        else:
            row.split(factor=0.5).prop(scene, 'frame_current')

        row = layout.row()
        row.scale_y = 2
        row.operator('wm.schedule_task', icon='ADD')

    def glacier_disabled(self):
        layout = self.layout
        layout.label(text='Switch to Cycles')


class RENDER_PT_ManagementPanel(Panel, RENDER_PT_Any):
    bl_label = 'Manage Tasks'
    bl_parent_id = 'RENDER_PT_main_panel'

    @classmethod
    def poll(cls, context):
        return bpy.context.engine == 'CYCLES'

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        row = layout.row()
        row.label(text='Name')
        row.label(text='Progress')
        row.label(text='State')
        row = layout.row()
        row.template_list('MY_UL_List', 'The_List', scene,
                          'task_list', scene, 'list_index')

        if scene.list_index >= 0 and scene.task_list:
            row = layout.row(align=True)
            row.operator('wm.cancel_task', icon='CANCEL')
            row.operator('wm.download_task_result', icon='TRIA_DOWN_BAR')
            row.operator('wm.delete_task', icon='TRASH')


backend = Backend()


def key_path_update_callback(self,  context):
    file_path = bpy.path.abspath(bpy.context.scene.glacier.key_profile_path)
    if not file_path:
        return
    config = open(file_path).read().split('\n')
    config.remove('')
    if len(config) > 3:
        raise Exception('Bad file format')
    backend.command_queue.append(['connect', config[0], config[1], config[2]])


class GlacierProperties(PropertyGroup):
    is_animation: BoolProperty(
        name='Animation',
        description='',
        default=False)

    key_profile_path: StringProperty(
        name='GR Profile',
        description='',
        default='',
        maxlen=1024,
        subtype='FILE_PATH',
        update=key_path_update_callback)


classes = (
    GlacierProperties,
    WM_OT_ScheduleTask,
    WM_OT_CancelTask,
    WM_OT_DeleteTask,
    WM_OT_DownloadTaskResult,
    RENDER_PT_MainPanel,
    RENDER_PT_ManagementPanel,
    MY_UL_List,
    ListItem)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    bpy.types.Scene.glacier = PointerProperty(type=GlacierProperties)
    bpy.types.Scene.task_list = CollectionProperty(type=ListItem)
    bpy.types.Scene.list_index = bpy.props.IntProperty(name='Index for task_list',
                                                       default=0)
    backend.task_list = bpy.context.scene.task_list
    daemon_cmd_processor = threading.Thread(target=backend.command_queue_processor)
    daemon_list_updater = threading.Thread(target=backend.task_list_updater)
    daemon_cmd_processor.daemon = True
    daemon_list_updater.daemon = True
    daemon_cmd_processor.start()
    daemon_list_updater.start()


def unregister():
    backend.killed = True
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    del bpy.types.Scene.glacier
    del bpy.types.Scene.task_list
    del bpy.types.Scene.list_index


if __name__ == '__main__':
    register()
