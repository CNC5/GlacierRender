import bpy
from bpy.props import StringProperty, IntProperty, CollectionProperty
from bpy.types import PropertyGroup, UIList, Operator, Panel


class ListItem(PropertyGroup):
    name: StringProperty(
           name="Name",
           description="A name for this task",
           default="Untitled")

    state: StringProperty(
           name="State",
           description="This task state",
           default="SCHEDULED")

    progress: StringProperty(
           name="Progress",
           description="This task progress",
           default="0")

    time_left: StringProperty(
           name="ETA",
           description="This task ETA",
           default="00:00:00")


class MY_UL_List(UIList):
    def draw_item(self, context, layout, data, task, icon, active_data,
                  active_propname, index):

        if task.state == 'SCHEDULED':
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
            layout.label(text=task.name, icon = custom_icon)
            layout.label(text=task.progress)
            if task.time_left == '00:00:00':
                layout.label(text='∞')
            else:
                layout.label(text=task.time_left)
            layout.label(text=task.state)

        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon = custom_icon)


class LIST_OT_NewItem(Operator):
    bl_idname = "my_list.new_item"
    bl_label = "Add a new item"

    def execute(self, context):
        context.scene.my_list.add()

        return{'FINISHED'}


class LIST_OT_DeleteItem(Operator):
    bl_idname = "my_list.delete_item"
    bl_label = "Deletes an item"

    @classmethod
    def poll(cls, context):
        return context.scene.my_list

    def execute(self, context):
        my_list = context.scene.my_list
        index = context.scene.list_index

        my_list.remove(index)
        context.scene.list_index = min(max(0, index - 1), len(my_list) - 1)

        return{'FINISHED'}


class LIST_OT_MoveItem(Operator):
    bl_idname = "my_list.move_item"
    bl_label = "Move an item in the list"

    direction: bpy.props.EnumProperty(items=(('UP', 'Up', ""),
                                              ('DOWN', 'Down', ""),))

    @classmethod
    def poll(cls, context):
        return context.scene.my_list

    def move_index(self):
        index = bpy.context.scene.list_index
        list_length = len(bpy.context.scene.my_list) - 1  # (index starts at 0)
        new_index = index + (-1 if self.direction == 'UP' else 1)

        bpy.context.scene.list_index = max(0, min(new_index, list_length))

    def execute(self, context):
        my_list = context.scene.my_list
        index = context.scene.list_index

        neighbor = index + (-1 if self.direction == 'UP' else 1)
        my_list.move(neighbor, index)
        self.move_index()

        return{'FINISHED'}


class PT_ListExample(Panel):
    bl_label = "UI_List Demo"
    bl_idname = "SCENE_PT_LIST_DEMO"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        row = layout.row()
        row.label(text='Name')
        row.label(text='Progress')
        row.label(text='ETA')
        row.label(text='State')
        row = layout.row()
        row.template_list("MY_UL_List", "The_List", scene,
                          "my_list", scene, "list_index")

        row = layout.row()
        row.operator('my_list.new_item', text='NEW')
        row.operator('my_list.delete_item', text='REMOVE')
        row.operator('my_list.move_item', text='UP').direction = 'UP'
        row.operator('my_list.move_item', text='DOWN').direction = 'DOWN'

        if scene.list_index >= 0 and scene.my_list:
            item = scene.my_list[scene.list_index]

            row = layout.row()
            row.prop(item, "name")
            row.prop(item, "state")


def register():

    bpy.utils.register_class(ListItem)
    bpy.utils.register_class(MY_UL_List)
    bpy.utils.register_class(LIST_OT_NewItem)
    bpy.utils.register_class(LIST_OT_DeleteItem)
    bpy.utils.register_class(LIST_OT_MoveItem)
    bpy.utils.register_class(PT_ListExample)

    bpy.types.Scene.my_list = CollectionProperty(type = ListItem)
    bpy.types.Scene.list_index = IntProperty(name = "Index for my_list",
                                             default = 0)


def unregister():

    del bpy.types.Scene.my_list
    del bpy.types.Scene.list_index

    bpy.utils.unregister_class(ListItem)
    bpy.utils.unregister_class(MY_UL_List)
    bpy.utils.unregister_class(LIST_OT_NewItem)
    bpy.utils.unregister_class(LIST_OT_DeleteItem)
    bpy.utils.unregister_class(LIST_OT_MoveItem)
    bpy.utils.unregister_class(PT_ListExample)


if __name__ == "__main__":
    register()
