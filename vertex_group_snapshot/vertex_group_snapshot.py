# vertex_group_snapshot/vertex_group_snapshot.py
import bpy
import json
from datetime import datetime
from bpy.props import StringProperty, IntProperty, CollectionProperty
from bpy.types import PropertyGroup, Operator, Panel, AddonPreferences

# Properties
class VertexGroupSnapshot(PropertyGroup):
    name: StringProperty(name="Snapshot Name")
    data: StringProperty(name="Snapshot Data")
    index: IntProperty()

# Operators
class VGS_OT_CreateSnapshot(Operator):
    bl_idname = "vgs.create_snapshot"
    bl_label = "创建快照"
    bl_description = "Capture current vertex group states"

    def execute(self, context):
        obj = context.object
        snapshots = obj.vertex_group_snapshots
        
        # 生成时间戳名称
        now = datetime.now()
        base_name = now.strftime("%H_%M_%m_%d")
        
        # 处理重复名称
        index = 1
        final_name = base_name
        while final_name in [s.name for s in snapshots]:
            final_name = f"{base_name}_{index:02d}"
            index += 1

        # 收集数据
        snapshot_data = {}
        for vg in obj.vertex_groups:
            group_data = {}
            for v in obj.data.vertices:
                try:
                    weight = vg.weight(v.index)
                except RuntimeError:
                    weight = 0
                group_data[str(v.index)] = weight
            snapshot_data[vg.name] = group_data

        # 创建快照
        snapshot = snapshots.add()
        snapshot.name = final_name
        snapshot.data = json.dumps(snapshot_data)
        obj.active_snapshot_index = len(snapshots) - 1
        
        self.report({'INFO'}, f"快照 {snapshot.name} 已创建")
        return {'FINISHED'}

class VGS_OT_ApplySnapshot(Operator):
    bl_idname = "vgs.apply_snapshot"
    bl_label = "应用快照"
    bl_description = "Restore selected snapshot"

    @classmethod
    def poll(cls, context):
        return context.object and context.object.vertex_group_snapshots

    def execute(self, context):
        obj = context.object
        snapshots = obj.vertex_group_snapshots
        if not snapshots:
            self.report({'ERROR'}, "没有可用的快照")
            return {'CANCELLED'}
        
        try:
            snapshot = snapshots[obj.active_snapshot_index]
            data = json.loads(snapshot.data)
        except (IndexError, KeyError):
            self.report({'ERROR'}, "无效的快照")
            return {'CANCELLED'}

        # 清除旧顶点组
        for vg in obj.vertex_groups:
            obj.vertex_groups.remove(vg)

        # 重建顶点组
        for vg_name in data:
            new_vg = obj.vertex_groups.new(name=vg_name)
            group_data = data[vg_name]
            for v_index, weight in group_data.items():
                if float(weight) > 0:
                    new_vg.add([int(v_index)], float(weight), 'REPLACE')

        self.report({'INFO'}, f"已应用快照: {snapshot.name}")
        return {'FINISHED'}

class VGS_OT_DeleteSnapshot(Operator):
    bl_idname = "vgs.delete_snapshot"
    bl_label = "删除快照"
    bl_description = "Remove selected snapshot"

    @classmethod
    def poll(cls, context):
        return context.object and context.object.vertex_group_snapshots

    def execute(self, context):
        obj = context.object
        snapshots = obj.vertex_group_snapshots
        index = obj.active_snapshot_index
        
        if index < 0 or index >= len(snapshots):
            self.report({'ERROR'}, "无效的索引")
            return {'CANCELLED'}
        
        snapshots.remove(index)
        obj.active_snapshot_index = min(index, len(snapshots)-1)
        self.report({'INFO'}, "快照已删除")
        return {'FINISHED'}

# Panel drawing function for integration
def draw_panel(layout, context):
    obj = context.object
    if not obj or obj.type != 'MESH':
        layout.label(text="请选择一个网格对象")
        return

    snapshots = obj.vertex_group_snapshots

    # 创建按钮
    layout.operator("vgs.create_snapshot", icon='FILE_NEW')

    # 快照列表
    if snapshots:
        layout.template_list(
            "UI_UL_list",
            "vertex_group_snapshots",
            obj,
            "vertex_group_snapshots",
            obj,
            "active_snapshot_index",
            rows=4
        )

        # 操作按钮
        row = layout.row(align=True)
        row.operator("vgs.apply_snapshot", icon='FILE_REFRESH')
        row.operator("vgs.delete_snapshot", icon='TRASH')
    else:
        layout.label(text="暂无快照")

# Registration
def register():
    bpy.utils.register_class(VertexGroupSnapshot)
    bpy.types.Object.vertex_group_snapshots = CollectionProperty(
        type=VertexGroupSnapshot
    )
    bpy.types.Object.active_snapshot_index = IntProperty(
        name="Active Snapshot Index",
        default=0
    )
    bpy.utils.register_class(VGS_OT_CreateSnapshot)
    bpy.utils.register_class(VGS_OT_ApplySnapshot)
    bpy.utils.register_class(VGS_OT_DeleteSnapshot)

def unregister():
    bpy.utils.unregister_class(VertexGroupSnapshot)
    del bpy.types.Object.vertex_group_snapshots
    del bpy.types.Object.active_snapshot_index
    bpy.utils.unregister_class(VGS_OT_CreateSnapshot)
    bpy.utils.unregister_class(VGS_OT_ApplySnapshot)
    bpy.utils.unregister_class(VGS_OT_DeleteSnapshot)