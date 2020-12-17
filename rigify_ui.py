import bpy
from rigify.ui import DATA_PT_rigify_buttons, DATA_PT_rigify_bone_groups, BONE_PT_rigify_buttons

class BENDIFY_PT_BoneType(bpy.types.Panel):
    bl_category = "Bendify"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Rigify Type"
    bl_order = 1
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        if not context.object:
            return False
        return context.object.type == 'ARMATURE' and context.active_pose_bone\
               and context.active_object.data.get("rig_id") is None
    
    def draw(self, context):
        BONE_PT_rigify_buttons.draw(self, context)

class BENDIFY_PT_BoneGroups(bpy.types.Panel):
    bl_category = "Bendify"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Rigify Bone Groups"
    bl_order = 4
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        if not context.object:
            return False
        return context.object.type == 'ARMATURE' and context.active_object.data.get("rig_id") is None

    def draw(self, context):
        DATA_PT_rigify_bone_groups.draw(self, context)
        self.layout.operator('armature.bendify_add_bone_groups')

class BENDIFY_PT_RigifyButtons(bpy.types.Panel):
    bl_category = "Bendify"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Rigify Buttons"
    bl_order = 5
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        if not context.object:
            return False
        return context.object.type == 'ARMATURE' and context.active_object.data.get("rig_id") is None
    
    def draw(self, context):
        DATA_PT_rigify_buttons.draw(self, context)