bl_info = {
    "name": "Vertex Group Combiner",
    "author": "SilentNightSound#7430",
    "version": (1, 0),
    "blender": (3, 6, 0),
    "description": "Combines vertex groups with the same prefix into one",
    "category": "Object",
}

import bpy

class VertexGroupCombinerOperator(bpy.types.Operator):
    bl_idname = "sk_tools.combine_vertex_groups"
    bl_label = "合并至指定值"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        vgroup_num = context.scene.vgroup_num
        obj = bpy.context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "没有选中的网格对象。")
            return {'CANCELLED'}
        for num in range(0, vgroup_num + 1):
            relevant = [x.name for x in obj.vertex_groups if x.name.split(".")[0] == f"{num}"]
            vgroup = obj.vertex_groups.new(name=f"x{num}")
            for vert_id, vert in enumerate(obj.data.vertices):
                available_groups = [v_group_elem.group for v_group_elem in vert.groups]
                combined = 0
                for v in relevant:
                    if obj.vertex_groups[v].index in available_groups:
                        combined += obj.vertex_groups[v].weight(vert_id)
                if combined > 0:
                    vgroup.add([vert_id], combined, 'ADD')
            for vg in [x for x in obj.vertex_groups if x.name.split(".")[0] == f"{num}"]:
                obj.vertex_groups.remove(vg)
            for vg in obj.vertex_groups:
                if vg.name[0].lower() == "x":
                    vg.name = vg.name[1:]
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.vertex_group_sort()
        self.report({'INFO'}, f"已合并顶点组至 {vgroup_num}。")
        return {'FINISHED'}

class InOneButtonOperator(bpy.types.Operator):
    bl_idname = "sk_tools.in_one_button"
    bl_label = "合并至最大值"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = bpy.context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "没有选中的网格对象。")
            return {'CANCELLED'}
        
        # Get the highest vertex group index
        if not obj.vertex_groups:
            self.report({'WARNING'}, "选中的对象没有顶点组。")
            return {'CANCELLED'}
        
        # Extract numeric prefixes from vertex group names and find the maximum
        max_num = -1
        for vg in obj.vertex_groups:
            try:
                # Split by "." and take the first part, assuming it’s the numeric prefix
                prefix = vg.name.split(".")[0]
                num = int(prefix)
                max_num = max(max_num, num)
            except (ValueError, IndexError):
                continue  # Skip if the name doesn’t start with a number
        
        if max_num < 0:
            self.report({'WARNING'}, "未找到以数字开头的顶点组。")
            return {'CANCELLED'}
        
        # Update the scene's vgroup_num property
        context.scene.vgroup_num = max_num
        
        # Trigger the Combine Vertex Groups operator
        bpy.ops.sk_tools.combine_vertex_groups()
        
        self.report({'INFO'}, f"已将最大组号设置为 {max_num} 并合并顶点组。")
        return {'FINISHED'}

class SortVertexGroupsOperator(bpy.types.Operator):
    bl_idname = "sk_tools.sort_vertex_groups_vgc"
    bl_label = "排列顶点组"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = bpy.context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "没有选中的网格对象。")
            return {'CANCELLED'}
        if not obj.vertex_groups:
            self.report({'WARNING'}, "选中的对象没有顶点组。")
            return {'CANCELLED'}
        
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.vertex_group_sort()
        self.report({'INFO'}, "顶点组已按名称排序。")
        return {'FINISHED'}

class RemoveUnusedVertexGroupsOperator(bpy.types.Operator):
    bl_idname = "sk_tools.remove_unused_vertex_groups"
    bl_label = "去除未使用顶点组"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = bpy.context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "没有选中的网格对象。")
            return {'CANCELLED'}
        if not obj.vertex_groups:
            self.report({'WARNING'}, "选中的对象没有顶点组。")
            return {'CANCELLED'}
        
        # 遍历所有顶点，记录使用的顶点组索引
        used_groups = set()
        for vert in obj.data.vertices:
            for group_elem in vert.groups:
                if group_elem.weight > 0:  # 只考虑权重大于0的顶点组
                    used_groups.add(group_elem.group)
        
        # 找出并移除未使用的顶点组
        removed_count = 0
        for vg in reversed(obj.vertex_groups[:]):  # 使用副本以避免修改时出错
            if vg.index not in used_groups:
                obj.vertex_groups.remove(vg)
                removed_count += 1
        
        if removed_count > 0:
            self.report({'INFO'}, f"已移除 {removed_count} 个未使用的顶点组。")
        else:
            self.report({'INFO'}, "没有找到未使用的顶点组。")
        return {'FINISHED'}

def draw_panel(layout, context):
    # 第一行：去除未使用顶点组 和 排列顶点组
    row1 = layout.row(align=True)
    row1.operator("sk_tools.remove_unused_vertex_groups", text="去除未使用顶点组")
    row1.operator("sk_tools.sort_vertex_groups_vgc", text="排列顶点组")

    # 第二行：指定顶点组、合并至指定值 和 合并至最大值
    row2 = layout.row(align=True)
    row2.prop(context.scene, "vgroup_num", text="指定顶点组")
    row2.operator("sk_tools.combine_vertex_groups", text="合并至指定值")
    row2.operator("sk_tools.in_one_button", text="合并至最大值")

def register():
    bpy.utils.register_class(VertexGroupCombinerOperator)
    bpy.utils.register_class(InOneButtonOperator)
    bpy.utils.register_class(SortVertexGroupsOperator)
    bpy.utils.register_class(RemoveUnusedVertexGroupsOperator)  # 注册新操作
    # Register the scene property for vgroup_num
    bpy.types.Scene.vgroup_num = bpy.props.IntProperty(
        name="Max Group Number",
        default=255,
        min=0,
        description="Maximum group number to combine"
    )

def unregister():
    bpy.utils.unregister_class(RemoveUnusedVertexGroupsOperator)  # 注销新操作
    bpy.utils.unregister_class(SortVertexGroupsOperator)
    bpy.utils.unregister_class(InOneButtonOperator)
    bpy.utils.unregister_class(VertexGroupCombinerOperator)
    # Remove the scene property
    del bpy.types.Scene.vgroup_num