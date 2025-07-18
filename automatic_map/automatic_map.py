import bpy
from bpy.types import Operator

# Export Mod 按钮的操作
class ZMTB_OT_export_mod(Operator):
    bl_idname = "zmtb.export_mod"
    bl_label = "Export Mod"
    
    def execute(self, context):
        # 保留测试提示
        self.report({'INFO'}, "测试按钮被点击！")
        
        # WWMI 导出逻辑
        wwmi_enabled = "WWMI-Tools" in bpy.context.preferences.addons
        if wwmi_enabled:
            if hasattr(bpy.ops.wwmi_tools, "export_mod"):
                if context.selected_objects:
                    bpy.ops.wwmi_tools.export_mod()
                    self.report({'INFO'}, "WWMI Mod 导出成功！")
                else:
                    self.report({'WARNING'}, "未选择任何对象，无法导出！")
            else:
                self.report({'ERROR'}, "Export Mod Operator未找到")
        else:
            self.report({'ERROR'}, "WWMI-Tools未安装")
        
        return {'FINISHED'}

# 顶部导航栏绘制函数
def header_button_drawer(self, context):
    layout = self.layout
    row = layout.row(align=True)
    row.operator("zmtb.export_mod", text="Export Mod", icon='EXPORT')

def register():
    bpy.utils.register_class(ZMTB_OT_export_mod)
    bpy.types.TOPBAR_HT_upper_bar.prepend(header_button_drawer)  # 使用 prepend 确保靠左

def unregister():
    bpy.utils.unregister_class(ZMTB_OT_export_mod)
    bpy.types.TOPBAR_HT_upper_bar.remove(header_button_drawer)