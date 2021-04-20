import bpy
from bpy.props import *
from bpy.types import Object, PropertyGroup


def alm_pin_poll(self, obj):
    return obj.type == 'ARMATURE' and obj.name in bpy.context.scene.objects

def alm_meta_poll(self, obj):
    return obj.type == 'ARMATURE' and hasattr(obj.data, 'rigify_layers') and len(obj.data.rigify_layers) >= 29

class BendifySceneSettings(PropertyGroup):
    alm_pin: PointerProperty(type=Object, name="Pinned Armature Object", poll=alm_pin_poll)
    alm_meta: PointerProperty(type=Object, name="Metarig for Layer Names", poll=alm_meta_poll)
    alm_layers: BoolVectorProperty(name="Visible Armature Layers", size=32)
    alm_empty: BoolProperty(name="Show Empty Armature Layers", default=False)
    alm_compact: BoolProperty(name="Reduce Displayed Properties", default=False)
    alm_mode: EnumProperty(
        name="Armature Layer Manager Mode",
        default='BUTTONS',
        items=(
            ('LAYERS', "Layers", "Layers", 'GRIP', 0),
            ('BUTTONS', "Buttons", "Buttons", 'PRESET', 1),
            ('EDIT', "Edit", "Edit", 'OPTIONS', 2),
            ('PREVIEW', "Preview", "Preview", 'ANCHOR_CENTER', 3)
        )
    )

offset_axes = (
        ('NONE', "None", "None"),
        ('SCALE_X', "X", "X"),
        ('SCALE_Y', "Y", "Y"),
        ('SCALE_Z', "Z", "Z")
    )

class ArmaConstraintTargets(PropertyGroup):
    props_options = {'LIBRARY_EDITABLE'}
    name: StringProperty(name="Bone Name", default="")

    weight: FloatProperty(
        name="Weight",
        default=0.0,
        min=0.0,
        max=1.0,
        description="Constraint Weight",
        options=props_options
    )

    scale_offset: BoolProperty(
        name="Offset Scale",
        default=False,
        description="Get scale offset from this parent",
        options=props_options
    )

    scale_source_x: EnumProperty(
        items=offset_axes,
        name="X Source Axis",
        default='SCALE_X',
        description="Source axis for X scale offset",
        options=props_options
    )

    scale_source_y: EnumProperty(
        items=offset_axes,
        name="Y Source Axis",
        default='SCALE_Y',
        description="Source axis for Y scale offset",
        options=props_options
    )

    scale_source_z: EnumProperty(
        items=offset_axes,
        name="Z Source Axis",
        default='SCALE_Z',
        description="Source axis for Z scale offset",
        options=props_options
    )
