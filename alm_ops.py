import bpy

class AlmMixIn():
    """Mix-in class for armature layer manager objects, providing poll and armature identification"""
    
    def arma_single(self, context):
        '''Check if there is only one armature in the scene and return object if so'''
        arma_objs = [obj for obj in context.scene.objects if obj.type == 'ARMATURE']
        if len(arma_objs) == 1:
            return arma_objs[0]

    def arma(self, context):
        '''Return the most definitive armature object candidate'''
        pin = context.scene.bendify.alm_pin
        act = context.active_object
        if pin:
            return pin
        elif self.arma_single(context):
            return self.arma_single(context)
        elif act and act.type == 'ARMATURE':
            return act
    
    def meta_check(self, obj):
        '''Check if obj is metarig'''
        return hasattr(obj.data, 'rigify_layers') and len(obj.data.rigify_layers) >= 29

    def meta_any(self, context):
        '''Return all metarigs (data) in the scene'''
        return [obj for obj in context.scene.objects if obj.type == 'ARMATURE' and self.meta_check(obj)]

    def meta_single(self, context):
        '''Check if there is only one metarig in the scene and return object if so'''
        meta_objs = self.meta_any(context)
        if len(meta_objs) == 1:
            return meta_objs[0]

    def meta(self, context):
        '''Return the most definitive metarig candidate'''
        meta = context.scene.bendify.alm_meta
        act = context.active_object
        arma = self.arma(context)
        if meta:
            return meta
        elif self.meta_single(context):
            return self.meta_single(context)
        elif arma and self.meta_check(arma):
            return arma
        elif act and act.type == 'ARMATURE' and self.meta_check(act):
            return act
    
    def bendify(self, context):
        return context.scene.bendify
    
    @classmethod
    def poll(self, context):
        pin = context.scene.bendify.alm_pin
        act = context.active_object
        if pin:
            return pin
        elif act and act.type == 'ARMATURE':
            return act

class BENDIFY_OT_AlmToggle(bpy.types.Operator, AlmMixIn):
    """Toggle armature layer visibility for all layers"""
    bl_idname = 'view3d.armature_layer_manager_toggle'
    bl_label = "Armature Layers Toggle"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if sum(self.bendify(context).alm_layers) == 0:
            self.bendify(context).alm_layers = self.arma(context).data.layers
            self.arma(context).data.layers = 32 * [True]
        else:
            self.arma(context).data.layers = self.bendify(context).alm_layers
            self.bendify(context).alm_layers = 32 * [False]
        return {"FINISHED"}

class BENDIFY_OT_AlmSelect(bpy.types.Operator, AlmMixIn):
    """(De-)Select all bones in layer according to the chosen mode"""
    bl_idname = 'view3d.armature_layer_manager_select'
    bl_label = "Select Layer Bones"
    bl_options = {'REGISTER', 'UNDO'}
    
    layer: bpy.props.IntProperty(name="Layer", min=0, max=31)
    select: bpy.props.BoolProperty(name="Select", default=True)
    new: bpy.props.BoolProperty(name="New Selection", default=True)

    def execute(self, context):
        def bone_select(bone, select):
            bone.select = select
            bone.select_head = select
            bone.select_tail = select
        
        obj = self.arma(context)
        if context.mode == 'EDIT_ARMATURE':
            bones = obj.data.edit_bones
        else:
            bones = obj.data.bones
        
        for bone in bones:
            if bone.layers[self.layer]:
                bone_select(bone, self.select)
            else:
                if self.new:
                    bone_select(bone, False)

        return {"FINISHED"}

class BENDIFY_OT_AlmLock(bpy.types.Operator, AlmMixIn):
    """Lock all bones in one specific layer"""
    bl_idname = 'view3d.armature_layer_manager_lock'
    bl_label = "Lock All Bones In Layer"
    bl_options = {'REGISTER', 'UNDO'}
    
    layer: bpy.props.IntProperty(name="Layer", min=0, max=31)

    def execute(self, context):
        obj = self.arma(context)
        lock = True
        mode = False
        if context.mode == 'EDIT_ARMATURE':
            mode = True
            bpy.ops.object.mode_set(mode='POSE')
        for bone in obj.data.bones:
            if bone.layers[self.layer]:
                if bone.hide_select:
                    lock = False
        for bone in obj.data.bones:
            if bone.layers[self.layer]:
                if lock:
                    bone.select = False
                    bone.select_head = False
                    bone.select_tail = False
                bone.hide_select = lock
        if mode:
            bpy.ops.object.mode_set(mode='EDIT')
        return {"FINISHED"}

class BENDIFY_OT_AlmAdd(bpy.types.Operator, AlmMixIn):
    """Add selection to specified layer"""
    bl_idname = 'view3d.armature_layer_manager_add'
    bl_label = "Add Bones To Layer"
    bl_options = {'REGISTER', 'UNDO'}
    
    layer: bpy.props.IntProperty(name="Layer", min=0, max=31)
    move: bpy.props.BoolProperty(name="Move", default=False)
    
    @classmethod
    def poll(self, context):
        if AlmMixIn.poll(context):
            return context.selected_bones or context.selected_pose_bones

    def execute(self, context):
        if context.mode == 'POSE':
            bones = [context.active_object.data.bones[b.name] for b in context.selected_pose_bones]
        else:
            bones = context.selected_bones
        for bone in bones:
            bone.layers[self.layer] = True
            if self.move:
                for i in range(31):
                    if not i == self.layer:
                        bone.layers[i] = False
        return {"FINISHED"}

class BENDIFY_OT_AlmSolo(bpy.types.Operator, AlmMixIn):
    """Set armature layer to solo"""
    bl_idname = 'view3d.armature_layer_manager_solo'
    bl_label = "Solo Layer"
    bl_options = {'REGISTER', 'UNDO'}
    
    layer: bpy.props.IntProperty(name="Layer", min=0, max=31)

    def execute(self, context):
        obj = self.arma(context)
        obj.data.layers[self.layer] = True
        for i in range(31):
            if not i == self.layer:
                obj.data.layers[i] = False
        return {"FINISHED"}