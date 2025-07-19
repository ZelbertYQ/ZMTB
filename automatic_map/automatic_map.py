import bpy
import os
import re
from bpy.types import Operator, PropertyGroup
from bpy.props import StringProperty, PointerProperty
import random
from PIL import Image

class ZMTB_AutomaticMapProperties(PropertyGroup):
    collection: PointerProperty(
        name="模型集合",
        description="选择用于存放模型的集合",
        type=bpy.types.Collection
    )
    dump_dir: StringProperty(
        name="转储目录",
        description="选择包含贴图的转储目录，或点击下方按钮从 WWMI 的 Object Sources 获取",
        default="",
        subtype='DIR_PATH'
    )
    frame_dir: StringProperty(
        name="帧分析目录",
        description="选择帧分析目录（包含 deduped 子目录）以判断漫反射贴图，或点击下方按钮从 WWMI 的 Frame Dump 获取",
        default="",
        subtype='DIR_PATH'
    )

class ZMTB_OT_UpdateDirectoriesFromWWMI(Operator):
    bl_idname = "zmtb.update_directories_from_wwmi"
    bl_label = "从 WWMI 获取目录"
    bl_description = "从 WWMI 插件获取 Object Sources 和 Frame Dump 目录（自动附加 deduped 子目录）"

    def execute(self, context):
        props = context.scene.zmtb_automatic_map
        if "WWMI-Tools" not in context.preferences.addons:
            self.report({'ERROR'}, "WWMI-Tools 未安装或未启用")
            return {'CANCELLED'}

        wwmi_settings = context.scene.wwmi_tools_settings
        if not hasattr(wwmi_settings, 'object_source_folder') or not hasattr(wwmi_settings, 'frame_dump_folder'):
            self.report({'ERROR'}, "无法访问 WWMI-Tools 设置，请确认 WWMI 插件已正确加载")
            return {'CANCELLED'}

        if wwmi_settings.object_source_folder and os.path.exists(wwmi_settings.object_source_folder):
            props.dump_dir = wwmi_settings.object_source_folder
            print(f"Updated dump_dir to: {props.dump_dir}")
        else:
            self.report({'WARNING'}, "WWMI 的 Object Sources 未设置或目录不存在")

        if wwmi_settings.frame_dump_folder and os.path.exists(wwmi_settings.frame_dump_folder):
            deduped_path = os.path.join(wwmi_settings.frame_dump_folder, "deduped")
            if os.path.exists(deduped_path):
                props.frame_dir = deduped_path
                print(f"Updated frame_dir to: {props.frame_dir}")
            else:
                self.report({'WARNING'}, f"Frame Dump 的 deduped 目录不存在: {deduped_path}")
        else:
            self.report({'WARNING'}, "WWMI 的 Frame Dump 未设置或目录不存在")

        if props.dump_dir or props.frame_dir:
            self.report({'INFO'}, "已尝试从 WWMI 获取目录，请检查转储目录和帧分析目录")
        else:
            self.report({'WARNING'}, "未找到有效的 WWMI 目录设置")

        return {'FINISHED'}

class ZMTB_OT_ApplyDiffuseTextures(Operator):
    bl_idname = "zmtb.apply_diffuse_textures"
    bl_label = "应用漫反射贴图"
    bl_description = "根据模型编号和贴图 hash 值应用漫反射贴图"

    def execute(self, context):
        props = context.scene.zmtb_automatic_map
        collection = props.collection
        dump_dir = props.dump_dir
        frame_dir = props.frame_dir

        if not collection or not dump_dir or not frame_dir:
            self.report({'ERROR'}, "请设置模型集合、转储目录和帧分析目录！")
            return {'CANCELLED'}

        if not os.path.exists(dump_dir):
            self.report({'ERROR'}, f"转储目录不存在: {dump_dir}")
            return {'CANCELLED'}
        if not os.path.exists(frame_dir):
            self.report({'ERROR'}, f"帧分析目录不存在: {frame_dir}")
            return {'CANCELLED'}

        model_numbers = {}
        for obj in collection.objects:
            match = re.match(r"Component\s+(\d+)(?:\.\d+)?", obj.name)
            if match:
                number = int(match.group(1))
                model_numbers[obj] = number
            else:
                print(f"Skipping object with invalid name: {obj.name}")

        if not model_numbers:
            self.report({'ERROR'}, "集合中未找到符合 'Component N' 格式的模型！")
            return {'CANCELLED'}

        # 每次重新扫描目录
        try:
            texture_files = [f for f in os.listdir(dump_dir) if f.endswith('.dds')]
            texture_files.sort(key=lambda x: len(re.findall(r'\d+', x)))
        except Exception as e:
            self.report({'ERROR'}, f"无法访问转储目录 {dump_dir}: {str(e)}")
            return {'CANCELLED'}

        single_number_textures = {}
        multi_number_textures = {}
        for texture in texture_files:
            match = re.match(r"Components-([\d-]+)\s+t=([0-9a-fA-F]+)\.dds", texture)
            if match:
                number_str = match.group(1)
                hash_value = match.group(2)
                numbers = [int(n) for n in number_str.split('-') if n]
                print(f"Processing texture: {texture}, numbers: {numbers}, hash: {hash_value}")
                if len(numbers) == 1:
                    number = numbers[0]
                    if self.is_diffuse_texture(hash_value, frame_dir):
                        file_path = os.path.join(dump_dir, texture)
                        size = self.get_texture_size(file_path)
                        if size and max(size) > 512:
                            if number not in single_number_textures:
                                single_number_textures[number] = []
                            single_number_textures[number].append((hash_value, file_path, size))
                            print(f"Added single-number texture for {number}: {texture}")
                        else:
                            if number not in single_number_textures:
                                single_number_textures[number] = []
                            single_number_textures[number].append((hash_value, file_path, None))
                            print(f"Added single-number texture for {number}: {texture} (size unavailable)")
                    else:
                        print(f"Texture {texture} is not diffuse (no SRGB)")
                else:
                    if self.is_diffuse_texture(hash_value, frame_dir):
                        file_path = os.path.join(dump_dir, texture)
                        size = self.get_texture_size(file_path)
                        if size and max(size) > 512:
                            for number in numbers:
                                if number not in multi_number_textures:
                                    multi_number_textures[number] = []
                                multi_number_textures[number].append((hash_value, file_path, size))
                                print(f"Added multi-number texture for {number}: {texture}")
                        else:
                            for number in numbers:
                                if number not in multi_number_textures:
                                    multi_number_textures[number] = []
                                multi_number_textures[number].append((hash_value, file_path, None))
                                print(f"Added multi-number texture for {number}: {texture} (size unavailable)")
                    else:
                        print(f"Texture {texture} is not diffuse (no SRGB)")
            else:
                print(f"Skipping invalid texture file: {texture}")

        selected_textures = {}
        for number in model_numbers.values():
            # 优先使用单编号贴图
            if number in single_number_textures and single_number_textures[number]:
                textures = single_number_textures[number]
                valid_textures = [t for t in textures if t[2] is not None]
                if valid_textures:
                    max_size = max(max(t[2]) for t in valid_textures)
                    max_textures = [t for t in valid_textures if max(t[2]) == max_size]
                    selected = random.choice(max_textures)
                    selected_textures[number] = (selected[0], selected[1])
                    print(f"Selected single-number texture for {number}: {selected[1]}")
                else:
                    # 如果所有单编号贴图大小不可用，选择第一个
                    selected = single_number_textures[number][0]
                    selected_textures[number] = (selected[0], selected[1])
                    print(f"Selected single-number texture for {number}: {selected[1]} (size unavailable)")
            # 仅在无单编号贴图时使用多编号贴图
            elif number in multi_number_textures and multi_number_textures[number]:
                textures = multi_number_textures[number]
                valid_textures = [t for t in textures if t[2] is not None]
                if valid_textures:
                    max_size = max(max(t[2]) for t in valid_textures)
                    max_textures = [t for t in valid_textures if max(t[2]) == max_size]
                    selected = random.choice(max_textures)
                    selected_textures[number] = (selected[0], selected[1])
                    print(f"Selected multi-number texture for {number}: {selected[1]} (no single-number available)")
                else:
                    # 如果所有多编号贴图大小不可用，选择第一个
                    selected = multi_number_textures[number][0]
                    selected_textures[number] = (selected[0], selected[1])
                    print(f"Selected multi-number texture for {number}: {selected[1]} (size unavailable, no single-number available)")
            else:
                print(f"No suitable texture found for {number}")

        for obj, number in model_numbers.items():
            if number in selected_textures:
                hash_value, file_path = selected_textures[number]
                material_name = f"{hash_value}-C{number}"
                material = bpy.data.materials.get(material_name)
                if not material:
                    material = bpy.data.materials.new(name=material_name)
                    material.use_nodes = True
                    nodes = material.node_tree.nodes
                    links = material.node_tree.links

                    nodes.clear()
                    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
                    bsdf.location = (0, 0)
                    output = nodes.new(type='ShaderNodeOutputMaterial')
                    output.location = (400, 0)
                    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

                    tex_image = nodes.new(type='ShaderNodeTexImage')
                    tex_image.location = (-400, 0)
                    try:
                        tex_image.image = bpy.data.images.load(file_path)
                        tex_image.image.colorspace_settings.name = 'sRGB'
                        tex_image.image.alpha_mode = 'NONE'
                    except Exception as e:
                        self.report({'ERROR'}, f"无法加载贴图 {file_path}: {str(e)}")
                        continue
                    links.new(tex_image.outputs['Color'], bsdf.inputs['Base Color'])

                if obj.data.materials:
                    obj.data.materials[0] = material
                else:
                    obj.data.materials.append(material)
                print(f"Applied material {material_name} to object {obj.name}")

        self.report({'INFO'}, "漫反射贴图应用完成！")
        return {'FINISHED'}

    def is_diffuse_texture(self, hash_value, frame_dir):
        matched_files = []
        try:
            for file in os.listdir(frame_dir):
                if hash_value in file:
                    matched_files.append(file)
                    if 'SRGB' in file.upper():
                        print(f"Diffuse texture found for hash {hash_value}: {file}")
                        return True
            print(f"Files matched for hash {hash_value}: {matched_files if matched_files else 'None'}")
            print(f"No diffuse texture for hash {hash_value} (no SRGB found)")
            return False
        except Exception as e:
            print(f"Error accessing frame_dir {frame_dir}: {str(e)}")
            return False

    def get_texture_size(self, file_path):
        try:
            with Image.open(file_path) as img:
                print(f"Texture {file_path}: size {img.size}")
                return img.size
        except Exception as e:
            print(f"Failed to read {file_path}: {str(e)}")
            return None

class ZMTB_OT_OneClickShade(Operator):
    bl_idname = "zmtb.one_click_shade"
    bl_label = "一键着色"
    bl_description = "自动选择当前选中集合并执行获取目录和应用漫反射贴图"

    def execute(self, context):
        props = context.scene.zmtb_automatic_map
        active_obj = context.view_layer.objects.active

        if not active_obj or not active_obj.users_collection:
            self.report({'ERROR'}, "请在出线视图中选择一个对象或集合！")
            return {'CANCELLED'}

        collection = active_obj.users_collection[0]
        props.collection = collection
        print(f"Selected collection: {collection.name}")

        bpy.ops.zmtb.update_directories_from_wwmi()
        if not props.dump_dir or not props.frame_dir:
            self.report({'WARNING'}, "目录获取失败，请检查 WWMI 设置！")
            return {'CANCELLED'}

        bpy.ops.zmtb.apply_diffuse_textures()
        return {'FINISHED'}

def register():
    bpy.utils.register_class(ZMTB_AutomaticMapProperties)
    bpy.utils.register_class(ZMTB_OT_UpdateDirectoriesFromWWMI)
    bpy.utils.register_class(ZMTB_OT_ApplyDiffuseTextures)
    bpy.utils.register_class(ZMTB_OT_OneClickShade)
    bpy.types.Scene.zmtb_automatic_map = PointerProperty(type=ZMTB_AutomaticMapProperties)

def unregister():
    bpy.utils.unregister_class(ZMTB_AutomaticMapProperties)
    bpy.utils.unregister_class(ZMTB_OT_UpdateDirectoriesFromWWMI)
    bpy.utils.unregister_class(ZMTB_OT_ApplyDiffuseTextures)
    bpy.utils.unregister_class(ZMTB_OT_OneClickShade)
    del bpy.types.Scene.zmtb_automatic_map