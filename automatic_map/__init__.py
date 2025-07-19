bl_info = {
    "name": "ZMTB Automatic Map",
    "author": "Grok (Integrated for ZMTB)",
    "version": (1, 0, 0),
    "blender": (4, 4, 3),
    "location": "View3D > Sidebar > ZMTB > Automatic Map",
    "description": "A tool to apply diffuse textures to game models based on component numbers and hash values.",
    "category": "中文版",
}

from . import automatic_map

def register():
    automatic_map.register()

def unregister():
    automatic_map.unregister()