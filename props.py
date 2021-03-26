import bpy

def alm_pin_poll(self, object):
    return object.type == 'ARMATURE' and object.name in bpy.context.scene.objects

def alm_meta_poll(self, object):
    return object.type == 'ARMATURE' and hasattr(object.data, 'rigify_layers') and len(object.data.rigify_layers) >= 29

class BendifySceneSettings(bpy.types.PropertyGroup):
    alm_pin: bpy.props.PointerProperty(type=bpy.types.Object, name="Pinned Armature Object", poll=alm_pin_poll)
    alm_meta: bpy.props.PointerProperty(type=bpy.types.Object, name="Metarig for Layer Names", poll=alm_meta_poll)
    alm_layers: bpy.props.BoolVectorProperty(name="Visible Armature Layers", size=32)
    alm_empty: bpy.props.BoolProperty(name="Show Empty Armature Layers", default=False)
    alm_compact: bpy.props.BoolProperty(name="Reduce Displayed Properties", default=False)
    alm_mode: bpy.props.EnumProperty(
        name="Armature Layer Manager Mode",
        default='BUTTONS',
        items=(
            ('LAYERS', "Layers", "Layers", 'GRIP', 0),
            ('BUTTONS', "Buttons", "Buttons", 'PRESET', 1),
            ('EDIT', "Edit", "Edit", 'OPTIONS', 2),
            ('PREVIEW', "Preview", "Preview", 'ANCHOR_CENTER', 3)
        )
    )