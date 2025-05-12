# uv_snapshot/uv_snapshot.py
import bpy
import json
from datetime import datetime
from bpy.props import StringProperty, IntProperty, CollectionProperty
from bpy.types import PropertyGroup, Operator, Panel, AddonPreferences

# Properties
class UVSnapshot(PropertyGroup):
    name: StringProperty(name="UV Snapshot Name")
    data: StringProperty(name="UV Snapshot Data")
    index: IntProperty()

# Operators
class UVS_OT_CreateSnapshot(Operator):
    bl_idname = "uvs.create_snapshot"
    bl_label = "创建UV快照"
    bl_description = "Capture current UV map states"

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != 'MESH' or not obj.data.uv_layers:
            self.report({'ERROR'}, "需要一个带有UV贴图的网格对象")
            return {'CANCELLED'}

        snapshots = obj.uv_snapshots
        
        # 生成时间戳名称
        now = datetime.now()
        base_name = now.strftime("%H_%M_%m_%d")
        
        # 处理重复名称
        index = 1
        final_name = base_name
        while final_name in [s.name for s in snapshots]:
            final_name = f"{base_name}_{index:02d}"
            index += 1

        # 收集UV数据
        snapshot_data = {}
        for uv_layer in obj.data.uv_layers:
            uv_data = {}
            for loop in obj.data.loops:
                uv = uv_layer.data[loop.index].uv
                uv_data[str(loop.index)] = [uv.x, uv.y]
            snapshot_data[uv_layer.name] = uv_data

        # 创建快照
        snapshot = snapshots.add()
        snapshot.name = final_name
        snapshot.data = json.dumps(snapshot_data)
        obj.active_uv_snapshot_index = len(snapshots) - 1
        
        self.report({'INFO'}, f"UV快照 {snapshot.name} 已创建")
        return {'FINISHED'}

class UVS_OT_ApplySnapshot(Operator):
    bl_idname = "uvs.apply_snapshot"
    bl_label = "应用UV快照"
    bl_description = "Restore selected UV snapshot"

    @classmethod
    def poll(cls, context):
        # 仅检查对象是否存在并有快照，无需限制模式
        return context.object and context.object.uv_snapshots and context.object.type == 'MESH'

    def execute(self, context):
        obj = context.object
        snapshots = obj.uv_snapshots
        if not snapshots:
            self.report({'ERROR'}, "没有可用的UV快照")
            return {'CANCELLED'}
        
        try:
            snapshot = snapshots[obj.active_uv_snapshot_index]
            data = json.loads(snapshot.data)
        except (IndexError, KeyError):
            self.report({'ERROR'}, "无效的UV快照")
            return {'CANCELLED'}

        # 保存当前模式并切换到对象模式以修改 UV 层结构
        current_mode = obj.mode
        if current_mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        # 清除旧UV层
        while obj.data.uv_layers:
            obj.data.uv_layers.remove(obj.data.uv_layers[0])

        # 重建UV层
        for uv_name in data:
            new_uv = obj.data.uv_layers.new(name=uv_name)
            uv_data = data[uv_name]
            for loop_index, uv_coords in uv_data.items():
                new_uv.data[int(loop_index)].uv = (float(uv_coords[0]), float(uv_coords[1]))

        # 恢复原始模式
        if current_mode != 'OBJECT':
            bpy.ops.object.mode_set(mode=current_mode)

        self.report({'INFO'}, f"已应用UV快照: {snapshot.name}")
        return {'FINISHED'}

class UVS_OT_DeleteSnapshot(Operator):
    bl_idname = "uvs.delete_snapshot"
    bl_label = "删除UV快照"
    bl_description = "Remove selected UV snapshot"

    @classmethod
    def poll(cls, context):
        return context.object and context.object.uv_snapshots

    def execute(self, context):
        obj = context.object
        snapshots = obj.uv_snapshots
        index = obj.active_uv_snapshot_index
        
        if index < 0 or index >= len(snapshots):
            self.report({'ERROR'}, "无效的索引")
            return {'CANCELLED'}
        
        snapshots.remove(index)
        obj.active_uv_snapshot_index = min(index, len(snapshots)-1)
        self.report({'INFO'}, "UV快照已删除")
        return {'FINISHED'}

# Panel drawing function for integration
def draw_panel(layout, context):
    obj = context.object
    if not obj or obj.type != 'MESH':
        layout.label(text="请选择一个网格对象")
        return

    snapshots = obj.uv_snapshots

    # 创建按钮
    layout.operator("uvs.create_snapshot", icon='FILE_NEW')

    # UV快照列表
    if snapshots:
        layout.template_list(
            "UI_UL_list",
            "uv_snapshots",
            obj,
            "uv_snapshots",
            obj,
            "active_uv_snapshot_index",
            rows=4
        )

        # 操作按钮
        row = layout.row(align=True)
        row.operator("uvs.apply_snapshot", icon='FILE_REFRESH')
        row.operator("uvs.delete_snapshot", icon='TRASH')
    else:
        layout.label(text="暂无UV快照")

# Registration
def register():
    bpy.utils.register_class(UVSnapshot)
    bpy.types.Object.uv_snapshots = CollectionProperty(
        type=UVSnapshot
    )
    bpy.types.Object.active_uv_snapshot_index = IntProperty(
        name="Active UV Snapshot Index",
        default=0
    )
    bpy.utils.register_class(UVS_OT_CreateSnapshot)
    bpy.utils.register_class(UVS_OT_ApplySnapshot)
    bpy.utils.register_class(UVS_OT_DeleteSnapshot)

def unregister():
    bpy.utils.unregister_class(UVSnapshot)
    del bpy.types.Object.uv_snapshots
    del bpy.types.Object.active_uv_snapshot_index
    bpy.utils.unregister_class(UVS_OT_CreateSnapshot)
    bpy.utils.unregister_class(UVS_OT_ApplySnapshot)
    bpy.utils.unregister_class(UVS_OT_DeleteSnapshot)