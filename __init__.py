bl_info = {
    "name": "ZelbertYQ's MOD Tool Box",
    "author": "Various (Integrated by Grok)",
    "version": (1, 0, 0),
    "blender": (3, 6, 11),
    "location": "View3D > Sidebar > SK Tools, Header > Export Mod",
    "description": "A collection of tools for vertex colors, weight painting, vertex groups, shape keys, bone matching, and mod exporting.",
    "category": "中文版",
}

import bpy
from bpy.types import Panel, Operator
from .vertex_color_preset import vertex_color_preset
from .weight_paint_matching import weight_paint_matching
from .vertex_group_combiner import vertex_group_combiner
from .sk_keeper import sk_keeper
from .vertex_group_snapshot import vertex_group_snapshot
from .uv_snapshot import uv_snapshot
from .bone_match import bone_match
from .automatic_map import automatic_map

class ZMTB_OT_export_mod(Operator):
    bl_idname = "zmtb.export_mod"
    bl_label = "Export Mod"
    
    def execute(self, context):
        wwmi_enabled = "WWMI-Tools" in bpy.context.preferences.addons
        if wwmi_enabled:
            if hasattr(bpy.ops.wwmi_tools, "export_mod"):
                try:
                    bpy.ops.wwmi_tools.export_mod()
                    self.report({'INFO'}, "WWMI Mod 导出成功！")
                except Exception as e:
                    self.report({'ERROR'}, f"导出失败: {str(e)}")
            else:
                self.report({'ERROR'}, "Export Mod Operator未找到")
        else:
            self.report({'ERROR'}, "WWMI-Tools未安装")
        
        return {'FINISHED'}

def header_button_drawer(self, context):
    if context.region.alignment == 'RIGHT':
        layout = self.layout
        row = layout.row(align=True)
        row.operator("zmtb.export_mod", text="Export Mod", icon='EXPORT')

class SK_TOOLS_PT_main_panel(Panel):
    bl_label = "ZelbertYQ's MOD Tool Box"
    bl_idname = "SK_TOOLS_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ZMTB"

    def draw(self, context):
        layout = self.layout

        # 自动贴图（可折叠）
        box = layout.box()
        row = box.row()
        row.prop(context.scene, "zmtb_automatic_map_collapsed", icon="TRIA_DOWN" if not context.scene.zmtb_automatic_map_collapsed else "TRIA_RIGHT", text="自动贴图", emboss=False)
        row.operator("zmtb.one_click_shade", text="一键着色", icon='MATERIAL')
        print(f"Automatic Map collapsed: {context.scene.zmtb_automatic_map_collapsed}")  # 调试输出
        if not context.scene.zmtb_automatic_map_collapsed:
            props = context.scene.zmtb_automatic_map
            box.prop(props, "collection")
            box.prop(props, "dump_dir")
            box.prop(props, "frame_dir")
            box.operator("zmtb.update_directories_from_wwmi", text="从 WWMI 获取目录")
            box.operator("zmtb.apply_diffuse_textures", text="应用漫反射贴图")

        # 形态键处理
        box = layout.box()
        box.label(text="形态键处理", icon='SHAPEKEY_DATA')
        sk_keeper.draw_panel(box, context)

        # 网格数据预设
        box = layout.box()
        box.label(text="网格数据预设", icon='COLOR')
        vertex_color_preset.draw_panel(box, context)

        # 权重匹配
        box = layout.box()
        box.label(text="权重匹配", icon='MOD_VERTEX_WEIGHT')
        weight_paint_matching.draw_panel(box, context)

        # 顶点组处理
        box = layout.box()
        box.label(text="顶点组处理", icon='GROUP_VERTEX')
        vertex_group_combiner.draw_panel(box, context)

        # 顶点组快照
        box = layout.box()
        box.label(text="顶点组快照", icon='SNAP_ON')
        vertex_group_snapshot.draw_panel(box, context)

        # UV快照
        box = layout.box()
        box.label(text="UV快照", icon='UV_DATA')
        uv_snapshot.draw_panel(box, context)

        # 骨骼匹配
        box = layout.box()
        box.label(text="骨骼匹配", icon='BONE_DATA')
        bone_match.draw_panel(box, context)

def register():
    bpy.utils.register_class(SK_TOOLS_PT_main_panel)
    bpy.utils.register_class(ZMTB_OT_export_mod)
    bpy.types.TOPBAR_HT_upper_bar.prepend(header_button_drawer)
    bpy.types.Scene.zmtb_automatic_map_collapsed = bpy.props.BoolProperty(
        name="Collapse Automatic Map",
        description="Toggle visibility of the Automatic Map panel",
        default=True
    )
    vertex_color_preset.register()
    weight_paint_matching.register()
    sk_keeper.register()
    vertex_group_combiner.register()
    vertex_group_snapshot.register()
    uv_snapshot.register()
    bone_match.register()
    automatic_map.register()

def unregister():
    bpy.utils.unregister_class(SK_TOOLS_PT_main_panel)
    bpy.utils.unregister_class(ZMTB_OT_export_mod)
    bpy.types.TOPBAR_HT_upper_bar.remove(header_button_drawer)
    del bpy.types.Scene.zmtb_automatic_map_collapsed
    vertex_color_preset.unregister()
    weight_paint_matching.unregister()
    sk_keeper.unregister()
    vertex_group_combiner.unregister()
    vertex_group_snapshot.unregister()
    uv_snapshot.unregister()
    bone_match.unregister()
    automatic_map.unregister()

if __name__ == "__main__":
    register()