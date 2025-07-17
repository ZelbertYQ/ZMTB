import bpy
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import StringProperty, BoolProperty
from mathutils import Vector, Quaternion, Euler
import re
import os

class BoneMatchProperties(PropertyGroup):
    """存储 BoneMatch 的属性"""
    custom_mapping: StringProperty(  # type: ignore
        name="自定义骨骼映射",
        description="输入骨骼对（例如，arm.R:arm.L），每行一对",
        default=""
    )
    use_default_mapping: BoolProperty(  # type: ignore
        name="使用默认映射算法",
        description="使用默认命名规则（例如，.L/.R）进行骨骼匹配",
        default=True
    )
    location_flip_x: BoolProperty(  # type: ignore
        name="X",
        description="控制位移 X 轴是否翻转",
        default=True
    )
    location_flip_y: BoolProperty(  # type: ignore
        name="Y",
        description="控制位移 Y 轴是否翻转",
        default=True
    )
    location_flip_z: BoolProperty(  # type: ignore
        name="Z",
        description="控制位移 Z 轴是否翻转",
        default=True
    )
    rotation_flip_w: BoolProperty(  # type: ignore
        name="W",
        description="控制四元数旋转的 W 分量是否翻转",
        default=False
    )
    rotation_flip_x: BoolProperty(  # type: ignore
        name="X",
        description="控制旋转 X 分量是否翻转",
        default=True
    )
    rotation_flip_y: BoolProperty(  # type: ignore
        name="Y",
        description="控制旋转 Y 分量是否翻转",
        default=True
    )
    rotation_flip_z: BoolProperty(  # type: ignore
        name="Z",
        description="控制旋转 Z 分量是否翻转",
        default=True
    )
    scale_flip_x: BoolProperty(  # type: ignore
        name="X",
        description="控制缩放 X 轴是否翻转",
        default=True
    )
    scale_flip_y: BoolProperty(  # type: ignore
        name="Y",
        description="控制缩放 Y 轴是否翻转",
        default=True
    )
    scale_flip_z: BoolProperty(  # type: ignore
        name="Z",
        description="控制缩放 Z 轴是否翻转",
        default=True
    )

class SK_TOOLS_OT_bone_match(Operator):
    """翻转变换到对侧骨骼"""
    bl_idname = "sk_tools.bone_match"
    bl_label = "翻转变换"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.mode == 'POSE' and context.active_object and
                context.active_object.type == 'ARMATURE' and context.selected_pose_bones)

    def has_transform(self, bone):
        """检查骨骼是否存在位移、旋转或缩放"""
        default_location = Vector((0, 0, 0))
        default_scale = Vector((1, 1, 1))
        default_quat = Quaternion((1, 0, 0, 0))
        default_euler = Euler((0, 0, 0))
        default_axis_angle = (0, 0, 0, 0)

        if (bone.location - default_location).magnitude > 0.0001:
            return True

        if bone.rotation_mode == 'QUATERNION':
            if (bone.rotation_quaternion - default_quat).magnitude > 0.0001:
                return True
        elif bone.rotation_mode == 'AXIS_ANGLE':
            angle, x, y, z = bone.rotation_axis_angle
            if abs(angle) > 0.0001 or (x, y, z) != (0, 0, 0):
                return True
        else:  # Euler
            if (bone.rotation_euler - default_euler).magnitude > 0.0001:
                return True

        if (bone.scale - default_scale).magnitude > 0.0001:
            return True

        return False

    def execute(self, context):
        armature = context.active_object
        props = context.scene.bone_match_props
        selected_bones = context.selected_pose_bones

        # 检查是否有任何轴被启用
        if not (props.location_flip_x or props.location_flip_y or props.location_flip_z or
                props.rotation_flip_w or props.rotation_flip_x or props.rotation_flip_y or props.rotation_flip_z or
                props.scale_flip_x or props.scale_flip_y or props.scale_flip_z):
            self.report({'ERROR'}, "未启用任何翻转轴（位移、旋转或缩放的 W/X/Y/Z）")
            return {'CANCELLED'}

        # 分离有变换和无变换的骨骼
        bones_with_transform = []
        bones_without_transform = []
        for bone in selected_bones:
            if self.has_transform(bone):
                bones_with_transform.append(bone)
            else:
                bones_without_transform.append(bone)

        # 处理有变换的骨骼，翻转到对应的无变换骨骼
        flipped_count = 0
        for source_bone in bones_with_transform:
            opposite_bone_name = self.get_opposite_bone(source_bone.name, props)
            if not opposite_bone_name:
                self.report({'WARNING'}, f"未找到 {source_bone.name} 的对侧骨骼")
                continue

            opposite_bone = armature.pose.bones.get(opposite_bone_name)
            if not opposite_bone:
                self.report({'WARNING'}, f"对侧骨骼 {opposite_bone_name} 在骨架中不存在")
                continue

            if opposite_bone in bones_with_transform:
                self.report({'WARNING'}, f"跳过 {source_bone.name}，因为 {opposite_bone_name} 已有变换")
                continue

            self.flip_transform(source_bone, opposite_bone, props)
            flipped_count += 1

        if flipped_count == 0:
            self.report({'ERROR'}, "未执行任何翻转，可能没有有效的骨骼对或目标骨骼已有变换")
            return {'CANCELLED'}

        self.report({'INFO'}, f"已将 {flipped_count} 个骨骼的变换翻转到对侧骨骼")
        return {'FINISHED'}

    def get_opposite_bone(self, bone_name, props):
        """获取对侧骨骼名称"""
        if props.custom_mapping:
            mapping = self.parse_custom_mapping(props.custom_mapping)
            for src, dst in mapping:
                if src == bone_name:
                    return dst
                if dst == bone_name:
                    return src

        if props.use_default_mapping:
            return self.default_mapping(bone_name)

        return None

    def parse_custom_mapping(self, mapping_text):
        """解析自定义映射表"""
        mapping = []
        for line in mapping_text.split('\n'):
            line = line.strip()
            if ':' in line and line.count(':') == 1:
                src, dst = line.split(':', 1)
                mapping.append((src.strip(), dst.strip()))
        return mapping

    def default_mapping(self, bone_name):
        """默认映射算法：基于 .L/.R 或 _left/_right 后缀"""
        patterns = [
            (r'\.L$', '.R'),
            (r'\.R$', '.L'),
            (r'_left$', '_right'),
            (r'_right$', '_left'),
            (r'\.left$', '.right'),
            (r'\.right$', '.left'),
        ]
        for pattern, replacement in patterns:
            if re.search(pattern, bone_name):
                return re.sub(pattern, replacement, bone_name)
        return None

    def flip_transform(self, source_bone, target_bone, props):
        """翻转变换，根据位移、旋转和缩放的 W/X/Y/Z 复选框控制"""
        # 位置翻转
        target_bone.location = source_bone.location.copy()
        if props.location_flip_x:
            target_bone.location[0] = -source_bone.location[0]
        if props.location_flip_y:
            target_bone.location[1] = -source_bone.location[1]
        if props.location_flip_z:
            target_bone.location[2] = -source_bone.location[2]

        # 旋转翻转
        if source_bone.rotation_mode == 'QUATERNION':
            quat = source_bone.rotation_quaternion.copy()
            target_bone.rotation_quaternion = (
                -quat[0] if props.rotation_flip_w else quat[0],
                -quat[1] if props.rotation_flip_x else quat[1],
                -quat[2] if props.rotation_flip_y else quat[2],
                -quat[3] if props.rotation_flip_z else quat[3]
            )
        elif source_bone.rotation_mode == 'AXIS_ANGLE':
            angle, x, y, z = source_bone.rotation_axis_angle
            target_bone.rotation_axis_angle = (
                angle,
                -x if props.rotation_flip_x else x,
                -y if props.rotation_flip_y else y,
                -z if props.rotation_flip_z else z
            )
        else:  # Euler
            euler = source_bone.rotation_euler.copy()
            target_bone.rotation_euler = (
                -euler[0] if props.rotation_flip_x else euler[0],
                -euler[1] if props.rotation_flip_y else euler[1],
                -euler[2] if props.rotation_flip_z else euler[2]
            )

        # 缩放翻转
        target_bone.scale = source_bone.scale.copy()
        if props.scale_flip_x:
            if abs(source_bone.scale[0]) > 0.0001:
                target_bone.scale[0] = 1.0 / source_bone.scale[0]
            else:
                self.report({'WARNING'}, f"{source_bone.name} 的 X 轴缩放为 0，已设置为 1.0")
                target_bone.scale[0] = 1.0
        if props.scale_flip_y:
            if abs(source_bone.scale[1]) > 0.0001:
                target_bone.scale[1] = 1.0 / source_bone.scale[1]
            else:
                self.report({'WARNING'}, f"{source_bone.name} 的 Y 轴缩放为 0，已设置为 1.0")
                target_bone.scale[1] = 1.0
        if props.scale_flip_z:
            if abs(source_bone.scale[2]) > 0.0001:
                target_bone.scale[2] = 1.0 / source_bone.scale[2]
            else:
                self.report({'WARNING'}, f"{source_bone.name} 的 Z 轴缩放为 0，已设置为 1.0")
                target_bone.scale[2] = 1.0

class SK_TOOLS_OT_load_bone_mapping(Operator):
    """加载自定义骨骼映射表文件"""
    bl_idname = "sk_tools.load_bone_mapping"
    bl_label = "加载映射表"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")  # type: ignore
    filter_glob: bpy.props.StringProperty(default="*.txt", options={'HIDDEN'})  # type: ignore

    def execute(self, context):
        props = context.scene.bone_match_props
        try:
            with open(self.filepath, 'r', encoding='utf-8') as file:
                lines = file.readlines()
                valid_lines = []
                for line in lines:
                    line = line.strip()
                    if ':' in line and line.count(':') == 1:
                        valid_lines.append(line)
                    else:
                        self.report({'WARNING'}, f"跳过无效行：{line}")
                props.custom_mapping = '\n'.join(valid_lines)
            self.report({'INFO'}, f"已从 {self.filepath} 加载骨骼映射表")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"加载文件失败：{str(e)}")
            return {'CANCELLED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class SK_TOOLS_OT_save_bone_mapping(Operator):
    """保存自定义骨骼映射表到文件"""
    bl_idname = "sk_tools.save_bone_mapping"
    bl_label = "保存映射表"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")  # type: ignore
    filter_glob: bpy.props.StringProperty(default="*.txt", options={'HIDDEN'})  # type: ignore

    def execute(self, context):
        props = context.scene.bone_match_props
        if not props.custom_mapping:
            self.report({'ERROR'}, "自定义映射表为空，无法保存")
            return {'CANCELLED'}
        try:
            with open(self.filepath, 'w', encoding='utf-8') as file:
                file.write(props.custom_mapping)
            self.report({'INFO'}, f"已将骨骼映射表保存到 {self.filepath}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"保存文件失败：{str(e)}")
            return {'CANCELLED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class SK_TOOLS_OT_export_selected_bones(Operator):
    """导出选中的骨骼名称到文件"""
    bl_idname = "sk_tools.export_selected_bones"
    bl_label = "导出选中骨骼"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")  # type: ignore
    filter_glob: bpy.props.StringProperty(default="*.txt", options={'HIDDEN'})  # type: ignore

    @classmethod
    def poll(cls, context):
        return (context.mode == 'POSE' and context.active_object and
                context.active_object.type == 'ARMATURE' and context.selected_pose_bones)

    def execute(self, context):
        selected_bones = context.selected_pose_bones
        if not selected_bones:
            self.report({'ERROR'}, "未选择任何骨骼")
            return {'CANCELLED'}

        try:
            with open(self.filepath, 'w', encoding='utf-8') as file:
                for bone in selected_bones:
                    file.write(f"{bone.name}\n")
            self.report({'INFO'}, f"已将 {len(selected_bones)} 个骨骼导出到 {self.filepath}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"导出文件失败：{str(e)}")
            return {'CANCELLED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class SK_TOOLS_OT_reset_selected_bones(Operator):
    """重置选定骨骼的变换"""
    bl_idname = "sk_tools.reset_selected_bones"
    bl_label = "重置选定骨骼"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.mode == 'POSE' and context.active_object and
                context.active_object.type == 'ARMATURE' and context.selected_pose_bones)

    def execute(self, context):
        selected_bones = context.selected_pose_bones
        if not selected_bones:
            self.report({'ERROR'}, "未选择任何骨骼")
            return {'CANCELLED'}

        for bone in selected_bones:
            # 重置位置
            bone.location = Vector((0, 0, 0))

            # 重置旋转
            if bone.rotation_mode == 'QUATERNION':
                bone.rotation_quaternion = Quaternion((1, 0, 0, 0))
            elif bone.rotation_mode == 'AXIS_ANGLE':
                bone.rotation_axis_angle = (0, 0, 0, 0)
            else:  # Euler
                bone.rotation_euler = Euler((0, 0, 0))

            # 重置缩放
            bone.scale = Vector((1, 1, 1))

        self.report({'INFO'}, f"已重置 {len(selected_bones)} 个骨骼的变换")
        return {'FINISHED'}

def draw_panel(layout, context):
    """绘制 BoneMatch 面板"""
    props = context.scene.bone_match_props
    box = layout.box()
    box.label(text="骨骼匹配", icon='BONE_DATA')
    
    row = box.row()
    row.prop(props, "use_default_mapping", text="使用默认映射算法")
    row.operator("sk_tools.load_bone_mapping", text="加载映射表", icon='FILEBROWSER')
    
    row = box.row()
    row.label(text="位移控制:")
    row.prop(props, "location_flip_x", text="X")
    row.prop(props, "location_flip_y", text="Y")
    row.prop(props, "location_flip_z", text="Z")
    
    row = box.row()
    row.label(text="旋转控制:")
    row.prop(props, "rotation_flip_w", text="W")
    row.prop(props, "rotation_flip_x", text="X")
    row.prop(props, "rotation_flip_y", text="Y")
    row.prop(props, "rotation_flip_z", text="Z")
    
    row = box.row()
    row.label(text="缩放控制:")
    row.prop(props, "scale_flip_x", text="X")
    row.prop(props, "scale_flip_y", text="Y")
    row.prop(props, "scale_flip_z", text="Z")
    
    box.prop(props, "custom_mapping", text="自定义骨骼映射")
    
    row = box.row()
    row.operator("sk_tools.export_selected_bones", text="导出选中骨骼", icon='FILE_TICK')
    row.operator("sk_tools.save_bone_mapping", text="保存映射表", icon='FILE_TICK')
    
    row = box.row()
    row.operator("sk_tools.bone_match", text="翻转变换")
    row.operator("sk_tools.reset_selected_bones", text="重置选定骨骼", icon='FILE_REFRESH')

def register():
    bpy.utils.register_class(SK_TOOLS_OT_bone_match)
    bpy.utils.register_class(SK_TOOLS_OT_load_bone_mapping)
    bpy.utils.register_class(SK_TOOLS_OT_save_bone_mapping)
    bpy.utils.register_class(SK_TOOLS_OT_export_selected_bones)
    bpy.utils.register_class(SK_TOOLS_OT_reset_selected_bones)
    bpy.utils.register_class(BoneMatchProperties)
    bpy.types.Scene.bone_match_props = bpy.props.PointerProperty(type=BoneMatchProperties)

def unregister():
    bpy.utils.unregister_class(SK_TOOLS_OT_bone_match)
    bpy.utils.unregister_class(SK_TOOLS_OT_load_bone_mapping)
    bpy.utils.unregister_class(SK_TOOLS_OT_save_bone_mapping)
    bpy.utils.unregister_class(SK_TOOLS_OT_export_selected_bones)
    bpy.utils.unregister_class(SK_TOOLS_OT_reset_selected_bones)
    bpy.utils.unregister_class(BoneMatchProperties)
    del bpy.types.Scene.bone_match_props