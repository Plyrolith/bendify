from bpy.types import Panel
from rigify import rig_lists
from rigify.ui import DATA_PT_rigify_buttons, DATA_PT_rigify_bone_groups, BONE_PT_rigify_buttons


class BoneSubPanelMixin():
    @classmethod
    def poll_sub(cls, context, ui):
        bone = context.active_pose_bone
        rig_name = str(bone.rigify_type).replace(" ", "")
        if rig_name != "":
            try:
                rig = rig_lists.rigs[rig_name]['module']
                return hasattr(rig.Rig, ui)
            except (ImportError, AttributeError):
                return False
    
    def draw_sub(self, context, ui):
        layout = self.layout
        bone = context.active_pose_bone
        rig = rig_lists.rigs[str(bone.rigify_type).replace(" ", "")]['module']
        getattr(rig.Rig, ui)(layout, bone.rigify_parameters)

### New rig type panels

class BoneBBones(BoneSubPanelMixin):
    @classmethod
    def poll(cls, context):
        if BENDIFY_PT_BoneType.poll(context):
            return cls.poll_sub(context, 'bbones_ui')

    def draw(self, context):
        self.draw_sub(context, 'bbones_ui')

class TweakAttach(BoneSubPanelMixin):
    @classmethod
    def poll(cls, context):
        if BENDIFY_PT_BoneType.poll(context):
            return cls.poll_sub(context, 'tweak_attach_ui')

    def draw(self, context):
        self.draw_sub(context, 'tweak_attach_ui')

class BoneParents(BoneSubPanelMixin):
    @classmethod
    def poll(cls, context):
        if BENDIFY_PT_BoneType.poll(context):
            return cls.poll_sub(context, 'parents_ui')

    def draw(self, context):
        self.draw_sub(context, 'parents_ui')

### Properties panels

class BONE_PT_BoneBBones(BoneBBones, Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_label = "Bendy Bones"
    bl_context = "bone"
    bl_options = {'DEFAULT_CLOSED'}
    bl_parent_id = "BONE_PT_rigify_buttons"
    bl_order = 1

class BONE_PT_TweakAttach(TweakAttach, Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_label = "Tweak Start & End Attach"
    bl_context = "bone"
    bl_options = {'DEFAULT_CLOSED'}
    bl_parent_id = "BONE_PT_rigify_buttons"
    bl_order = 2

class BONE_PT_BoneParents(BoneParents, Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_label = "Parenting Targets"
    bl_context = "bone"
    bl_options = {'DEFAULT_CLOSED'}
    bl_parent_id = "BONE_PT_rigify_buttons"
    bl_order = 3

### View3D panels

class BENDIFY_PT_BoneBBones(BoneBBones, Panel):
    bl_category = "Bendify"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Bendy Bones"
    bl_options = {'DEFAULT_CLOSED'}
    bl_parent_id = "BENDIFY_PT_BoneType"
    bl_order = 1

class BENDIFY_PT_TweakAttach(TweakAttach, Panel):
    bl_category = "Bendify"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Tweak Attach"
    bl_options = {'DEFAULT_CLOSED'}
    bl_parent_id = "BENDIFY_PT_BoneType"
    bl_order = 2

class BENDIFY_PT_BoneParents(BoneParents, Panel):
    bl_category = "Bendify"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Parenting Targets"
    bl_options = {'DEFAULT_CLOSED'}
    bl_parent_id = "BENDIFY_PT_BoneType"
    bl_order = 3

### Original rigify panels for View3D

class BENDIFY_PT_BoneType(Panel):
    bl_category = "Bendify"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Rigify Type"
    bl_order = 1

    @classmethod
    def poll(cls, context):
        return context.active_object \
        and context.active_object.type == 'ARMATURE' \
        and context.active_object.data.get("rig_id") is None \
        and context.active_pose_bone
    
    def draw(self, context):
        # Sometimes gets called even if poll is false... therefore, one more condition
        if context.active_pose_bone:
            self.layout.operator('pose.rigify_copy_to_selected', icon='COPYDOWN')
            BONE_PT_rigify_buttons.draw(self, context)

class BENDIFY_PT_BoneGroups(Panel):
    bl_category = "Bendify"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Rigify Bone Groups"
    bl_order = 4
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return context.active_object \
        and context.active_object.type == 'ARMATURE' \
        and context.active_object.data.get("rig_id") is None

    def draw(self, context):
        DATA_PT_rigify_bone_groups.draw(self, context)
        self.layout.operator('armature.bendify_add_bone_groups')


class BENDIFY_PT_RigifyButtons(Panel):
    bl_category = "Bendify"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Rigify Buttons"
    bl_order = 5

    @classmethod
    def poll(cls, context):
        return context.active_object \
        and context.active_object.type == 'ARMATURE' \
        and context.active_object.data.get("rig_id") is None
    
    def draw(self, context):
        DATA_PT_rigify_buttons.draw(self, context)
