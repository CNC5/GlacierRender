import bpy

from bpy.props import (StringProperty,
                       BoolProperty,
                       PointerProperty,
                       )
from bpy.types import (Panel,
                       Menu,
                       Operator,
                       PropertyGroup,
                       )

bl_info = {
    'name': 'Glacier Render',
    'description': '',
    'author': 'cnc5',
    'version': (0, 0, 3),
    'blender': (2, 80, 0),
    'location': 'Properties > Render',
    'warning': '',  # used for warning icon and text in addons panel
    'wiki_url': '',
    'tracker_url': '',
    'category': 'Render'
}


class GlacierProperties(PropertyGroup):
    is_animation: BoolProperty(
        name='Animation',
        description='',
        default=False
        )

    key_profile_path: StringProperty(
        name='GR Profile',
        description='',
        default='',
        maxlen=1024,
        subtype='FILE_PATH'
        )


class WM_OT_ScheduleTask(Operator):
    bl_label = 'Render'
    bl_idname = 'wm.schedule_task'

    def execute(self, context):
        scene = context.scene
        glacier = scene.glacier

        # print the values to the console
        print('Hello World')
        print('bool state:', glacier.is_animation)

        return {'FINISHED'}


class WM_OT_CancelTask(Operator):
    bl_label = 'Cancel'
    bl_idname = 'wm.cancel_task'

    def execute(self, context):
        scene = context.scene
        glacier = scene.glacier

        # print the values to the console
        print('Hello World')
        print('bool state:', glacier.is_animation)

        return {'FINISHED'}


class WM_OT_PauseTask(Operator):
    bl_label = 'Pause'
    bl_idname = 'wm.pause_task'

    def execute(self, context):
        scene = context.scene
        glacier = scene.glacier

        # print the values to the console
        print('Hello World')
        print('bool state:', glacier.is_animation)

        return {'FINISHED'}


class WM_OT_ResumeTask(Operator):
    bl_label = 'Resume'
    bl_idname = 'wm.resume_task'

    def execute(self, context):
        scene = context.scene
        glacier = scene.glacier

        # print the values to the console
        print('Hello World')
        print('bool state:', glacier.is_animation)

        return {'FINISHED'}


class RENDER_MT_CustomMenu(Menu):
    bl_label = 'Select'
    bl_idname = 'RENDER_MT_custom_menu'

    def draw(self, context):
        layout = self.layout

        # Built-in operators
        layout.operator('object.select_all', text='Select/Deselect All').action = 'TOGGLE'
        layout.operator('object.select_all', text='Inverse').action = 'INVERT'
        layout.operator('object.select_random', text='Random')


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
        layout.menu(RENDER_MT_CustomMenu.bl_idname, text='Presets', icon='SCENE')

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

        box = layout.column(align=True)
        box.operator('wm.cancel_task', icon='REMOVE')
        row = box.row(align=True)
        row.operator('wm.pause_task', icon='PAUSE')
        row.operator('wm.resume_task', icon='PLAY')


classes = (
    GlacierProperties,
    WM_OT_ScheduleTask,
    WM_OT_CancelTask,
    WM_OT_PauseTask,
    WM_OT_ResumeTask,
    RENDER_MT_CustomMenu,
    RENDER_PT_MainPanel,
    RENDER_PT_ManagementPanel
)

backend = Backend()


def key_path_update_callback():
    backend.reshim()


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    bpy.types.Scene.glacier = PointerProperty(type=GlacierProperties)

    sub_particles = bpy.types.PropertyGroup
    bpy.msgbus.subscribe_rna(key=sub_particles, owner=backend, args=(), notify=key_path_update_callback,)
    bpy.msgbus.publish_rna(key=sub_particles)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    del bpy.types.Scene.glacier


if __name__ == '__main__':
    register()
