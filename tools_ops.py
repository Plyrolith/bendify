import bpy
import re
import unicodedata

class BENDIFY_OT_StretchToReset(bpy.types.Operator):
    """Reset Stretch To constraint length for selected bones"""
    bl_idname = 'pose.stretchto_reset'
    bl_label = "Reset Strech Constraints"
    bl_options = {'REGISTER', 'UNDO'}

    selected: bpy.props.BoolProperty(name="Selected Only", default=True)
    
    @classmethod
    def poll(cls, context):
        return context.mode == 'POSE'

    def execute(self, context):
        #bpy.ops.constraint.stretchto_reset()
        bones = context.selected_pose_bones if self.selected else context.active_object.pose.bones
        for bone in bones:
            for c in bone.constraints:
                if c.type == 'STRETCH_TO':
                    c.rest_length = 0
        return {"FINISHED"}

class BENDIFY_OT_ConstraintsMirror(bpy.types.Operator):
    """Mirror Constraints of selected Bones to or from the other side"""
    bl_idname = 'pose.constraints_mirror'
    bl_label = "Mirror Constraints"
    bl_options = {'REGISTER', 'UNDO'}

    receive_constraints: bpy.props.BoolProperty(name="Receive Constraints", default=False)

    @classmethod
    def poll(cls, context):
        return context.mode == 'POSE' and context.selected_pose_bones

    def execute(self, context):
        def mirror_name(name):
            pair = []
            if ".L" in name:
                pair = [".L", ".R"]
            elif ".R" in name:
                pair = [".R", ".L"]
            if pair:
                return name.replace(pair[0], pair[1])
        
        def mirror_bone(obj, bone):
            mn = mirror_name(bone.name)
            if mn and mn in obj.pose.bones:
                return obj.pose.bones[mn]

        obj = context.active_object
        pbones = context.selected_pose_bones
        pb_active = context.active_pose_bone

        for pb in pbones:
            mb = mirror_bone(obj, pb)
            if mb:
                bpy.ops.pose.select_all(action='DESELECT')
                obj.data.bones[pb.name].select = True
                obj.data.bones[mb.name].select = True

                givr = mb if self.receive_constraints else pb
                rcvr = pb if self.receive_constraints else mb
                obj.data.bones.active = obj.data.bones[givr.name]

                if givr.constraints:
                    bpy.ops.pose.constraints_copy()
                    for c in rcvr.constraints:
                        c.name = mirror_name(c.name) or c.name
                        if hasattr(c, 'subtarget'):
                            if c.subtarget:
                                c.subtarget = mirror_name(c.subtarget) or c.subtarget
                        if hasattr(c, 'targets'):
                            for t in c.targets:
                                if t.subtarget:
                                    t.subtarget = mirror_name(t.subtarget) or t.subtarget
        
        bpy.ops.pose.select_all(action='DESELECT')
        for bone_sel in pbones:
            obj.data.bones[bone_sel.name].select = True
        obj.data.bones.active = obj.data.bones[pb_active.name]
        return {"FINISHED"}

class BENDIFY_OT_ConstraintsAddArmature(bpy.types.Operator):
    """Add armature constraints with targets"""
    bl_idname = 'pose.constraints_add_armature'
    bl_label = "Add Targeted Armature Constraints"
    bl_options = {'REGISTER', 'UNDO'}

    use_bone_envelopes: bpy.props.BoolProperty(name="Preserve Volume", default=False)
    use_deform_preserve_volume: bpy.props.BoolProperty(name="Use Envelopes", default=False)
    use_current_location: bpy.props.BoolProperty(name="Use Current Location", default=False)
    mode: bpy.props.EnumProperty(
        items=(
            ('ACTIVE', 'Active', 'Active'),
            ('SELECTED', 'Selected', 'Selected'),
            ('PARENT', 'Parent', 'Parent')
        ),
        name='Targeting Mode',
        default='ACTIVE'
    )
    redistribute: bpy.props.BoolProperty(name="Redistribute Weights", default=False)

    @classmethod
    def poll(cls, context):
        return context.mode == 'POSE' and len([obj for obj in context.selected_objects if obj.type == 'ARMATURE']) == 1

    def execute(self, context):
        def arma_get(pbone):
            arma = None
            for c in pbone.constraints:
                if c.type == 'ARMATURE':
                    arma = c
                    break
            if not arma:
                arma = pbone.constraints.new(type='ARMATURE')
            return arma
        
        def arma_move(context, pbone, constraint):
            i = pbone.constraints.find(constraint.name)
            if i > 0:
                data = context.active_object.data
                pb_act = data.bones.active
                context_c = context.copy()
                context_c["constraint"] = constraint
                data.bones.active = data.bones[pbone.name]
                for i in range(i):
                    bpy.ops.constraint.move_up(context_c, constraint.name, 'BONE')
                data.bones.active = pb_act
            return i

        def arma_targets(obj, arma, targets):
            weight = 1.0
            for t in arma.targets:
                weight -= t.weight
                if t.target == obj and t.subtarget in targets:
                    targets.remove(t.subtarget)
            
            weight = weight / len(targets)

            for t in targets:
                new_t = arma.targets.new()
                new_t.target = obj
                new_t.subtarget = t
                new_t.weight = weight
            
        def arma_redistribute(arma):
            l = len(arma.targets)
            for t in arma.targets:
                t.weight = 1.0 / l
        
        act = context.active_object
        pairing = {}
        if self.mode == 'ACTIVE':
            targets = [b.name for b in context.selected_pose_bones]
            targets.remove(context.active_pose_bone.name)
            pairing[context.active_pose_bone] = targets

        elif self.mode == 'SELECTED':
            receivers = context.selected_pose_bones
            receivers.remove(context.active_pose_bone)
            for r in receivers:
                pairing[r] = [context.active_pose_bone.name]
        
        elif self.mode == 'PARENT':
            for b in context.selected_pose_bones:
                if b.parent:
                    pairing[b] = [b.parent.name]
        
        bpy.ops.object.mode_set(mode='EDIT')
        for b in pairing:
            if b.parent:
                act.data.edit_bones[b.name].parent = None
        act.update_from_editmode()
        bpy.ops.object.mode_set(mode='POSE')

        for b in pairing:
            arma = arma_get(b)
            arma_move(context, b, arma)
            arma_targets(act, arma, pairing[b])

            arma.use_bone_envelopes = self.use_bone_envelopes
            arma.use_deform_preserve_volume = self.use_deform_preserve_volume
            arma.use_current_location = self.use_current_location
            arma.show_expanded = True

            if self.redistribute:
                arma_redistribute(arma)
        return {"FINISHED"}

class BENDIFY_OT_ObjectNamesNormalize(bpy.types.Operator):
    """Rename objects to match the optimal pattern"""
    bl_idname = 'object.object_names_normalize'
    bl_label = "Rename Objects"
    bl_options = {'REGISTER', 'UNDO'}

    selected: bpy.props.BoolProperty(name="Selected Only", default=True)
    lower: bpy.props.BoolProperty(name="Lowercase", default=True)
    data: bpy.props.BoolProperty(name="Data", default=True)
    multi: bpy.props.BoolProperty(name="Multi Guess", default=True)
    widgets: bpy.props.BoolProperty(name="Widgets", default=False)

    @classmethod
    def poll(cls, context):
        return bpy.data.objects

    def execute(self, context):
        for name_dict in self.object_names_normalize(context):
            for k, v in name_dict.items():
                k.name = v
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=480)

    def draw(self,context):
        layout = self.layout
        col = layout.column()
        row = col.row(align=True)
        sel_icon = 'RESTRICT_SELECT_OFF' if self.selected else 'RESTRICT_SELECT_ON'
        row.prop(self, "selected", expand=True, icon=sel_icon)
        low_icon = 'FONTPREVIEW' if self.lower else 'FILE_FONT'
        row.prop(self, "lower", expand=True, icon=low_icon)
        row = col.row(align=True)
        row.prop(self, "widgets", expand=True, icon='VIEW_PAN') 
        row.prop(self, "data", expand=True, icon='MOD_DATA_TRANSFER')
        row.prop(self, "multi", expand=True, icon='GP_MULTIFRAME_EDITING', emboss=self.data)
        box = col.box()
        for i, name_dict in enumerate(self.object_names_normalize(context)):
            icon = 'OBJECT_DATA' if i == 0 else "MOD_DATA_TRANSFER"
            for k, v in name_dict.items():
                row = box.row(align=True)
                row.label(text=k.name, icon=icon)
                row.label(text=v, icon='DISCLOSURE_TRI_RIGHT')
                #row.label(text=k.name + " > " + v, icon=icon)

    def object_names_normalize(self, context):
        """Renames objects in to match the optimal pattern.
        Returns: Tuple of object/data dictionaries with datablock keys and name values
        """
        
        def prefixes():
            return {
                'ARMATURE': "RIG",
                'CURVE': "CRV",
                'CAMERA': "CAM",
                'EMPTY': "MTY",
                'MESH': "GEO",
                'GPENCIL': "GPL",
                'LATTICE': "LAT",
                'META': "MBL",
                'LIGHT': "LGT",
                'LIGHT_PROBE': "LPR",
                'SPEAKER': "SPK",
                'SURFACE': "SFC",
                'FONT': "TXT",
                'WIDGET': "WGT",
                'VISIBILITY': "VIS"
            }

        def object_type_prefix(obj_type):
            """Selects standard naming convention prefixes for input object type (string)
            Returns: String
            """
            if obj_type in prefixes():
                return prefixes()[obj_type]
            else:
                return "OBJ"

        def string_clean(string, lower=True, dot=False):
            """Cleans a string, replacing all special characters with underscores.
            Also attempts to replace local special characters with simplified standard ones
            and removes double underscores.
            Returns: String.
            """
            tmp_string = ""
            for char in string.replace("ß","ss"):
                desc = unicodedata.name(char)
                cutoff = desc.find(' WITH ')
                if cutoff != -1:
                    desc = desc[:cutoff]
                    try:
                        char = unicodedata.lookup(desc)
                    except KeyError:
                        pass  # removing "WITH ..." produced an invalid name
                tmp_string += char
            if dot:
                allowed = '[^A-Za-z0-9.]+'
            else:
                allowed = '[^A-Za-z0-9]+'
            tmp_string = re.sub(allowed, '_', tmp_string).lstrip("_").rstrip("_")

            # Lowercase
            if lower:
                low_string = ""
                mutable = len(tmp_string) * [True]
                for p in list(prefixes().values()):
                    if p in tmp_string:
                        start = tmp_string.index(p)
                        end = start + len(p)
                        for p_i in range(start, end):
                            mutable[p_i] = False
                for i, m in enumerate(mutable):
                    low_string += tmp_string[i].lower() if m else tmp_string[i]
                tmp_string = low_string
            
            return re.sub('\_\_+', '*', tmp_string)

        def suffix_caps(name):
            '''Check for dot-one-letter segments and capitalize them'''
            segs = name.split(".")
            for seg in segs:
                if len(seg) == 1:
                    segs[segs.index(seg)] = seg.upper()
            return ".".join(segs)

        def rename(prefix, name, lower=True, widgets=False):
            dash_segs = name.split("-")
            if dash_segs[0] in list(prefixes().values()):
                prefix = dash_segs[0]
                name = "-".join(dash_segs[1:])
            if widgets:
                prefix = prefix.replace("GEO", "WGT")
            return "-".join([prefix, suffix_caps(string_clean(name, lower, dot=True))])

        objects = context.selected_objects if self.selected else bpy.data.objects

        # Dict for return
        obj_names = {}
        data_names = {}

        # Blocklists
        blocklist = ["WGTS_rig"]
        blocklist_data = []

        # Object renaming
        for obj in objects:
            if obj.name not in blocklist:
                prefix = object_type_prefix(obj.type)
                obj_name_new = rename(prefix, obj.name, self.lower, self.widgets)

                if not obj_name_new == obj.name:
                    obj_names[obj] = obj_name_new

                # Data renaming
                if self.data and obj.data not in blocklist_data and hasattr(obj.data, 'users'):
                    data_name_new = obj_name_new

                    # Multi user data
                    if obj.data.users > 1:
                        # Check if last segment is numeric
                        dot_segs = obj_name_new.split(".") if self.multi else obj.data.name.split(".")
                        data_name_new = rename(
                            prefix,
                            ".".join(dot_segs[:-1]) if dot_segs[-1].isnumeric() else ".".join(dot_segs),
                            self.lower,
                            self.widgets
                        )
                        blocklist_data.append(obj.data)

                    if not data_name_new == obj.data.name:
                        data_names[obj.data] = data_name_new
        
        return (obj_names, data_names)

class BENDIFY_OT_MaterialSlotsSwitch(bpy.types.Operator):
    """Convert material slots links for selected objects"""
    bl_idname = 'view3d.material_slots_switch'
    bl_label = "Switch Material Slot Links"
    bl_options = {'REGISTER', 'UNDO'}

    mode: bpy.props.EnumProperty(
            items=[
                ('OBJECT', "Object", "Object", 'OBJECT_DATA', 0),
                ('DATA', "Data", "Data", 'MESH_DATA', 1)
            ],
            name="Link Mode",
            default='OBJECT'
        )
    selected: bpy.props.BoolProperty(name="Selected Only", default=True)
    unlink: bpy.props.BoolProperty(name="Unlink Material from Other Slot", default=False)

    @classmethod
    def poll(cls, context):
        return bpy.data.objects
    
    def execute(self, context):
        objects = context.selected_objects if self.selected else bpy.data.objects
        opposite = {
            'OBJECT': 'DATA',
            'DATA': 'OBJECT'
        }
        for obj in objects:
            for slot in obj.material_slots:
                if slot.link is not self.mode:
                    if slot.material:
                        mat = slot.material
                        if self.unlink:
                            slot.material = None
                    else:
                        mat = None
                    slot.link = self.mode
                    if mat:
                        slot.material = mat
                elif self.unlink:
                    slot.link = opposite[self.mode]
                    slot.material = None
                    slot.link = self.mode

        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.row().prop(self, 'mode', expand=True)
        col.row().prop(self, 'selected')
        col.row().prop(self, 'unlink')

class BENDIFY_OT_DrawBlendSwitch(bpy.types.Operator):
    """Switch brush blend method in drawing mode"""
    bl_idname = 'paint.blend_switch'
    bl_label = "Draw Blend Switch"
    bl_options = {'REGISTER'}

    brush: bpy.props.EnumProperty(
        items=(
            ('ACTIVE', 'Active', 'Active', 'GREASEPENCIL', 0),
            ('DRAW', 'Draw', 'Draw', 'BRUSH_DATA', 1),
            ('DEDICATED', 'Dedicated', 'Dedicated', 'BRUSHES_ALL', 2)
        ),
        name="Brush",
        default='ACTIVE'
    )
    blend: bpy.props.EnumProperty(
        items=(
            ('ADD', 'Add', 'Add', 'ADD', 0),
            ('SUB', 'Sutract', 'Subtract', 'REMOVE', 1),
            ('MIX', 'Mix', 'Mix', 'DOT', 2)
        ),
        name="Blend",
        default='ADD'
    )

    @classmethod
    def poll(cls, context):
        modes = ('PAINT_WEIGHT', 'PAINT_TEXTURE', 'PAINT_VERTEX')
        return context.mode in modes

    def execute(self, context):
        brushes = bpy.data.brushes
        if context.mode == 'PAINT_WEIGHT':
            paint = context.tool_settings.weight_paint
        elif context.mode == 'PAINT_TEXTURE':
            paint = context.tool_settings.image_paint
        elif context.mode == 'PAINT_VERTEX':
            paint = context.tool_settings.vertex_paint
        
        if self.brush == 'ACTIVE':
            brush = paint.brush
        
        elif self.brush == 'DRAW':
            if 'Draw' not in brushes:
                brush = brushes.new('Draw')
            else:
                brush = brushes['Draw']
        
        elif self.brush == 'DEDICATED':
            name = self.blend.capitalize()
            if name not in brushes:
                brush = brushes.new(name)
            else:
                brush = brushes[name]

        brush.blend = self.blend
        brush.use_paint_vertex = True
        brush.use_paint_image = True
        brush.use_paint_weight = True

        paint.brush = brush
        bpy.ops.wm.tool_set_by_id(name="builtin_brush.Draw")
        return {"FINISHED"}