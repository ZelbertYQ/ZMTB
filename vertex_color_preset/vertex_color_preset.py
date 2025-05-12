bl_info = {
    "name": "顶点色快速预设",
    "author": "夏末",
    "version": (1, 5),
    "blender": (3, 6, 11),
    "location": "工具栏",
    "description": "顶点色预设和自定义",
    "warning": "",
    "doc_url": "",
    "category": "中文版",
}

import bpy

class CustomProperties(bpy.types.PropertyGroup):
    a: bpy.props.FloatProperty(name="Red", default=1.0, min=0.0, max=1.0, precision=3)
    b: bpy.props.FloatProperty(name="Green", default=0.216, min=0.0, max=1.0, precision=3)
    c: bpy.props.FloatProperty(name="Blue", default=0.216, min=0.0, max=1.0, precision=3)
    d: bpy.props.FloatProperty(name="Alpha", default=0.304, min=0.0, max=1.0, precision=3)
    is_ming_chao_selected: bpy.props.BoolProperty(name="Ming Chao Selected", default=False)

class SET_DEFAULT_COLOR_YS_OT(bpy.types.Operator):
    bl_idname = "sk_tools.set_default_color_ys"
    bl_label = "Set Genshin Default Color"
    def execute(self, context):
        props = context.scene.custom_props
        props.a = 1.0
        props.b = 0.216
        props.c = 0.216
        props.d = 0.302
        props.is_ming_chao_selected = False
        return {'FINISHED'}

class SET_DEFAULT_COLOR_BT_OT(bpy.types.Operator):
    bl_idname = "sk_tools.set_default_color_bt"
    bl_label = "Set Honkai BT Default Color"
    def execute(self, context):
        props = context.scene.custom_props
        props.a = 1.0
        props.b = 0.216
        props.c = 0.0
        props.d = 0.302
        props.is_ming_chao_selected = False
        return {'FINISHED'}

class SET_DEFAULT_COLOR_ZZZ_OT(bpy.types.Operator):
    bl_idname = "sk_tools.set_default_color_zzz"
    bl_label = "Set ZZZ Default Color"
    def execute(self, context):
        props = context.scene.custom_props
        props.a = 0.216
        props.b = 0.216
        props.c = 0.0
        props.d = 0.0
        props.is_ming_chao_selected = False
        return {'FINISHED'}

class SET_DEFAULT_COLOR_MT_OT(bpy.types.Operator):
    bl_idname = "sk_tools.set_default_color_mt"
    bl_label = "Set Ming Chao Default Color"
    def execute(self, context):
        props = context.scene.custom_props
        props.a = 1.0
        props.b = 0.216
        props.c = 0.0
        props.d = 0.0
        props.is_ming_chao_selected = True
        return {'FINISHED'}

class ADD_COLOR_ATTRIBUTE_OT(bpy.types.Operator):
    bl_idname = "sk_tools.add_color_attribute"
    bl_label = "添加颜色属性"
    def execute(self, context):
        props = context.scene.custom_props
        color = (props.a, props.b, props.c, props.d)  # COLOR 使用用户指定的 RGBA
        color1 = (0.0, 0.0, 0.0, 0.0)  # COLOR1 固定为 (0, 0, 0, 0)
        selected_objects = bpy.context.selected_objects
        if not selected_objects:
            self.report({'WARNING'}, "No objects selected!")
            return {'CANCELLED'}
        for obj in selected_objects:
            if obj.type == 'MESH':
                # 处理 COLOR 属性
                if "COLOR" in obj.data.attributes:
                    obj.data.attributes.remove(obj.data.attributes["COLOR"])
                color_attr = obj.data.attributes.new(name="COLOR", domain='CORNER', type='BYTE_COLOR')
                for i in range(len(color_attr.data)):
                    color_attr.data[i].color = color
                
                # 处理 COLOR1 属性（仅在 Ming Chao 选中时）
                if props.is_ming_chao_selected:
                    if "COLOR1" in obj.data.attributes:
                        obj.data.attributes.remove(obj.data.attributes["COLOR1"])
                    color_attr1 = obj.data.attributes.new(name="COLOR1", domain='CORNER', type='BYTE_COLOR')
                    for i in range(len(color_attr1.data)):
                        color_attr1.data[i].color = color1
                    self.report({'INFO'}, f"Added 'COLOR' ({color}) and 'COLOR1' ({color1}) for {obj.name}")
                else:
                    self.report({'INFO'}, f"Added 'COLOR' ({color}) for {obj.name}")
            else:
                self.report({'WARNING'}, f"{obj.name} is not a mesh!")
        return {'FINISHED'}

class OBJECT_OT_uv_name(bpy.types.Operator):
    bl_idname = "sk_tools.uv_name"
    bl_label = "UV Name"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        selected_objects = bpy.context.selected_objects
        for obj in selected_objects:
            for i, uv_map in enumerate(obj.data.uv_layers):
                uv_map.name = f"TEXCOORD{i}.xy" if i > 0 else "TEXCOORD.xy"
        return {'FINISHED'}

class xiamotools(bpy.types.Operator):
    bl_idname = "sk_tools.caizhifenli"
    bl_label = "按材质名称分离"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        bpy.ops.mesh.separate(type='MATERIAL')
        for i in range(len(bpy.context.selected_objects)):
            bpy.context.selected_objects[i].name = bpy.context.selected_objects[i].active_material.name
        return {'FINISHED'}

def draw_panel(layout, context):
    props = context.scene.custom_props
    
    # RGB通道属性排列行
    prop_row = layout.row(align=True)
    prop_row.prop(props, "a", text="R")
    prop_row.prop(props, "b", text="G")
    prop_row.prop(props, "c", text="B")
    prop_row.prop(props, "d", text="A")

    # 第一行：预设按钮
    preset_row = layout.row(align=True)
    preset_row.operator("sk_tools.set_default_color_ys", text="原神")
    preset_row.operator("sk_tools.set_default_color_bt", text="崩坏3")
    preset_row.operator("sk_tools.set_default_color_zzz", text="绝区零")
    preset_row.operator("sk_tools.set_default_color_mt", text="鸣潮")

    # 第二行：功能按钮
    action_row = layout.row(align=True)
    action_row.operator("sk_tools.caizhifenli", text="按材质分离模型")
    action_row.operator("sk_tools.uv_name", text="重命名UV")
    action_row.operator("sk_tools.add_color_attribute")


def register():
    bpy.utils.register_class(CustomProperties)
    bpy.types.Scene.custom_props = bpy.props.PointerProperty(type=CustomProperties)
    bpy.utils.register_class(SET_DEFAULT_COLOR_YS_OT)
    bpy.utils.register_class(SET_DEFAULT_COLOR_BT_OT)
    bpy.utils.register_class(SET_DEFAULT_COLOR_ZZZ_OT)
    bpy.utils.register_class(SET_DEFAULT_COLOR_MT_OT)
    bpy.utils.register_class(ADD_COLOR_ATTRIBUTE_OT)
    bpy.utils.register_class(OBJECT_OT_uv_name)
    bpy.utils.register_class(xiamotools)

def unregister():
    bpy.utils.unregister_class(xiamotools)
    bpy.utils.unregister_class(OBJECT_OT_uv_name)
    bpy.utils.unregister_class(ADD_COLOR_ATTRIBUTE_OT)
    bpy.utils.unregister_class(SET_DEFAULT_COLOR_MT_OT)
    bpy.utils.unregister_class(SET_DEFAULT_COLOR_ZZZ_OT)
    bpy.utils.unregister_class(SET_DEFAULT_COLOR_BT_OT)
    bpy.utils.unregister_class(SET_DEFAULT_COLOR_YS_OT)
    del bpy.types.Scene.custom_props
    bpy.utils.unregister_class(CustomProperties)