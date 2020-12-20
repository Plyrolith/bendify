import bpy

class BendifyWidgetsPanel():
    """General widget tools panel"""
    def draw(self, context):
        layout = self.layout
        col = layout.column()

        col.row().operator('pose.widgets_select', icon='VIEW_PAN')
        col.row().operator('pose.widgets_edit', icon='MESH_DATA')
        col.row().separator()
        row = col.row(align=True)
        row.operator('view3d.widgets_names_fix', icon='BOLD')
        row.operator('view3d.widgets_remove_unused', icon='X')

class BENDIFY_PT_BendifyWidgets(bpy.types.Panel, BendifyWidgetsPanel):
    bl_category = "Bendify"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Widgets"
    bl_order = 3
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(self, context):
        #return context.mode == 'POSE'
        return True