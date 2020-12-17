import bpy

class BendifyToolsPosePanel():
    '''General pose tools panel'''
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
        arma_par = row.operator('pose.constraint_add_armature', text="Convert Parents", icon='TRANSFORM_ORIGINS')
        arma_par.mode = 'PARENT'
        row = layout.row(align=True)
        arma_sel = row.operator('pose.constraint_add_armature', text="To Selected", icon='FULLSCREEN_ENTER')
        arma_sel.mode = 'SELECTED'
        arma_act = row.operator('pose.constraint_add_armature', text="To Active", icon='FULLSCREEN_EXIT')
        arma_act.mode = 'ACTIVE'

class BendifyToolsObjectPanel():
    '''General object tools panel'''
    def draw(self, context):
        layout = self.layout
        col = layout.column()

        col.row().operator('object.object_names_normalize', icon='FILE_TEXT')
        '''
        col.row().separator()
        col.row().operator('view3d.material_slots_link_change', icon='MATERIAL')
        col.row().operator('view3d.widgets_fix_names', icon='MATERIAL')
        col.row().operator('view3d.widgets_delete_unused', icon='MATERIAL')
        '''

class BENDIFY_PT_BendifyToolsPose(bpy.types.Panel, BendifyToolsPosePanel):
    bl_category = "Bendify"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Bendify Tools"
    bl_order = 1

    @classmethod
    def poll(self, context):
        return context.mode == 'POSE'
    
class BENDIFY_PT_BendifyToolsObject(bpy.types.Panel, BendifyToolsObjectPanel):
    bl_category = "Bendify"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Object Tools"
    bl_order = 1

    @classmethod
    def poll(self, context):
        return context.mode == 'OBJECT'