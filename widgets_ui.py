from bpy.types import Panel


class BendifyWidgetsPanel():
    """General widget tools panel"""
    def draw(self, context):
        layout = self.layout
        col = layout.column()

        row = col.row(align=True)
        row.operator('scene.widgets_names_fix', text="Fix Names", icon='BOLD')
        row.operator('scene.widgets_remove_unused', text="Clean", icon='X')
        col.row().separator()

        if context.mode == 'POSE':
            col.row().operator('pose.widgets_select', icon='VIEW_PAN')
            col.row().operator('pose.widgets_bevel', icon='MOD_BEVEL')
            #transform = col.row().operator('pose.widgets_transform', icon='OBJECT_ORIGIN')
        row = col.row()
        if hasattr(context.scene, '["edit_widgets"]'):
            row.operator('scene.widgets_edit_stop', icon='CANCEL')
        else:
            row.operator('pose.widgets_edit_start', icon='MESH_DATA')


class BENDIFY_PT_BendifyWidgets(Panel, BendifyWidgetsPanel):
    bl_category = "Bendify"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Widgets"
    bl_order = 3
    bl_options = {'DEFAULT_CLOSED'}
