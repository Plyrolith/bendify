import bpy

class BendifySceneSettings(bpy.types.PropertyGroup):
    alm_pin: bpy.props.PointerProperty(type=bpy.types.Object, name="Pinned Armature Object")#, poll=alm_pin_poll)
    alm_meta: bpy.props.PointerProperty(type=bpy.types.Armature, name="Metarig for Layer Names")#, poll=alm_meta_poll)
    alm_layers: bpy.props.BoolVectorProperty(name="Visible Armature Layers", size=32)
    alm_empty: bpy.props.BoolProperty(name="Show Empty Armature Layers", default=False)
    alm_compact: bpy.props.BoolProperty(name="Reduce Displayed Properties", default=False)
    alm_mode: bpy.props.EnumProperty(
        name="Armature Layer Manager Mode",
        default='BUTTONS',
        items=(
            ('BUTTONS', "Buttons", "Buttons"),
            ('EDIT', "Edit", "Edit"),
            ('PREVIEW', "Preview", "Preview")
        )
    )

    def alm_pin_poll(self, object):
        return object.type == 'ARMATURE'

    def alm_meta_poll(self, object):
        return object.type == 'ARMATURE' and getattr(object.data, 'rigify_layers')