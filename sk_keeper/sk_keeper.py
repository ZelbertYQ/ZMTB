bl_info = {
    "name": "SKkeeper",
    "author": "Johannes Rauch",
    "version": (1, 6),
    "blender": (2, 80, 3),
    "location": "Search > Apply modifiers (Keep Shapekeys)",
    "description": "Applies modifiers and keeps shapekeys, with additional shape key utilities",
    "category": "Utility",
    "wiki_url": "https://github.com/smokejohn/SKkeeper",
}

import time
import bpy
import re
from bpy.types import Operator, PropertyGroup
from bpy.props import BoolProperty, CollectionProperty

def log(msg):
    t = time.localtime()
    current_time = time.strftime("%H:%M", t)
    print("<SKkeeper {}> {}".format(current_time, msg))

def copy_object(obj, times=1, offset=0):
    objects = []
    for i in range(0, times):
        copy_obj = obj.copy()
        copy_obj.data = obj.data.copy()
        copy_obj.name = obj.name + "_shapekey_" + str(i+1)
        copy_obj.location.x += offset*(i+1)
        bpy.context.collection.objects.link(copy_obj)
        objects.append(copy_obj)
    return objects

def apply_shapekey(obj, sk_keep):
    shapekeys = obj.data.shape_keys.key_blocks
    if sk_keep < 0 or sk_keep > len(shapekeys):
        return
    for i in reversed(range(0, len(shapekeys))):
        if i != sk_keep:
            obj.shape_key_remove(shapekeys[i])
    obj.shape_key_remove(shapekeys[0])

def apply_modifiers(obj):
    modifiers = obj.modifiers
    for modifier in modifiers:
        if modifier.type == 'SUBSURF':
            modifier.show_only_control_edges = False
    for o in bpy.context.scene.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target='MESH')

def remove_modifiers(obj):
    for i in reversed(range(0, len(obj.modifiers))):
        obj.modifiers.remove(obj.modifiers[i])

def apply_subdmod(obj):
    modifiers = [mod for mod in obj.modifiers if mod.type == 'SUBSURF']
    for o in bpy.context.scene.objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = obj
    modifiers[0].show_only_control_edges = False
    bpy.ops.object.modifier_apply(modifier=modifiers[0].name)

def apply_modifier(obj, modifier_name):
    modifier = [mod for mod in obj.modifiers if mod.name == modifier_name][0]
    for o in bpy.context.scene.objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)

def add_objs_shapekeys(destination, sources):
    for o in bpy.context.scene.objects:
        o.select_set(False)
    for src in sources:
        src.select_set(True)
    bpy.context.view_layer.objects.active = destination
    bpy.ops.object.join_shapes()

def has_vertex_displacement(obj, shape_key, base_verts, epsilon=1e-6):
    """检查形态键是否包含顶点位移"""
    shape_verts = shape_key.data
    for i in range(len(base_verts)):
        if (abs(shape_verts[i].co.x - base_verts[i].co.x) > epsilon or
            abs(shape_verts[i].co.y - base_verts[i].co.y) > epsilon or
            abs(shape_verts[i].co.z - base_verts[i].co.z) > epsilon):
            return True
    return False

class SK_TYPE_Resource(PropertyGroup):
    selected: BoolProperty(name="Selected", default=False)

class SK_OT_apply_mods_SK(Operator):
    bl_idname = "sk_tools.apply_mods_sk"
    bl_label = "应用全部修改器"
    bl_options = {'REGISTER', 'UNDO'}
    def validate_input(self, obj):
        if not obj:
            self.report({'ERROR'}, "No Active object. Please select an object")
            return {'CANCELLED'}
        if obj.type != 'MESH':
            self.report({'ERROR'}, "Wrong object type. Please select a MESH object")
            return {'CANCELLED'}
        if not obj.data.shape_keys:
            self.report({'ERROR'}, "The selected object doesn't have any shapekeys")
            return {'CANCELLED'}
        if len(obj.data.shape_keys.key_blocks) == 1:
            self.report({'ERROR'}, "The selected object only has a base shapekey")
            return {'CANCELLED'}
        if len(obj.modifiers) == 0:
            self.report({'ERROR'}, "The selected object doesn't have any modifiers")
            return {'CANCELLED'}
    def execute(self, context):
        self.obj = context.active_object
        if self.validate_input(self.obj) == {'CANCELLED'}:
            return {'CANCELLED'}
        sk_names = [block.name for block in self.obj.data.shape_keys.key_blocks]
        receiver = copy_object(self.obj, times=1, offset=0)[0]
        receiver.name = "sk_receiver"
        apply_shapekey(receiver, 0)
        apply_modifiers(receiver)
        num_shapes = len(self.obj.data.shape_keys.key_blocks)
        for i in range(1, num_shapes):
            blendshape = copy_object(self.obj, times=1, offset=0)[0]
            apply_shapekey(blendshape, i)
            apply_modifiers(blendshape)
            add_objs_shapekeys(receiver, [blendshape])
            receiver.data.shape_keys.key_blocks[i].name = sk_names[i]
            mesh_data = blendshape.data
            bpy.data.objects.remove(blendshape)
            bpy.data.meshes.remove(mesh_data)
        orig_name = self.obj.name
        orig_data = self.obj.data
        bpy.data.objects.remove(self.obj)
        bpy.data.meshes.remove(orig_data)
        receiver.name = orig_name
        return {'FINISHED'}

class SK_OT_apply_subd_SK(Operator):
    bl_idname = "sk_tools.apply_subd_sk"
    bl_label = "应用全部细分"
    bl_options = {'REGISTER', 'UNDO'}
    def validate_input(self, obj):
        if not obj:
            self.report({'ERROR'}, "No Active object. Please select an object")
            return {'CANCELLED'}
        if obj.type != 'MESH':
            self.report({'ERROR'}, "Wrong object type. Please select a MESH object")
            return {'CANCELLED'}
        if not obj.data.shape_keys:
            self.report({'ERROR'}, "The selected object doesn't have any shapekeys")
            return {'CANCELLED'}
        if len(obj.data.shape_keys.key_blocks) == 1:
            self.report({'ERROR'}, "The selected object only has a base shapekey")
            return {'CANCELLED'}
        if not [mod for mod in obj.modifiers if mod.type == 'SUBSURF']:
            self.report({'ERROR'}, "No subdivision surface modifiers")
            return {'CANCELLED'}
    def execute(self, context):
        self.obj = context.active_object
        if self.validate_input(self.obj) == {'CANCELLED'}:
            return {'CANCELLED'}
        sk_names = [block.name for block in self.obj.data.shape_keys.key_blocks]
        receiver = copy_object(self.obj, times=1, offset=0)[0]
        receiver.name = "sk_receiver"
        apply_shapekey(receiver, 0)
        apply_subdmod(receiver)
        num_shapes = len(self.obj.data.shape_keys.key_blocks)
        for i in range(1, num_shapes):
            blendshape = copy_object(self.obj, times=1, offset=0)[0]
            apply_shapekey(blendshape, i)
            apply_subdmod(blendshape)
            add_objs_shapekeys(receiver, [blendshape])
            receiver.data.shape_keys.key_blocks[i].name = sk_names[i]
            mesh_data = blendshape.data
            bpy.data.objects.remove(blendshape)
            bpy.data.meshes.remove(mesh_data)
        orig_name = self.obj.name
        orig_data = self.obj.data
        bpy.data.objects.remove(self.obj)
        bpy.data.meshes.remove(orig_data)
        receiver.name = orig_name
        return {'FINISHED'}

class SK_OT_apply_mods_choice_SK(Operator):
    bl_idname = "sk_tools.apply_mods_choice_sk"
    bl_label = "应用选定修改器"
    bl_options = {'REGISTER', 'UNDO'}
    resource_list: CollectionProperty(name="Modifier List", type=SK_TYPE_Resource)
    def invoke(self, context, event):
        self.obj = context.active_object
        if not self.obj or self.obj.type != 'MESH' or not self.obj.data.shape_keys or len(self.obj.data.shape_keys.key_blocks) == 1 or len(self.obj.modifiers) == 0:
            self.report({'ERROR'}, "Invalid object or no shapekeys/modifiers.")
            return {'CANCELLED'}
        self.resource_list.clear()
        for mod in self.obj.modifiers:
            entry = self.resource_list.add()
            entry.name = mod.name
        return context.window_manager.invoke_props_dialog(self, width=350)
    def execute(self, context):
        sk_names = [block.name for block in self.obj.data.shape_keys.key_blocks]
        receiver = copy_object(self.obj, times=1, offset=0)[0]
        receiver.name = "sk_receiver"
        apply_shapekey(receiver, 0)
        for entry in self.resource_list:
            if entry.selected:
                apply_modifier(receiver, entry.name)
        num_shapes = len(self.obj.data.shape_keys.key_blocks)
        for i in range(1, num_shapes):
            blendshape = copy_object(self.obj, times=1, offset=0)[0]
            apply_shapekey(blendshape, i)
            for entry in self.resource_list:
                if entry.selected:
                    apply_modifier(blendshape, entry.name)
            remove_modifiers(blendshape)
            add_objs_shapekeys(receiver, [blendshape])
            receiver.data.shape_keys.key_blocks[i].name = sk_names[i]
            mesh_data = blendshape.data
            bpy.data.objects.remove(blendshape)
            bpy.data.meshes.remove(mesh_data)
        orig_name = self.obj.name
        orig_data = self.obj.data
        bpy.data.objects.remove(self.obj)
        bpy.data.meshes.remove(orig_data)
        receiver.name = orig_name
        return {'FINISHED'}
    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        for entry in self.resource_list:
            row = col.row()
            row.prop(entry, 'selected', text=entry.name)

class SK_OT_sort_deform_shape_keys(Operator):
    bl_idname = "sk_tools.sort_deform_sk"
    bl_label = "排序Deform形态键"
    bl_options = {'REGISTER', 'UNDO'}
    def validate_input(self, obj):
        if not obj:
            self.report({'ERROR'}, "没有选中的对象，请选择一个对象")
            return {'CANCELLED'}
        if obj.type != 'MESH':
            self.report({'ERROR'}, "对象类型错误，请选择一个网格对象")
            return {'CANCELLED'}
        if not obj.data.shape_keys:
            self.report({'ERROR'}, "选中的对象没有形态键")
            return {'CANCELLED'}
        if len(obj.data.shape_keys.key_blocks) == 1:
            self.report({'ERROR'}, "选中的对象仅有一个基础形态键")
            return {'CANCELLED'}
    def execute(self, context):
        obj = context.active_object
        if self.validate_input(obj) == {'CANCELLED'}:
            return {'CANCELLED'}
        key_blocks = obj.data.shape_keys.key_blocks
        deform_keys = []
        for kb in key_blocks:
            if kb.name.startswith("Deform"):
                match = re.search(r'Deform\s*(\d+)', kb.name)
                if match:
                    number = int(match.group(1))
                    deform_keys.append((number, kb.name))
        if not deform_keys:
            self.report({'WARNING'}, "未找到前缀为Deform的形态键")
            return {'CANCELLED'}
        deform_keys.sort(key=lambda x: x[0])
        for num, key_name in reversed(deform_keys):
            idx = key_blocks.find(key_name)
            if idx > 0:
                for _ in range(idx, 1, -1):
                    obj.active_shape_key_index = idx
                    bpy.ops.object.shape_key_move(type='UP')
                    idx -= 1
        self.report({'INFO'}, "已按数字顺序对Deform形态键排序")
        return {'FINISHED'}

class SK_OT_remove_empty_shape_keys(Operator):
    bl_idname = "sk_tools.remove_empty_sk"
    bl_label = "删除无位移形态键"
    bl_options = {'REGISTER', 'UNDO'}
    def validate_input(self, obj):
        if not obj:
            self.report({'ERROR'}, "没有选中的对象，请选择一个对象")
            return {'CANCELLED'}
        if obj.type != 'MESH':
            self.report({'ERROR'}, "对象类型错误，请选择一个网格对象")
            return {'CANCELLED'}
        if not obj.data.shape_keys:
            self.report({'ERROR'}, "选中的对象没有形态键")
            return {'CANCELLED'}
    def execute(self, context):
        obj = context.active_object
        if self.validate_input(obj) == {'CANCELLED'}:
            return {'CANCELLED'}
        shape_keys = obj.data.shape_keys.key_blocks
        base_verts = obj.data.vertices
        if "Basis" in shape_keys:
            base_verts = shape_keys["Basis"].data
        to_remove_names = []
        for shape_key in shape_keys:
            if shape_key.name == "Basis":
                continue
            if not has_vertex_displacement(obj, shape_key, base_verts):
                to_remove_names.append(shape_key.name)
        context.view_layer.objects.active = obj
        for name in to_remove_names:
            for i, shape_key in enumerate(shape_keys):
                if shape_key.name == name:
                    obj.active_shape_key_index = i
                    log(f"删除无位移形态键: {name}")
                    bpy.ops.object.shape_key_remove()
                    break
        if to_remove_names:
            self.report({'INFO'}, f"已删除 {len(to_remove_names)} 个无位移形态键")
        else:
            self.report({'INFO'}, "未找到无位移形态键")
        return {'FINISHED'}

class SK_OT_remove_deform_shape_keys(Operator):
    bl_idname = "sk_tools.remove_deform_sk"
    bl_label = "删除Deform形态键"
    bl_options = {'REGISTER', 'UNDO'}
    def validate_input(self, obj):
        if not obj:
            self.report({'ERROR'}, "没有选中的对象，请选择一个对象")
            return {'CANCELLED'}
        if obj.type != 'MESH':
            self.report({'ERROR'}, "对象类型错误，请选择一个网格对象")
            return {'CANCELLED'}
        if not obj.data.shape_keys:
            self.report({'ERROR'}, "选中的对象没有形态键")
            return {'CANCELLED'}
    def execute(self, context):
        obj = context.active_object
        if self.validate_input(obj) == {'CANCELLED'}:
            return {'CANCELLED'}
        shape_keys = obj.data.shape_keys.key_blocks
        to_remove_names = [sk.name for sk in shape_keys if sk.name.startswith("Deform")]
        context.view_layer.objects.active = obj
        for name in to_remove_names:
            for i, shape_key in enumerate(shape_keys):
                if shape_key.name == name:
                    obj.active_shape_key_index = i
                    log(f"删除Deform形态键: {name}")
                    bpy.ops.object.shape_key_remove()
                    break
        if to_remove_names:
            self.report({'INFO'}, f"已删除 {len(to_remove_names)} 个Deform形态键")
        else:
            self.report({'INFO'}, "未找到Deform形态键")
        return {'FINISHED'}

def draw_panel(layout, context):
    row = layout.row(align=True)
    row.operator("sk_tools.apply_mods_sk")
    row.operator("sk_tools.apply_subd_sk")
    row.operator("sk_tools.apply_mods_choice_sk")
    row = layout.row(align=True)
    row.operator("sk_tools.sort_deform_sk")
    row.operator("sk_tools.remove_empty_sk")
    row.operator("sk_tools.remove_deform_sk")

def register():
    bpy.utils.register_class(SK_TYPE_Resource)
    bpy.utils.register_class(SK_OT_apply_mods_SK)
    bpy.utils.register_class(SK_OT_apply_subd_SK)
    bpy.utils.register_class(SK_OT_apply_mods_choice_SK)
    bpy.utils.register_class(SK_OT_sort_deform_shape_keys)
    bpy.utils.register_class(SK_OT_remove_empty_shape_keys)
    bpy.utils.register_class(SK_OT_remove_deform_shape_keys)

def unregister():
    bpy.utils.unregister_class(SK_OT_remove_deform_shape_keys)
    bpy.utils.unregister_class(SK_OT_remove_empty_shape_keys)
    bpy.utils.unregister_class(SK_OT_sort_deform_shape_keys)
    bpy.utils.unregister_class(SK_OT_apply_mods_choice_SK)
    bpy.utils.unregister_class(SK_OT_apply_subd_SK)
    bpy.utils.unregister_class(SK_OT_apply_mods_SK)
    bpy.utils.unregister_class(SK_TYPE_Resource)