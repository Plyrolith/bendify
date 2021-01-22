import bpy

class BendifyToolsPosePanel():
    """General pose tools panel"""
    def draw(self, context):
        layout = self.layout
        col = layout.column()

        row = col.row(align=True)
        reset_sel = row.operator('pose.stretchto_reset', icon='CON_STRETCHTO')
        reset_sel.selected = True
        reset_all = row.operator('pose.stretchto_reset', text="", icon='CONSTRAINT')
        reset_all.selected = False

        col.row().operator('pose.constraints_mirror', icon='MOD_MIRROR')

        col.row().separator()
        col.row().label(text="Armature Constraints", icon='MOD_ARMATURE')
        row = col.row()
        arma_par = row.operator('pose.constraints_add_armature', text="Convert Parents", icon='TRANSFORM_ORIGINS')
        arma_par.mode = 'PARENT'
        row = layout.row(align=True)
        arma_sel = row.operator('pose.constraints_add_armature', text="To Selected", icon='FULLSCREEN_ENTER')
        arma_sel.mode = 'SELECTED'
        arma_act = row.operator('pose.constraints_add_armature', text="To Active", icon='FULLSCREEN_EXIT')
        arma_act.mode = 'ACTIVE'

class BendifyToolsObjectPanel():
    """General object tools panel"""
    def draw(self, context):
        layout = self.layout
        col = layout.column()

        col.row().operator('object.object_names_normalize', icon='FILE_TEXT')
        col.row().operator('view3d.material_slots_switch', icon='MATERIAL')


class BendifyToolsWeightPaintPanel():
    """Weight paint tools panel"""
    def draw(self, context):
        layout = self.layout
        col = layout.column()

        col.row().operator('object.mirror_all_weights', icon='MOD_MIRROR')

class BENDIFY_PT_BendifyToolsPose(bpy.types.Panel, BendifyToolsPosePanel):
    bl_category = "Bendify"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Bendify Tools"
    bl_order = 2

    @classmethod
    def poll(self, context):
        return context.mode == 'POSE'
    
class BENDIFY_PT_BendifyToolsObject(bpy.types.Panel, BendifyToolsObjectPanel):
    bl_category = "Bendify"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Object Tools"
    bl_order = 6

    @classmethod
    def poll(self, context):
        return context.mode == 'OBJECT'

class BENDIFY_PT_BendifyToolsWeightPaint(bpy.types.Panel, BendifyToolsWeightPaintPanel):
    bl_category = "Bendify"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Weight Tools"
    bl_order = 7

    @classmethod
    def poll(self, context):
        return context.mode == 'PAINT_WEIGHT'