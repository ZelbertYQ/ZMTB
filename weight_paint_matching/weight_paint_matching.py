bl_info = {
    "name": "Comilarex Tools",
    "author": "Comilarex",
    "version": (2, 2),
    "blender": (3, 6, 2),
    "description": "Matches vertex groups based on weight paint centroids and surface area. Also can flip and pull weight from other objects.",
    "category": "Object",
}

import bpy
import re
from bpy.props import PointerProperty, StringProperty, EnumProperty
from bpy.types import Object, Operator
from mathutils import Vector

class WeightPaintMatchingOperator(bpy.types.Operator):
    bl_idname = "sk_tools.weight_paint_matching"
    bl_label = "Match Weight Paints"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        base_obj = context.scene.weight_paint_matching_base
        target_obj = context.scene.weight_paint_matching_target
        if base_obj and target_obj:
            match_vertex_groups(base_obj, target_obj)
            self.report({'INFO'}, "Vertex groups matched.")
        else:
            self.report({'ERROR'}, "One or more objects not found.")
        return {'FINISHED'}

def get_weighted_center(obj, vgroup):
    total_weight_area = 0.0
    weighted_position_sum = Vector((0.0, 0.0, 0.0))
    vertex_influence_area = calculate_vertex_influence_area(obj)
    for vertex in obj.data.vertices:
        weight = get_vertex_group_weight(vgroup, vertex)
        influence_area = vertex_influence_area[vertex.index]
        weight_area = weight * influence_area
        if weight_area > 0:
            weighted_position_sum += obj.matrix_world @ vertex.co * weight_area
            total_weight_area += weight_area
    return weighted_position_sum / total_weight_area if total_weight_area > 0 else None

def calculate_vertex_influence_area(obj):
    vertex_area = [0.0] * len(obj.data.vertices)
    for face in obj.data.polygons:
        area_per_vertex = face.area / len(face.vertices)
        for vert_idx in face.vertices:
            vertex_area[vert_idx] += area_per_vertex
    return vertex_area

def get_vertex_group_weight(vgroup, vertex):
    for group in vertex.groups:
        if group.group == vgroup.index:
            return group.weight
    return 0.0

def match_vertex_groups(base_obj, target_obj):
    for base_group in base_obj.vertex_groups:
        base_group.name = "unknown"
    target_centers = {target_group.name: get_weighted_center(target_obj, target_group) for target_group in target_obj.vertex_groups}
    for base_group in base_obj.vertex_groups:
        base_center = get_weighted_center(base_obj, base_group)
        if base_center:
            best_match = min(target_centers.items(), key=lambda x: (base_center - x[1]).length if x[1] else float('inf'), default=None)
            if best_match:
                base_group.name = best_match[0]

class RenameUnknownVertexGroupsOperator(bpy.types.Operator):
    bl_idname = "sk_tools.renumber_unknown_vertex_groups"
    bl_label = "Renumber 'Unknown' Groups"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        obj = context.object
        if obj and obj.type == 'MESH':
            unknown_groups = [group for group in obj.vertex_groups if group.name.startswith("unknown")]
            existing_numbers = sorted([int(g.name) for g in obj.vertex_groups if g.name.isdigit()], key=int)
            missing_numbers = sorted(set(range(len(obj.vertex_groups))) - set(existing_numbers))
            for i, group in enumerate(unknown_groups):
                group.name = str(missing_numbers[i] if i < len(missing_numbers) else max(existing_numbers) + i - len(missing_numbers) + 1)
            self.report({'INFO'}, "Renumbered 'unknown' vertex groups.")
        else:
            self.report({'ERROR'}, "No mesh object selected.")
        return {'FINISHED'}

class SortVertexGroupsOperator(bpy.types.Operator):
    bl_idname = "sk_tools.sort_vertex_groups"
    bl_label = "Sort Vertex Groups"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        obj = context.object
        if obj and obj.type == 'MESH':
            bpy.context.view_layer.objects.active = obj
            sort_vertex_groups(obj)
            self.report({'INFO'}, "Vertex groups sorted numerically.")
        else:
            self.report({'ERROR'}, "No mesh object selected.")
        return {'FINISHED'}

def sort_vertex_groups(obj):
    sorted_group_names = sorted([g.name for g in obj.vertex_groups], key=numeric_key)
    for correct_idx, group_name in enumerate(sorted_group_names):
        set_active_vertex_group(obj, group_name)
        current_idx = obj.vertex_groups.find(group_name)
        while current_idx < correct_idx:
            bpy.ops.object.vertex_group_move(direction='DOWN')
            current_idx += 1
        while current_idx > correct_idx:
            bpy.ops.object.vertex_group_move(direction='UP')
            current_idx -= 1

def set_active_vertex_group(obj, group_name):
    group_index = obj.vertex_groups.find(group_name)
    if group_index != -1:
        obj.vertex_groups.active_index = group_index

def numeric_key(s):
    return [int(text) if text.isdigit() else text for text in re.split('(\d+)', s)]

class FlipWeightsOperator(bpy.types.Operator):
    bl_idname = "sk_tools.flip_weights"
    bl_label = "Flip Weights"
    bl_options = {'REGISTER', 'UNDO'}
    target_group: bpy.props.StringProperty(name="Target Vertex Group")
    axis: bpy.props.EnumProperty(name="Axis", items=[('X', "X", ""), ('Y', "Y", ""), ('Z', "Z", "")], default='X')
    def execute(self, context):
        original_obj = context.object
        if not original_obj or original_obj.type != 'MESH' or not original_obj.vertex_groups.active:
            self.report({'ERROR'}, "Invalid selection or no active vertex group.")
            return {'CANCELLED'}
        try:
            mirrored_obj = self.create_mirrored_object(original_obj, context)
            self.transfer_weights(original_obj, mirrored_obj, context)
            self.report({'INFO'}, "Weights transferred from Source to Target object.")
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        finally:
            if 'mirrored_obj' in locals():
                bpy.data.objects.remove(mirrored_obj, do_unlink=True)
        return {'FINISHED'}
    def create_mirrored_object(self, original_obj, context):
        mirrored_obj_data = original_obj.data.copy()
        mirrored_obj = bpy.data.objects.new(original_obj.name + "_mirrored", mirrored_obj_data)
        context.collection.objects.link(mirrored_obj)
        mirrored_obj.matrix_world = original_obj.matrix_world.copy()
        axis_scale = {'X': (-1, 1, 1), 'Y': (1, -1, 1), 'Z': (1, 1, -1)}
        mirrored_obj.scale = axis_scale[self.axis]
        bpy.context.view_layer.objects.active = mirrored_obj
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        return mirrored_obj
    def transfer_weights(self, original_obj, mirrored_obj, context):
        target_group_name = context.scene.flip_weights_target_group
        target_group_index = original_obj.vertex_groups.find(target_group_name)
        if target_group_index == -1:
            raise ValueError(f"Target vertex group '{target_group_name}' not found.")
        original_obj.vertex_groups.active_index = target_group_index
        bpy.context.view_layer.objects.active = original_obj
        original_obj.select_set(True)
        mirrored_obj.select_set(True)
        bpy.ops.object.data_transfer(use_reverse_transfer=True, data_type='VGROUP_WEIGHTS', layers_select_src='ACTIVE', layers_select_dst='ACTIVE', mix_mode='REPLACE', vert_mapping='POLYINTERP_NEAREST')
        original_obj.select_set(False)
        mirrored_obj.select_set(False)
        bpy.ops.object.mode_set(mode='WEIGHT_PAINT')

class WeightSwapOperator(bpy.types.Operator):
    bl_idname = "sk_tools.weight_swap"
    bl_label = "Swap Weights"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        source_obj = context.scene.weight_swap_obj_a
        target_obj = context.active_object
        if not source_obj or not target_obj or not target_obj.vertex_groups.active:
            self.report({'WARNING'}, "Invalid selection or no active vertex group.")
            return {'CANCELLED'}
        target_vg_name = target_obj.vertex_groups.active.name
        source_vg = source_obj.vertex_groups.get(target_vg_name)
        if not source_vg:
            self.report({'ERROR'}, f"Vertex group '{target_vg_name}' not found in Source Object.")
            return {'CANCELLED'}
        source_obj.vertex_groups.active_index = source_vg.index
        bpy.context.view_layer.objects.active = target_obj
        target_obj.select_set(True)
        source_obj.select_set(True)
        bpy.ops.object.data_transfer(use_reverse_transfer=True, data_type='VGROUP_WEIGHTS', layers_select_src='ACTIVE', layers_select_dst='ACTIVE', mix_mode='REPLACE', vert_mapping='POLYINTERP_NEAREST')
        target_obj.select_set(False)
        source_obj.select_set(False)
        bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
        self.report({'INFO'}, "Weights transferred from Source to Target object.")
        return {'FINISHED'}

def draw_panel(layout, context):
    scene = context.scene
    
    # Matching section
    match_col = layout.column(align=True)
    match_col.prop(scene, "weight_paint_matching_target")
    match_col.prop(scene, "weight_paint_matching_base")
    
    action_row = match_col.row(align=True)
    action_row.operator("sk_tools.weight_paint_matching", text="匹配顶点组")
    action_row.operator("sk_tools.renumber_unknown_vertex_groups", text="移除未知顶点组")

    # Flip section with button on the right
    flip_row = layout.row(align=True)
    flip_row.prop(scene, "flip_weights_target_group", text="目标")
    flip_row.operator("sk_tools.flip_weights", text="翻转")

    # Swap section with button on the right
    swap_row = layout.row(align=True)
    swap_row.prop(scene, "weight_swap_obj_a", text="参考")
    swap_row.operator("sk_tools.weight_swap", text="交换")

def register():
    bpy.utils.register_class(WeightPaintMatchingOperator)
    bpy.utils.register_class(RenameUnknownVertexGroupsOperator)
    bpy.utils.register_class(SortVertexGroupsOperator)
    bpy.utils.register_class(FlipWeightsOperator)
    bpy.utils.register_class(WeightSwapOperator)
    bpy.types.Scene.weight_paint_matching_target = PointerProperty(name="基体", description="Object to copy weight paint data from", type=Object)
    bpy.types.Scene.weight_paint_matching_base = PointerProperty(name="目标", description="Object to receive weight paint data", type=Object)
    bpy.types.Scene.flip_weights_target_group = StringProperty(name="Target Vertex Group", description="The vertex group that receives the flipped weight paint")
    bpy.types.Scene.flip_weights_axis = EnumProperty(name="Axis", items=[('X', "X", ""), ('Y', "Y", ""), ('Z', "Z", "")], default='X')
    bpy.types.Scene.weight_swap_obj_a = PointerProperty(name="Reference", description="Object from which to copy weight paint data", type=Object)

def unregister():
    bpy.utils.unregister_class(WeightSwapOperator)
    bpy.utils.unregister_class(FlipWeightsOperator)
    bpy.utils.unregister_class(SortVertexGroupsOperator)
    bpy.utils.unregister_class(RenameUnknownVertexGroupsOperator)
    bpy.utils.unregister_class(WeightPaintMatchingOperator)
    del bpy.types.Scene.weight_paint_matching_target
    del bpy.types.Scene.weight_paint_matching_base
    del bpy.types.Scene.flip_weights_target_group
    del bpy.types.Scene.flip_weights_axis
    del bpy.types.Scene.weight_swap_obj_a