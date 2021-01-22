import bpy
from .alm_ops import AlmMixIn

class ArmatureLayerManagerPanel(AlmMixIn):
    """Armature Layer Panel drawing class"""    

    def layers_get(self, context):
        '''Returns a list of layer numbers to draw'''
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

    def pins(self, context):
        '''UI for the armature and metarig pins'''
        bendify = self.bendify(context)
        arma = self.arma(context)
        arma_single = self.arma_single(context)
        meta = self.meta(context)
        meta_any = self.meta_any(context)
        meta_single = self.meta_single(context)

        split = self.layout.split()
        
        col = split.column()
        col.row().label(text="Pinned Armature" if bendify.alm_pin or not arma else "Active: " + arma.name)
        if not arma_single:
            col.row().prop(
                bendify,
                'alm_pin',
                text="",
                icon='PINNED' if bendify.alm_pin else 'UNPINNED',
            )
        
        col = split.column()
        if meta_any:
            col.row().label(text="Pinned Metarig" if bendify.alm_meta or not meta or not meta.data else "Layer Names: " + meta.name)
        if bendify.alm_meta or meta_any and not meta_single:
            col.row().prop(
                bendify,
                'alm_meta',
                text="",
                icon='PINNED' if bendify.alm_meta else 'UNPINNED',
            )

    def toggles(self, context, layout):
        '''UI for "Empty" and "Compact" toggles (for buttons & edit)'''
        bendify = self.bendify(context)

        row = layout.row(align=True)
        # Empty Layers
        row.prop(
            bendify,
            'alm_empty',
            text="Empty",
            icon='GHOST_ENABLED' if bendify.alm_empty else 'GHOST_DISABLED',
            expand=True
        )

        # Compact
        row.prop(
            bendify,
            'alm_compact',
            text="Compact",
            icon='COLLAPSEMENU' if bendify.alm_compact else 'ALIGN_JUSTIFY',
            expand=True
        )

        layout.row().separator()

    def settings(self, context):
        '''UI for Armature viewport display toggles and mode selector'''
        bendify = self.bendify(context)
        obj = self.arma(context)
        data = obj.data

        # Display options
        layout = self.layout
        split = layout.row().split()
        row = split.row()
        row.prop(data, 'pose_position', expand=True)
        row = split.row()
        row.prop(data, 'display_type', text="")
        row.prop(data, 'show_axes', text="", icon='EMPTY_AXIS',expand=True)
        row.prop(obj, 'show_in_front', text="", icon='XRAY', expand=True)

        layout.row().separator()

        # Mode selector
        layout.row().prop(
            bendify,
            'alm_mode',
            expand=True
        )

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

        layout.row().separator()

    def layers(self, context):
        '''UI for simple layers view'''
        obj = self.arma(context)
        self.layout.row(align=True).prop(obj.data, 'layers', text="")

    def buttons(self, context):   
        '''Buttons UI'''    
        bendify = self.bendify(context)

        obj = self.arma(context)
        meta = self.meta(context)
        data = obj.data

        layout = self.layout

        # Create the layer rows
        box = layout.box()
        col = box.column()

        self.toggles(context, col)

        for i in self.layers_get(context):  
            
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
            if meta and meta.data.rigify_layers:
                if i < 29:
                    rigify_name = meta.data.rigify_layers[i].name
                    layer_name = rigify_name if rigify_name else " "
                    
                elif i == 29:
                    layer_name = "DEF"
                elif i == 30:
                    layer_name = "MCH"
                elif i == 31:
                    layer_name = "ORG"
            else:
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
        '''Rigify Layer Names mode'''
        bendify = self.bendify(context)

        layout = self.layout
        obj = self.arma(context)
        meta = self.meta(context)

        col = layout.box().column()

        # Ensure that the layers exist
        if not meta and hasattr(obj.data, 'rigify_layers'):
            if 0:
                for i in range(1 + len(obj.data.rigify_layers), 29):
                    obj.data.rigify_layers.add()
            else:
                # Can't add while drawing, just use button
                if len(obj.data.rigify_layers) < 29:
                    col.row().operator("pose.rigify_layer_init")
                    return

        else:
            self.toggles(context, col)
            # UI
            reserved_names = {29: 'DEF', 30: 'MCH', 31: 'ORG'}
            for i in self.layers_get(context):
                entry = col.row(align=True)
                if not bendify.alm_compact:
                    split = entry.split(factor=0.5, align=True)
                    entry = split.split(factor=0.15, align=True)
                icon = ('RESTRICT_VIEW_OFF' if obj.data.layers[i] else 'RESTRICT_VIEW_ON') if bendify.alm_compact else 'NONE'
                entry.prop(obj.data, "layers", index=i, text="" if bendify.alm_compact else str(i + 1), toggle=True, icon=icon)
                if i in reserved_names:
                    entry.label(text=reserved_names[i])
                else:
                    rigify_layer = meta.data.rigify_layers[i]
                    entry.prop(rigify_layer, "name", text="")
                    if not bendify.alm_compact:
                        extra = split.row(align=True)
                        extra.prop(rigify_layer, "row", text="UI")
                        extra.enabled = False if i == 28 else True
                        icon = 'RADIOBUT_ON' if rigify_layer.selset else 'RADIOBUT_OFF'
                        extra.prop(rigify_layer, "selset", text="", toggle=True, icon=icon)
                        if rigify_layer.group == 0:
                            group_text = 'None'
                        else:
                            group_text = meta.data.rigify_colors[rigify_layer.group-1].name
                        extra.prop(rigify_layer, "group", text=group_text)

    def preview(self, context):
        '''Build a live UI preview based on metarig data'''
        """
        def bone_check(obj, layer):
            return any(b.layers[layer] for b in obj.data.bones) \
            or  any(
                pb.rigify_type \
                and pb.rigify_parameters.tweak_layers_extra and pb.rigify_parameters.tweak_layers[layer] \
                or pb.rigify_parameters.primary_layers_extra and pb.rigify_parameters.primary_layers[layer] \
                or pb.rigify_parameters.secondary_layers_extra and pb.rigify_parameters.secondary_layers[layer] \
                or pb.rigify_parameters.fk_layers_extra and pb.rigify_parameters.fk_layers[layer] \
                for pb in obj.pose.bones
            )
        """

        layout = self.layout
        obj = self.arma(context)
        meta = self.meta(context)

        col = layout.box().column()
        if meta:
            for i in range(28):
                buttons = []
                for r in range(28):
                    r_layer = meta.data.rigify_layers[r]
                    if r_layer.row == i and r_layer.name.replace(" ",""): #bone_check(obj, r):
                        buttons.append([r, r_layer.name])
                if buttons:
                    split = col.row().split()
                for b in buttons:
                    split.row().prop(obj.data, 'layers', index=b[0], text=b[1], toggle=True)
            
            col.row().separator()
            col.row().separator()
            col.row().prop(obj.data, 'layers', index=28, text=meta.data.rigify_layers[28].name, toggle=True)
        else:
            col.row().label(text="Metarig not found", icon='ERROR')

    def draw(self, context):
        bendify = self.bendify(context)
        self.pins(context)
        if self.arma(context):
            self.settings(context)
            if bendify.alm_mode == 'LAYERS':
                self.layers(context)
            if bendify.alm_mode == 'BUTTONS':
                self.buttons(context)
            elif bendify.alm_mode == 'EDIT':
                self.edit(context)
            elif bendify.alm_mode == 'PREVIEW':
                self.preview(context)
        
class BENDIFY_PT_ArmatureLayerManagerViewport(bpy.types.Panel, ArmatureLayerManagerPanel):
    bl_category = "Bendify"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Armature Layer Manager"
    bl_order = 0

    @classmethod
    def poll(self, context):
        return True