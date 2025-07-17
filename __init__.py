bl_info = {
    "name": "ZelbertYQ's MOD Tool Box",
    "author": "Various (Integrated by Grok)",
    "version": (1, 0, 0),
    "blender": (3, 6, 11),  # Set to the highest required version among sub-add-ons
    "location": "View3D > Sidebar > SK Tools",
    "description": "A collection of tools for vertex colors, weight painting, vertex groups, shape keys, and bone matching.",
    "category": "中文版",
}

import bpy
from bpy.types import Panel
from .vertex_color_preset import vertex_color_preset
from .weight_paint_matching import weight_paint_matching
from .vertex_group_combiner import vertex_group_combiner
from .sk_keeper import sk_keeper
from .vertex_group_snapshot import vertex_group_snapshot
from .uv_snapshot import uv_snapshot
from .bone_match import bone_match  # 新增导入

# Main panel class
class SK_TOOLS_PT_main_panel(Panel):
    bl_label = "ZelbertYQ's MOD Tool Box"
    bl_idname = "SK_TOOLS_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ZMTB"

    def draw(self, context):
        layout = self.layout

        # SK Keeper Section
        box = layout.box()
        box.label(text="形态键处理", icon='SHAPEKEY_DATA')
        sk_keeper.draw_panel(box, context)

        # Vertex Color Preset Section
        box = layout.box()
        box.label(text="网格数据预设", icon='COLOR')
        vertex_color_preset.draw_panel(box, context)

        # Weight Paint Matching Section
        box = layout.box()
        box.label(text="权重匹配", icon='MOD_VERTEX_WEIGHT')
        weight_paint_matching.draw_panel(box, context)

        # Vertex Group Combiner Section
        box = layout.box()
        box.label(text="顶点组处理", icon='GROUP_VERTEX')
        vertex_group_combiner.draw_panel(box, context)

        # Vertex Group Snapshot Section
        box = layout.box()
        box.label(text="顶点组快照", icon='SNAP_ON')
        vertex_group_snapshot.draw_panel(box, context)

        # UV Snapshot Section
        box = layout.box()
        box.label(text="UV快照", icon='UV_DATA')
        uv_snapshot.draw_panel(box, context)

        # Bone Match Section (新增部分)
        box = layout.box()
        box.label(text="骨骼匹配", icon='BONE_DATA')
        bone_match.draw_panel(box, context)

def register():
    bpy.utils.register_class(SK_TOOLS_PT_main_panel)
    vertex_color_preset.register()
    weight_paint_matching.register()
    sk_keeper.register()
    vertex_group_combiner.register()
    vertex_group_snapshot.register()
    uv_snapshot.register()
    bone_match.register()  # 注册新模块

def unregister():
    bpy.utils.unregister_class(SK_TOOLS_PT_main_panel)
    vertex_color_preset.unregister()
    weight_paint_matching.unregister()
    sk_keeper.unregister()
    vertex_group_combiner.unregister()
    vertex_group_snapshot.unregister()
    uv_snapshot.unregister()
    bone_match.unregister()  # 注销新模块

if __name__ == "__main__":
    register()