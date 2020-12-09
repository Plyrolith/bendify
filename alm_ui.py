import bpy
from .alm_ops import AlmMixIn

class ArmatureLayerManagerPanel(AlmMixIn):
    """Armature Layer Panel drawing class"""    

    def pins(self, context):
        bendify = self.bendify(context)
        arma_single = self.arma_single(context)
        meta_single = self.meta_single(context)

        layout = self.layout

        # Potential two column layout
        if not arma_single and not meta_single:
            canvas = layout.split()
        else:
            canvas = layout
        
        if not arma_single:
            arma_heading = "Pinned Armature" if bendify.alm_pin or not self.arma(context) else "Active: " + self.arma(context).name
            col = canvas.column(heading=arma_heading)
            col.row().prop(
                bendify,
                'alm_pin',
                text="",
                icon='PINNED' if bendify.alm_pin else 'UNPINNED',
            )
        
        if not meta_single:
            meta_heading = "Pinned Metarig" if bendify.alm_pin or not self.meta(context) else "Names: " + self.meta(context).name
            col = canvas.column(heading=meta_heading)
            col.row().prop(
                bendify,
                'alm_meta',
                text="",
                icon='PINNED' if bendify.alm_meta else 'UNPINNED',
            )

    def layers(self, context):
        bendify = self.bendify(context)
        obj = self.arma(context)
        data = obj.data

        # Show empty layers
        if bendify.alm_empty:
            return [i for i in range(32)]
        
        # Show only layers containing bones
        else:
            layers = []
            # Edit bones for edit mode
            if context.mode == 'EDIT_ARMATURE':
                bones = data.edit_bones
            # Regular bones otherwise
            else:
                bones = data.bones
            for bone in bones:
                for i, layer in enumerate(bone.layers):
                    if layer and i not in layers:
                        layers.append(i)
            layers.sort()
            return layers

    def settings(self, context):
        bendify = self.bendify(context)
        obj = self.arma(context)
        data = obj.data

        # Display options
        layout = self.layout
        row = layout.row()
        row.prop(data, 'pose_position', expand=True)
        row.prop(data, 'display_type', text="")
        row.prop(data, 'show_axes', text="", icon='EMPTY_AXIS',expand=True)
        row.prop(obj, 'show_in_front', text="", icon='XRAY', expand=True)

        # Toggle all armatures
        row = layout.row(align=True)
        vl = 0
        for i in range(32):
            if data.layers[i] == True:
                vl += 1
        row.operator(
            'view3d.armature_layer_manager_toggle',
            text="Show Last" if vl == 32 else "Show All",
            icon='SNAP_FACE' if vl == 32 else 'SNAP_VERTEX'
        )

        """
        # Show layer list
        row.prop(
            plyrig,
            'armature_layers_list',
            text="",
            icon='TRIA_UP' if plyrig.armature_layers_list else 'TRIA_DOWN',
            expand=True
        )

        # Show standard grid instead of list
        else:
            row = layout.row(align=True)
            row.prop(data, 'layers', text="")

        """

        split = layout.split(factor=0.6)
        row = split.row()
        # Mode selector
        row.prop(
            bendify,
            'alm_mode',
            expand=True
        )
        
        if not bendify.alm_mode == 'PREVIEW':
            row = split.row()
            # Empty layers
            row.prop(
                bendify,
                'alm_empty',
                text="Empty",
                #icon='GHOST_ENABLED' if bendify.alm_empty else 'GHOST_DISABLED',
                #expand=True
            )

            row.prop(
                bendify,
                'alm_compact',
                text="Compact",
                #icon='COLLAPSEMENU' if bendify.alm_compact else 'ALIGN_JUSTIFY',
                #expand=True
            )

    def buttons(self, context):       
        bendify = self.bendify(context)

        obj = self.arma(context)
        meta = self.meta(context)
        data = obj.data

        layout = self.layout

        # Create the layer rows
        box = layout.box()
        col = box.column()
        for i in self.layers(context):  
            
            # Check for edit bones in this layer               
            if context.mode == 'EDIT_ARMATURE':
                if context.active_bone and context.active_bone.layers[i]:
                    layer_icon = 'RADIOBUT_ON'
                    empty = False
                elif any(b.layers[i] for b in context.selected_editable_bones):
                    layer_icon = 'LAYER_ACTIVE'
                    empty = False
                elif any(b.layers[i] for b in data.edit_bones):
                    layer_icon = 'LAYER_USED'
                    empty = False
                else:
                    layer_icon = 'BLANK1'
                    empty = True
            
            # Same for regular bones in other modes
            else:
                if context.active_pose_bone and data.bones[context.active_pose_bone.name].layers[i]:
                    layer_icon = 'RADIOBUT_ON'
                    empty = False
                elif context.mode == 'POSE' and any(data.bones[b.name].layers[i] for b in context.selected_pose_bones):
                    layer_icon = 'LAYER_ACTIVE'
                    empty = False
                elif any(data.bones[b.name].layers[i] for b in obj.pose.bones):
                    layer_icon = 'LAYER_USED'
                    empty = False
                else:
                    layer_icon = 'BLANK1'
                    empty = True
            
            # Use for rigify layer names or layer number
            if meta and meta.rigify_layers:
                if i < 29:
                    layer_name = meta.rigify_layers[i].name
                elif i == 29:
                    layer_name = "DEF"
                elif i == 30:
                    layer_name = "MCH"
                elif i == 31:
                    layer_name = "ORG"
            else:
                mode = 2
                layer_name = "Layer " + str(i + 1).zfill(2)
            
            # Start the row
            row = col.row(align=True)

            # Selection buttons
            # New selection
            select = row.operator('view3d.armature_layer_manager_select', text="", icon='BLANK1' if empty else 'SELECT_SET')
            select.layer = i
            select.new = False if empty else True # Make sure this won't act as a deselect button for empty layers
            select.select = True

            if not bendify.alm_compact:
                # Add to selection
                extend = row.operator('view3d.armature_layer_manager_select', text="", icon='BLANK1' if empty else 'SELECT_EXTEND')
                extend.layer = i
                extend.new = False
                extend.select = True
                # Subtract from selection
                subtract = row.operator('view3d.armature_layer_manager_select', text="", icon='BLANK1' if empty else 'SELECT_SUBTRACT')
                subtract.layer = i
                subtract.new = False
                subtract.select = False

            # Layer Name
            row.prop(data, 'layers', index=i, text=layer_name, toggle=True, icon=layer_icon)

            if not bendify.alm_compact:
                # Solo
                solo = row.operator('view3d.armature_layer_manager_solo', text="", icon='EVENT_S')
                solo.layer = i

            # Move to layer
            move = row.operator('view3d.armature_layer_manager_add', text="", icon='TRANSFORM_ORIGINS')
            move.layer = i
            move.move = True

            if not bendify.alm_compact:
                # Add to layer
                add = row.operator('view3d.armature_layer_manager_add', text="", icon='PLUS')
                add.layer = i
                add.move = False

                # Lock button
                unlocked = 0
                locked = 0
                for bone in data.bones:
                    if bone.layers[i]:
                        if bone.hide_select:
                            locked += 1
                        else:
                            unlocked += 1
                if unlocked + locked > 0:
                    if not locked:
                        lock_icon = 'UNLOCKED'
                    elif not unlocked:
                        lock_icon = 'LOCKED'
                    else:
                        lock_icon = 'IMAGE_ALPHA'
                else:
                    lock_icon = 'BLANK1'
                lock = row.operator('view3d.armature_layer_manager_lock', text="", icon=lock_icon)
                lock.layer = i
    
    def edit(self, context):
        bendify = self.bendify(context)

        layout = self.layout
        obj = self.arma(context)
        arm = self.meta(context)

        # Ensure that the layers exist
        if 0:
            for i in range(1 + len(arm.rigify_layers), 29):
                arm.rigify_layers.add()
        else:
            # Can't add while drawing, just use button
            if len(arm.rigify_layers) < 29:
                layout.operator("pose.rigify_layer_init")
                return

        # UI
        col = layout.box().column()
        reserved_names = {29: 'DEF', 30: 'MCH', 31: 'ORG'}
        for i in self.layers(context):
            entry = col.row(align=True)
            if not bendify.alm_compact:
                split = entry.row().split(factor=0.05)
                split.label(text=str(i + 1))
                split = split.split(factor=0.5, align=True)
                entry = split.row(align=True)
            icon = 'RESTRICT_VIEW_OFF' if obj.data.layers[i] else 'RESTRICT_VIEW_ON'
            entry.prop(obj.data, "layers", index=i, text="", toggle=True, icon=icon)
            if i in reserved_names:
                entry.label(text=reserved_names[i])
            else:
                rigify_layer = arm.rigify_layers[i]
                entry.prop(rigify_layer, "name", text="")
                if not bendify.alm_compact:
                    extra = split.row(align=True)
                    extra.prop(rigify_layer, "row", text="UI")
                    extra.enabled = False if i == 28 else True
                    icon = 'RADIOBUT_ON' if rigify_layer.selset else 'RADIOBUT_OFF'
                    extra.prop(rigify_layer, "selset", text="", toggle=True, icon=icon)
                    if rigify_layer.group == 0:
                        group_text='None'
                    else:
                        group_text=arm.rigify_colors[rigify_layer.group-1].name
                    extra.prop(rigify_layer, "group", text=group_text)

    def draw(self, context):
        bendify = self.bendify(context)
        self.pins(context)
        if self.arma(context):
            self.settings(context)
            if bendify.alm_mode == "BUTTONS":
                self.buttons(context)
            elif bendify.alm_mode == "EDIT":
                self.edit(context)
            elif bendify.alm_mode == "PREVIEW":
                pass


class BENDIFY_PT_ArmatureLayerManagerViewport(bpy.types.Panel, ArmatureLayerManagerPanel):
    bl_category = "Rigify"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Armature Layer Manager"
    bl_order = 0

    @classmethod
    def poll(self, context):
        return True