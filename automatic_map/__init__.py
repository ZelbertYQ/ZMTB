bl_info = {
    "name": "ZMTB Automatic Map",
    "author": "Grok (Integrated for ZMTB)",
    "version": (1, 0, 0),
    "blender": (4, 4, 3),
    "location": "View3D > Header > ZMTB Test Button",
    "description": "A tool for adding a test button in the 3D View header.",
    "category": "中文版",
}

from . import automatic_map

def register():
    automatic_map.register()

def unregister():
    automatic_map.unregister()