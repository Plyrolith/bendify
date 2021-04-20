from bpy.props import EnumProperty, IntProperty
from bpy.types import Operator


class BENDIFY_OT_RigifyBendifyParentAdd(Operator):
    """Add parent to rig module"""
    bl_idname = 'pose.rigify_add_bendify_parent'
    bl_label = "+"
    bl_options = {'INTERNAL', 'UNDO'}

    parent_type: EnumProperty(
        name="Parent Type",
        items=(
            ('PARENTS_IN', "Base Parent", "Base Parent"),
            ('PARENTS_CURVE', "Curve Parent", "Curve Parent"),
            ('PARENTS_OUT', "Outgoing Parent", "Outgoing Parent")
        ),
        default='PARENTS_IN'
    )
    
    @classmethod
    def poll(cls, context):
        if context.mode == 'POSE':
            try:
                return context.active_pose_bone.rigify_type
            except AttributeError:
                return None

    def execute(self, context):
        parents = getattr(context.active_pose_bone.rigify_parameters, self.parent_type.lower())
        weight = 1.0
        for p in parents:
            weight -= p.weight
        new = parents.add()
        new.weight = max(weight, 0.0)
        return {"FINISHED"}

class BENDIFY_OT_RigifyBendifyParentRemove(Operator):
    """Remove parent from rig module"""
    bl_idname = 'pose.rigify_remove_bendify_parent'
    bl_label = "X"
    bl_options = {'INTERNAL', 'UNDO'}

    parent_type: EnumProperty(
        name="Parent Type",
        items=(
            ('PARENTS_IN', "Base Parent", "Base Parent"),
            ('PARENTS_CURVE', "Curve Parent", "Curve Parent"),
            ('PARENTS_OUT', "Outgoing Parent", "Outgoing Parent")
        ),
        default='PARENTS_IN'
    )

    index: IntProperty(
        name="List Index",
        default=-1
    )
    
    @classmethod
    def poll(cls, context):
        if context.mode == 'POSE':
            try:
                return context.active_pose_bone.rigify_type
            except AttributeError:
                return None

    def execute(self, context):
        parents = getattr(context.active_pose_bone.rigify_parameters, self.parent_type.lower())
        if self.index == -1:
            parents.clear()
        else:
            parents.remove(self.index)
        return {"FINISHED"}