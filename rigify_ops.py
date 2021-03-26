from bpy.props import EnumProperty
from bpy.types import Operator


class BENDIFY_OT_RigifyAddBendifyParent(Operator):
    """Add parent to rig module"""
    bl_idname = 'pose.rigify_add_bendify_parent'
    bl_label = "+"
    bl_options = {'INTERNAL', 'UNDO'}

    parent_type: EnumProperty(
        name="Parent Type",
        items=(
            ('PARENTS_BASE', "Base Parent", "Base Parent"),
            ('PARENTS_CURVE', "Tip Parent", "Tip Parent"),
            ('PARENTS_TIP', "Curve Parent", "Curve Parent")
        ),
        default='PARENTS_BASE'
    )
    
    @classmethod
    def poll(cls, context):
        if context.mode == 'POSE':
            try:
                return context.active_pose_bone.rigify_type
            except AttributeError:
                return None

    def execute(self, context):
        getattr(context.active_pose_bone.rigify_parameters, self.parent_type.lower()).add()
        return {"FINISHED"}