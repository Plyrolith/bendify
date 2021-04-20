from bpy.props import *

from collections.abc import Mapping
from itertools import count

from rigify.base_rig import BaseRig, stage
from rigify.utils.errors import MetarigError
from rigify.utils.naming import strip_org, make_derived_name
from rigify.utils.misc import map_list
from rigify.utils.layers import ControlLayersOption
from rigify.utils.rig import connected_children_names
from rigify.utils.bones import put_bone, align_bone_orientation
from rigify.utils.widgets_basic import create_sphere_widget

from .props import ArmaConstraintTargets
from .utils.bones import align_bone_between_bones, align_bone_to_bone_axis, connect_bone_to_bone, distance, put_bone_to_bone
from .utils.mechanism import make_armature_constraint
from .utils.misc import threewise, threewise_nozip, attribute_return, var_name
from .utils.widgets_bendy import create_sub_tweak_widget, create_simple_arrow_widget


# Mixin utils


class BendyBoneUtilsMixin():
    """
    Bone utilities for Bendy Rigs
    """

    def distance(self, bone_name1, bone_name2, tail=False):
        return distance(self.obj, bone_name1, bone_name2, tail)
    
    def align_bone_to_bone_axis(self, bone_name1, bone_name2, axis='Y', preserve='X'):
        align_bone_to_bone_axis(self.obj, bone_name1, bone_name2, axis, preserve)

    def align_bone_between_bones(self, bone_name, prev_target, roll_target, next_target, prev_tail=False, next_tail=False):
        align_bone_between_bones(self.obj, bone_name, prev_target, roll_target, next_target, prev_tail, next_tail)

    def attribute_return(self, attributes, iterable=False):
        return attribute_return(self, attributes, iterable)
    
    def make_armature_constraint(
        self, bone_name, subtargets, weights_reset=True, 
        weights_equalize=False, extend=True, index=None, **options
    ):
        return make_armature_constraint(
            self.obj, self.get_bone(bone_name), subtargets,
            weights_reset, weights_equalize, extend, index, **options
        )


class BendyBoneBBoneMixin():
    """
    B-Bone methods for Bendy Rigs
    """

    def bbone_setup(
        self,
        bone,
        bbone_segments=8,
        bbone_easein=1.0,
        bbone_easeout=1.0,
        bbone_custom_handle_start=None,
        bbone_custom_handle_end=None,
        bbone_curveinx=0.0,
        bbone_curveiny=0.0,
        bbone_curveoutx=0.0,
        bbone_curveouty=0.0,
        bbone_rollin=0.0,
        bbone_rollout=0.0,
        use_endroll_as_inroll=False,
        bbone_scaleinx=1.0,
        bbone_scaleiny=1.0,
        bbone_scaleoutx=1.0,
        bbone_scaleouty=1.0,
        bbone_handle_type_start=None,
        bbone_handle_type_end=None
        ):
        bbone = self.get_bone(bone)
        bbone.bbone_segments = bbone_segments
        #bbone.bbone_x = bbone_x
        #bbone.bbone_z = bbone_z
        bbone.bbone_curveinx = bbone_curveinx
        bbone.bbone_curveiny = bbone_curveiny
        bbone.bbone_curveoutx = bbone_curveoutx
        bbone.bbone_curveouty = bbone_curveouty
        bbone.bbone_rollin = bbone_rollin
        bbone.bbone_rollout = bbone_rollout
        bbone.use_endroll_as_inroll = use_endroll_as_inroll
        bbone.bbone_scaleinx = bbone_scaleinx
        bbone.bbone_scaleiny = bbone_scaleiny
        bbone.bbone_scaleoutx = bbone_scaleoutx
        bbone.bbone_scaleouty = bbone_scaleouty
        bbone.bbone_easein = bbone_easein
        bbone.bbone_easeout = bbone_easeout
        bbone.bbone_custom_handle_start = self.get_bone(bbone_custom_handle_start)
        if bbone_handle_type_start:
            bbone.bbone_handle_type_start = bbone_handle_type_start
        else:
            bbone.bbone_handle_type_start = 'TANGENT' if bbone_custom_handle_start else 'AUTO'
        bbone.bbone_custom_handle_end = self.get_bone(bbone_custom_handle_end)
        if bbone_handle_type_end:
            bbone.bbone_handle_type_end = bbone_handle_type_end
        else:
            bbone.bbone_handle_type_end = 'TANGENT' if bbone_custom_handle_end else 'AUTO'

    def bbone_copy(self, bbone, bbone_source, handle_start=None, handle_end=None):
        bbs = self.get_bone(bbone_source)
        self.bbone_setup(
            bbone,
            bbs.bbone_segments,
            bbs.bbone_easein,
            bbs.bbone_easeout,
            handle_start if handle_start else bbs.bbone_custom_handle_start,
            handle_end if handle_end else bbs.bbone_custom_handle_end,
            bbs.bbone_curveinx,
            bbs.bbone_curveiny,
            bbs.bbone_curveoutx,
            bbs.bbone_curveouty,
            bbs.bbone_rollin,
            bbs.bbone_rollout,
            bbs.use_endroll_as_inroll,
            bbs.bbone_scaleinx,
            bbs.bbone_scaleiny,
            bbs.bbone_scaleoutx,
            bbs.bbone_scaleouty,
            None if handle_start else bbs.bbone_handle_type_start,
            None if handle_end else bbs.bbone_handle_type_end
        )

    def bbone_chain(self, bones, start=None, end=None):
        for i, bone_prev, bone_curr, bone_next in zip(count(0), *threewise_nozip(bones)):
            type_start = type_end = 'ABSOLUTE'
            if i == 0 and start:
                type_start = 'TANGENT'
                bone_prev = start
            if i == len(bones) - 1 and end:
                type_end = 'TANGENT'
                bone_next = end
            b = self.get_bone(bone_curr)
            if bone_prev:
                b.bbone_handle_type_start = type_start
                b.bbone_custom_handle_start = self.get_bone(bone_prev)
            if bone_next:
                b.bbone_handle_type_end = type_end
                b.bbone_custom_handle_end = self.get_bone(bone_next)

    def copy_transforms(self, bone, target, space=None):
        if space:
            self.make_constraint(bone, 'COPY_LOCATION', target)
            self.make_constraint(bone, 'COPY_ROTATION', target, space='CUSTOM', space_object=self.obj, space_subtarget=space)
            self.make_constraint(bone, 'COPY_SCALE', target)
        else:
            self.make_constraint(bone, 'COPY_TRANSFORMS', target)

    def driver_bbone_variable(self, handles, transform):
        variables = {}
        for i, handle in enumerate(handles):
            var = var_name(i)
            
            # Transform
            if isinstance(handle, Mapping) and transform in handle:
                bone = handle['bone']
                transform_type = handle[transform]
            else:
                bone = handle
                transform_type = transform

            # Build dict
            if transform != 'NONE':
                variables[var] = {
                    'type': 'TRANSFORMS',
                    'targets':
                    [
                        {
                            'id': self.obj,
                            'bone_target': bone,
                            'transform_type': transform_type,
                            'transform_space': 'LOCAL_SPACE',
                        }
                    ]
                }
        return variables
    
    @staticmethod
    def driver_bbone_expression(handles, subtract_one=False):
        ex = []
        for i, handle in enumerate(handles):
            var = var_name(i)
            if subtract_one:
                var = var + " - 1"
            if isinstance(handle, Mapping) and 'weight' in handle:
                var = "(" + var + ") * " + str(handle['weight'])
            ex.append(var)
        return " + ".join(ex)

    def driver_bbone_make(self, bone, handles, data_path, transform, subtract_one=False):
        pbone = self.get_bone(bone)
        self.make_driver(
            pbone,
            data_path,
            expression=self.driver_bbone_expression(handles, subtract_one),
            variables=self.driver_bbone_variable(handles, transform)
        )

    def driver_bbone_ease(self, bone, handles_in, handles_out):
        for handles, data_path, transform in zip(
            [handles_in, handles_out],
            ['bbone_easein', 'bbone_easeout'],
            ['SCALE_Y', 'SCALE_Y']
        ):
            self.driver_bbone_make(bone, handles, data_path, transform, True)

    def driver_bbone_scale(self, bone, handles_in, handles_out):
        for handles, data_path, transform in zip(
            [handles_in] * 2 + [handles_out] * 2,
            ['bbone_scaleinx', 'bbone_scaleiny', 'bbone_scaleoutx', 'bbone_scaleouty'],
            ['SCALE_X', 'SCALE_Z', 'SCALE_X', 'SCALE_Z']
        ):
            self.driver_bbone_make(bone, handles, data_path, transform)


class ScaleOffsetMixin():
    """
    Mix-in class for copy scale driver creation
    """

    offset_axes = (
        ('NONE', "None", "None"),
        ('X', "X", "X"),
        ('Y', "Y", "Y"),
        ('Z', "Z", "Z")
    )

    def bone_scale_offset(self, bone, target, map_x='X', map_y='Y', map_z='Z', use_x=True, use_y=True, use_z=True, index=-1):
        if map_x == 'NONE':
            use_x = False
            map_x = 'X'
        if map_y == 'NONE':
            use_y = False
            map_y = 'Y'
        if map_z == 'NONE':
            use_z = False
            map_z = 'Z'
        
        if map_x == 'X' and map_y == 'Y' and map_z == 'Z':
            con = self.make_constraint(
                bone,
                'COPY_SCALE',
                target,
                space='LOCAL',
                use_offset=True,
                use_x=use_x,
                use_y=use_y,
                use_z=use_z
            )
        
        else:
            con = self.make_constraint(
                bone,
                'TRANSFORM',
                target,
                space='LOCAL',
                use_motion_extrapolate=True,
                map_from='SCALE',
                map_to='SCALE',
                map_to_x_from=map_x,
                map_to_y_from=map_y,
                map_to_z_from=map_z,
                from_min_x_scale=0,
                from_min_y_scale=0,
                from_min_z_scale=0,
                to_min_x_scale=0 if use_x else 1,
                to_min_y_scale=0 if use_y else 1,
                to_min_z_scale=0 if use_z else 1,
                mix_mode_scale='MULTIPLY'
            )
        
        # Move constraint
        if index >= 0:
            b = self.get_bone(bone)
            i = b.constraints.find(con.name)
            b.constraints.move(i, index)


# Main rig

class BendyRig(BaseRig, BendyBoneBBoneMixin, BendyBoneUtilsMixin):
    """
    Base bendy rig with driven B-Bones
    """

    def find_org_bones(self, bone):
        return [bone.name] + connected_children_names(self.obj, bone.name)

    mch_root_name = "MCH-root"
    min_chain_length = 1

    rotation_modes = (
        ('QUATERNION', 'Quaternion (WXYZ)', 'Quaternion (WXYZ)'),
        ('XYZ', 'XYZ', 'XYZ'),
        ('XZY', 'XZY', 'XZY'), 
        ('YXZ', 'YXZ', 'YXZ'),
        ('YZX', 'YZX', 'YZX'),
        ('ZXY', 'ZXY', 'ZXY'),
        ('ZYX', 'ZYX', 'ZYX'),
        ('AXIS_ANGLE', 'Axis Angle', 'Axis Angle') 
    )
    
    def initialize(self):
        if len(self.bones.org) < self.min_chain_length:
            self.raise_error("Input to rig type must be a chain of {} or more bones.", self.min_chain_length)
        
        self.bbone_copy_properties = self.params.bbone_copy_properties
        self.bbone_segments = self.params.bbone_segments
        self.bbone_easein = self.params.bbone_easein
        self.bbone_easeout = self.params.bbone_easeout
        self.bbone_ease = self.params.bbone_ease
        self.bbone_scale = self.params.bbone_scale

        self.rotation_mode_tweak = self.params.rotation_mode_tweak

        self.volume_deform_default = self.params.volume_deform_default
        self.volume_deform_panel = self.params.volume_deform_panel

        self.keep_axis = 'SWING_Y'

        self.root_bone = self.parent_org = self.get_bone(self.base_bone).parent.name if self.get_bone(self.base_bone).parent else "root"
        self.root_bone_mch = None
        self.default_prop_bone = None

    def parent_bones(self):
        self.rig_parent_bone = self.get_bone_parent(self.bones.org[0])

    ####################################################
    # Root for arma constrained MCHs

    @stage.generate_bones
    def make_root_mch(self):
        if not self.mch_root_name in self.obj.data.edit_bones:
            self.copy_bone("root", self.mch_root_name, parent=False)
        self.root_bone_mch = self.mch_root_name

    @stage.apply_bones
    def apply_root_mch(self):
        if self.mch_root_name in self.obj.data.bones:
            self.get_bone(self.mch_root_name).parent = None

    ####################################################
    # Master control

    @stage.configure_bones
    def configure_volume_deform_properties(self):
        if self.default_prop_bone:
            self.configure_volume_prop(
                self.default_prop_bone,
                self.volume_deform_default,
                "volume_deform",
                self.volume_deform_panel,
                strip_org(self.base_bone) + " Deform Volume Variation"
            )
    
    def configure_volume_prop(self, bone, default, prop, panel=True, text="Volume Variation"):
        self.make_property(
            bone,
            prop,
            default=default,
            max=100.0,
            soft_min=0.0,
            soft_max=max(default, 1.0),
            description=text
        )
        if panel:
            p = self.script.panel_with_selected_check(self, self.bones.ctrl.flatten())
            p.custom_prop(
                bone,
                prop,
                text=text,
                slider=True
            )

    ####################################################
    # Tweak chain

    @stage.generate_bones
    def make_tweak_chain(self):
        orgs = self.bones.org
        self.bones.ctrl.tweak = map_list(self.make_tweak_bone, count(0), orgs + orgs[-1:])
        self.default_prop_bone = self.bones.ctrl.tweak[0]

    def make_tweak_bone(self, i, org):
        name = self.copy_bone(org, 'tweak_' + strip_org(org), parent=False)

        if i == len(self.bones.org):
            put_bone(self.obj, name, self.get_bone(org).tail)

        return name

    @stage.parent_bones
    def parent_tweak_chain(self):
        for tweak in self.bones.ctrl.tweak:
            self.set_bone_parent(tweak, self.root_bone)

    @stage.configure_bones
    def configure_tweak_chain(self):
        for i, tweak, org in zip(count(0), self.bones.ctrl.tweak, self.bones.org + [None]):
            if org:
                self.copy_bone_properties(org, tweak)
            self.configure_tweak_bone(i, tweak)

    def configure_tweak_bone(self, i, tweak):
        tweak_pb = self.get_bone(tweak)
        tweak_pb.rotation_mode = self.rotation_mode_tweak

    @stage.generate_widgets
    def make_tweak_widgets(self):
        for tweak in self.bones.ctrl.tweak:
            self.make_tweak_widget(tweak)

    def make_tweak_widget(self, tweak):
        create_sphere_widget(self.obj, tweak, radius=0.25)

    ##############################
    # ORG chain

    @stage.parent_bones
    def parent_org_chain(self):
       orgs = self.bones.org
       self.parent_bone_chain(orgs, use_connect=False)

    @stage.apply_bones
    def bbone_org_chain(self):
        orgs = self.bones.org
        tweaks = self.bones.ctrl.tweak
        self.ease_org_chain(orgs)
        self.bbone_chain(orgs, tweaks[0], tweaks[-1])

    def ease_org_chain(self, orgs):
        if not self.bbone_copy_properties:
            for i, org in zip(count(0), orgs):
                ease_in = 0.0 if i == 0 and not self.bbone_easein else 1.0
                ease_out = 0.0 if i == len(orgs) - 1 and not self.bbone_easeout else 1.0
                self.bbone_setup(org, self.bbone_segments, ease_in, ease_out)

    @stage.rig_bones
    def rig_org_chain(self):
        tweaks = self.bones.ctrl.tweak
        for org, tweak, next_tweak in zip(self.bones.org, tweaks, tweaks[1:]):
            self.rig_org_bone(org, tweak, next_tweak, self.parent_org)

    def rig_org_bone(self, mch, target=None, next_target=None, scale=None):
        if target and target == scale:
            self.make_constraint(mch, 'COPY_TRANSFORMS', target)
        else:
            if target:
                self.make_constraint(mch, 'COPY_LOCATION', target)
                self.make_constraint(mch, 'COPY_ROTATION', target)
            if scale:
                self.make_constraint(mch, 'COPY_SCALE', scale)#, use_y=False if next_target else True)
        if next_target:
            stretch = self.make_constraint(mch, 'STRETCH_TO', next_target, keep_axis=self.keep_axis)
            self.make_driver(stretch, 'bulge', variables=[(self.default_prop_bone, 'volume_deform')])

    ####################################################
    # Deform bones

    @stage.generate_bones
    def make_deform_chain(self):
        self.bones.deform = map_list(self.make_deform_bone, count(0), self.bones.org)

    def make_deform_bone(self, i, org):
        return self.copy_bone(org, make_derived_name(org, 'def'), parent=True, bbone=True)

    @stage.parent_bones
    def parent_deform_chain(self):
        for deform, org in zip(self.bones.deform, self.bones.org):
            self.set_bone_parent(deform, org)

    @stage.parent_bones
    def bbone_deform_chain(self):
        deforms = self.bones.deform
        tweaks = self.bones.ctrl.tweak
        for i, deform, tweak, next_tweak, org in zip(count(0), deforms, tweaks, tweaks[1:], self.bones.org):
            if self.bbone_copy_properties:
                self.bbone_copy(deform, org)
            else:
                ease_in = 0.0 if i == 0 and not self.bbone_easein else 1.0
                ease_out = 0.0 if i == len(deforms) - 1 and not self.bbone_easeout else 1.0
                self.bbone_setup(deform, self.bbone_segments, ease_in, ease_out, tweak, next_tweak)

    @stage.rig_bones
    def rig_deform_chain(self):
        tweaks = self.bones.ctrl.tweak
        for args in zip(self.bones.deform, tweaks, tweaks[1:], tweaks):
            self.rig_deform_bone(*args, self.root_bone)
    
    def rig_deform_bone(self, bone, handle_start, handle_end, rotation=None, scale=None):
        self.make_constraint(bone, 'COPY_LOCATION', handle_start)
        if rotation:
            self.make_constraint(bone, 'COPY_ROTATION', rotation)
        if scale:
            self.make_constraint(bone, 'COPY_SCALE', scale)
        stretch = self.make_constraint(bone, 'STRETCH_TO', handle_end, keep_axis=self.keep_axis)
        self.make_driver(stretch, 'bulge', variables=[(self.default_prop_bone, 'volume_deform')])

    @stage.rig_bones
    def drivers_deform_chain(self):
        ctrls = self.bones.ctrl
        for args in zip(count(0), self.bones.deform, ctrls.tweak, ctrls.tweak[1:]):
            self.drivers_deform_bone(*args)
    
    def drivers_deform_bone(self, i, bone, handle_in, handle_out):
        if self.bbone_ease:
            self.driver_bbone_ease(bone, [handle_in], [handle_out])
        if self.bbone_scale:
            self.driver_bbone_scale(bone, [handle_in], [handle_out])

    ####################################################
    # UI

    @classmethod
    def bbones_ui(self, layout, params):
        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.row().prop(params, 'rotation_mode_tweak', text="Tweak Mode")
        r = layout.row(align=True)
        r.prop(params, 'bbone_ease', text="Ease", toggle=True)
        r.prop(params, 'bbone_scale', text="Scale", toggle=True)
        r = layout.row(align=True)
        r.prop(params, 'volume_deform_default', slider=True)
        r.prop(params, 'volume_deform_panel', text="", icon='OPTIONS')
        layout.row().prop(params, 'bbone_copy_properties')
        r_seg = layout.row()
        r_seg.prop(params, 'bbone_segments')
        r_ease = layout.row(align=True)
        r_ease.prop(params, 'bbone_easein', text="Ease In", toggle=True)
        r_ease.prop(params, 'bbone_easeout', text="Ease Out", toggle=True)
        if params.bbone_copy_properties:
            r_seg.enabled = r_ease.enabled = False

    ####################################################
    # SETTINGS
    
    @stage.finalize
    def finalize_armature_display(self):
        '''New function to set rig viewport display and protect layers'''
        self.obj.data.display_type = 'BBONE'
        for i in (29, 30, 31):
            self.obj.data.layers_protected[i] = True
    
    @classmethod
    def add_parameters(self, params):
        super().add_parameters(params)

        params.bbone_copy_properties = BoolProperty(
            name="Individual B-Bone Properties",
            default=False,
            description="Copy original B-Bone settings per bone",
        )

        params.bbone_segments = IntProperty(
            name="B-Bone Segments",
            default=8,
            min=1,
            max=32,
            description="Number of B-Bone segments",
        )

        params.bbone_easein = BoolProperty(
            name="B-Bone Ease In",
            default=True,
            description="Deform easing in for first bone of chain",
        )

        params.bbone_easeout = BoolProperty(
            name="B-Bone Ease Out",
            default=True,
            description="Deform easing out for last bone of chain",
        )

        params.bbone_ease = BoolProperty(
            name="Ease Drivers",
            default=True,
            description="B-Bone easing driven by tweak",
        )

        params.bbone_scale = BoolProperty(
            name="Scale Drivers",
            default=True,
            description="B-Bone scaling driven by tweak",
        )

        params.rotation_mode_tweak = EnumProperty(
            name="Default Tweak Controller Rotation Mode",
            items=self.rotation_modes,
            default='ZXY',
            description="Default rotation mode for tweak control bones",
        )

        params.volume_deform_default = FloatProperty(
            name="Volume Variation",
            default=1.0,
            soft_min=0.0,
            soft_max=1.0,
            description="Default value for deform bone chain stretch volume variation. Can still be set while animating",
        )

        params.volume_deform_panel = BoolProperty(
            name="Deform Volume Variation Panel",
            default=False,
            description="Add a panel for volume variation control to the UI",
        )


# Advanced variations, mixable

class HandleBendyRig(BendyRig):
    """
    Bendy rig with more handle types
    """

    def initialize(self):
        super().initialize()
        self.bbone_handles = self.params.bbone_handles

        self.tweak_mch = self.bbone_handles == 'TANGENT'

    ####################################################
    # Tweak MCH chain

    @stage.generate_bones
    def make_tweak_mch_chain(self):
        if self.tweak_mch:
            orgs = self.bones.org
            self.bones.mch.tweak = map_list(self.make_tweak_mch_bone, count(0), orgs + orgs[-1:])

    def make_tweak_mch_bone(self, i, org):
        name = make_derived_name(org, 'mch', '_tweak')
        name = self.copy_bone(org, name, parent=False)

        if i == len(self.bones.org):
            put_bone(self.obj, name, self.get_bone(org).tail)
        
        return name

    @stage.parent_bones
    def parent_tweak_mch_chain(self):
        if self.tweak_mch:
            for mch in self.bones.mch.tweak:
                self.set_bone_parent(mch, self.root_bone_mch)
    
    @stage.parent_bones
    def align_tweak_mch_chain(self):
        if self.tweak_mch:
            mchs = self.bones.mch.tweak
            targets = threewise_nozip(mchs)
            
            for mch, p, c, n in zip(mchs, *targets):
                self.align_bone_between_bones(mch, p, c, n, next_tail=True if c == n else False)

    ####################################################
    # Tweak chain

    @stage.parent_bones
    def parent_tweak_chain(self):
        tweaks = self.bones.ctrl.tweak
        parents = self.bones.mch.tweak if self.tweak_mch else len(tweaks) * [self.root_bone]
        for args in zip(tweaks, parents):
            self.parent_tweak_bone(*args)

    def parent_tweak_bone(self, tweak, parent):
        inherit = {
            'NONE': 'AVERAGE',
            'Y': 'FIX_SHEAR',
            'TANGENT': 'AVERAGE',
        }
        self.set_bone_parent(tweak, parent, inherit_scale=inherit[self.bbone_handles])
    
    @stage.parent_bones
    def align_tweak_chain(self):
        if self.tweak_mch:
            tweaks = self.bones.ctrl.tweak
            targets = threewise_nozip(tweaks)
            
            for tweak, p, c, n in zip(tweaks, *targets):
                self.align_bone_between_bones(tweak, p, c, n, next_tail=True if c == n else False)

    def configure_tweak_bone(self, i, tweak):
        super().configure_tweak_bone(i, tweak)
        tweak_pb = self.get_bone(tweak)
        tweak_pb.lock_rotation_w = self.bbone_handles == 'NONE'
        tweak_pb.lock_rotation[0] = not self.bbone_handles == 'TANGENT'
        tweak_pb.lock_rotation[1] = self.bbone_handles == 'NONE'
        tweak_pb.lock_rotation[2] = not self.bbone_handles == 'TANGENT'
        tweak_pb.lock_scale = (not self.bbone_scale, not self.bbone_ease, not self.bbone_scale)

    ####################################################
    # Deform chain

    @stage.parent_bones
    def bbone_deform_chain(self):
        deforms = self.bones.deform
        tweaks = self.bones.ctrl.tweak
        for i, deform, tweak, next_tweak, org in zip(count(0), deforms, tweaks, tweaks[1:], self.bones.org):
            handle_start = tweak if self.bbone_handles == 'TANGENT' else None
            handle_end = next_tweak if self.bbone_handles == 'TANGENT' else None
            if self.bbone_copy_properties:
                self.bbone_copy(deform, org, handle_start, handle_end)
            else:
                ease_in = 0.0 if i == 0 and not self.bbone_easein else 1.0
                ease_out = 0.0 if i == len(deforms) - 1 and not self.bbone_easeout else 1.0
                self.bbone_setup(deform, self.bbone_segments, ease_in, ease_out, handle_start, handle_end)
        if not self.bbone_handles == 'TANGENT':
            self.bbone_chain(deforms)
            
    @stage.rig_bones
    def rig_deform_chain(self):
        tweaks = self.bones.ctrl.tweak
        rots = tweaks if self.bbone_handles != 'NONE' else len(tweaks) * [None]
        for args in zip(self.bones.deform, tweaks, tweaks[1:], rots):
            self.rig_deform_bone(*args)

    ####################################################
    # UI

    @classmethod
    def bbones_ui(self, layout, params):
        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.row().prop(params, 'bbone_handles', text="Handles", toggle=True)
        super().bbones_ui(layout, params)

    ####################################################
    # SETTINGS
    
    @classmethod
    def add_parameters(self, params):
        super().add_parameters(params)

        params.bbone_handles = EnumProperty(
            name="B-Bone Handles",
            items=[
                ('NONE', "None", "None"),
                ('Y', "Y Rotation Only", "Y Rotation Only"),
                ('TANGENT', "Full Tangent", "Full Tangent")
            ],
            default='TANGENT',
            description="B-Bone handles alignment",
        )

# INVISIBLE
class VolumeBendyRig(BaseRig, ScaleOffsetMixin):
    """
    Bendy rig with volume scaling control
    """

    def initialize(self):
        super().initialize()

        self.deform_scale = self.params.deform_scale
        self.deform_scale_x = self.params.deform_scale_x
        self.deform_scale_z = self.params.deform_scale_z

    ##############################
    # Deform

    @stage.finalize
    def offset_scale_chain(self):
        if self.deform_scale:
            for bone in [self.bones.deform, self.bones.org]:
                self.offset_scale_bone(bone)

    def offset_scale_bone(self, bone):
        self.bone_scale_offset(
            bone,
            self.deform_scale,
            self.deform_scale_x,
            'Y',
            self.deform_scale_z,
            use_y=False
        )

    ####################################################
    # UI

    @classmethod
    def bbones_ui(self, layout, params):
        super().bbones_ui(layout, params)
        col = layout.box().column()
        col.use_property_split = True
        col.use_property_decorate = False
        col.row().prop(params, 'deform_scale')
        if params.deform_scale:
            col.row().prop(params, 'deform_scale_x', expand=True)
            col.row().prop(params, 'deform_scale_z', expand=True)

    ####################################################
    # SETTINGS

    @classmethod
    def add_parameters(self, params):
        super().add_parameters(params)

        params.deform_scale = StringProperty(
            name="Volume Offset",
            default="",
            description="Copy X/Y scale from this bone",
        )

        params.deform_scale_x = EnumProperty(
            items=self.offset_axes,
            name="X Source Axis",
            default='X',
            description="Source axis for X scale deform offset",
        )

        params.deform_scale_z = EnumProperty(
            items=self.offset_axes,
            name="Z Source Axis",
            default='Z',
            description="Source axis for Z scale deform offset",
        )

# MAKE PANEL
class ParentedBendyRig(HandleBendyRig, ScaleOffsetMixin):
    """
    Bendy rig with complex parenting
    """

    def initialize(self):
        super().initialize()

        self.parents_in = self.attributes_to_dicts(self.params.parents_in)
        self.parents_in_copy_rotation = self.params.parents_in_copy_rotation
        self.parents_in_copy_rotation_default = self.params.parents_in_copy_rotation_default
        self.parents_in_copy_rotation_panel = self.params.parents_in_copy_rotation_panel
        self.parents_in_copy_scale = self.params.parents_in_copy_scale
        self.parents_in_copy_scale_default = self.params.parents_in_copy_scale_default
        self.parents_in_copy_scale_panel = self.params.parents_in_copy_scale_panel
        self.parents_in_type_single = self.params.parents_in_type_single

    def attributes_to_dicts(self, parents):
        dicts_list = []
        for p in parents:
            dicts_list.append(
                dict((key, getattr(p, key)) for key in dir(p) if key not in dir(p.__class__))
            )
        return dicts_list or [{"name": self.parent_org, "weight": 1.0}]

    ####################################################
    # Parent MCH chain

    @stage.generate_bones
    def make_parent_mch_chain(self):
        orgs = self.bones.org
        self.bones.mch.parent_in = self.make_parent_mch_bone(orgs[0], "_parent_in")
        self.bones.mch.inherit_in = self.root_bone = self.make_parent_mch_bone(orgs[0], "_inherit_in")

    def make_parent_mch_bone(self, org, suffix="", tail=False):
        orgs = self.bones.org
        name = make_derived_name(orgs[0], 'mch', suffix)
        name = self.copy_bone(org, name, parent=False)
        if tail:
            put_bone(self.obj, name, self.get_bone(org).tail)
        return name
    
    @stage.parent_bones
    def parent_parent_mch_chain(self):
        mchs = self.bones.mch
        self.set_bone_parent(mchs.parent_in, self.root_bone_mch)
        self.set_bone_parent(mchs.inherit_in, mchs.parent_in, inherit_scale='FIX_SHEAR')
        if self.parents_in_copy_rotation:
            align_bone_orientation(self.obj, mchs.inherit_in, self.parents_in_copy_rotation)
    
    @stage.rig_bones
    def rig_parent_mch_chain(self):
        mchs = self.bones.mch
        self.rig_parent_mch_bone(
            mchs.parent_in,
            self.parents_in,
            self.parents_in_type_single
        )
        self.rig_inherit_mch_bone(
            mchs.inherit_in,
            self.default_prop_bone,
            self.parents_in_copy_rotation,
            self.parents_in_copy_rotation_default,
            self.parents_in_copy_rotation_panel,
            self.parents_in_copy_scale,
            self.parents_in_copy_scale_default,
            self.parents_in_copy_scale_panel
        )
    
    def rig_parent_mch_bone(self, mch, parents, single_type='ARMATURE'):
        if len(parents) < 2 and single_type=='CHILD_OF':
            self.make_constraint(mch, 'CHILD_OF', parents[0]['name'])
        else:
            self.make_armature_constraint(mch, parents)
    
    def rig_inherit_mch_bone(
        self,
        inherit,
        prop_bone=None,
        copy_rotation=None,
        copy_rotation_default=1.0,
        copy_rotation_panel=False,
        copy_scale=None,
        copy_scale_default=1.0,
        copy_scale_panel=False
    ):
        if not prop_bone:
            prop_bone = self.default_prop_bone
        
        for target, default, panel, c_type in zip(
            [copy_rotation, copy_scale],
            [copy_rotation_default, copy_scale_default],
            [copy_rotation_panel, copy_scale_panel],
            ['copy_rotation', 'copy_scale']
        ):
            if target:
                text = c_type.split("_")
                text = " ".join([text[0], target, text[1]]).title()
                constraint = self.make_constraint(inherit, c_type.upper(), target, influence=default)
                self.configure_parent_prop(prop_bone, default, c_type, panel, text)
                self.make_driver(constraint, 'influence', variables=[(prop_bone, c_type)])

    def configure_parent_prop(self, bone, default, prop, panel=True, text="Parent"):
        self.make_property(bone, prop, default=default, description=text)
        if panel:
            p = self.script.panel_with_selected_check(self, self.bones.ctrl.flatten())
            p.custom_prop(bone, prop, text=text, slider=True)

    ####################################################
    # UI

    @classmethod
    def parents_component_ui(self, layout, params, parent_type='parents_in', text="", icon=None, use=False, scale=True):
        parents = getattr(params, parent_type)
        if not text:
            text = parent_type.replace("_", " ").capitalize()
        layout.use_property_split = True
        layout.use_property_decorate = False

        if icon:
            layout.label(text=text + " Parents", icon=icon)

        # Copy rotation
        col = layout.column()
        col.row().prop(params, parent_type + '_copy_rotation', text=text + " Rotation")
        if getattr(params, parent_type + '_copy_rotation'):
            r = col.row(align=True)
            r.prop(params, parent_type + '_copy_rotation_default', slider=True)
            r.prop(params, parent_type + '_copy_rotation_panel', text="", icon='OPTIONS')
            layout.separator(factor=0.2)
        
        # Copy scale
        col = layout.column()
        col.row().prop(params, parent_type + '_copy_scale', text=text + " Scale")
        if getattr(params, parent_type + '_copy_scale'):
            r = col.row(align=True)
            r.prop(params, parent_type + '_copy_scale_default', slider=True)
            r.prop(params, parent_type + '_copy_scale_panel', text="", icon='OPTIONS')
        layout.separator(factor=0.2)
        
        # Use
        if use:
            layout.row().prop(params, 'use_' + parent_type)
        if not use or getattr(params, 'use_' + parent_type):

            # Single type
            if len(parents) < 2:
                layout.row().prop(params, parent_type + '_type_single', expand=True)
            
            # Panel switcher
            else:
                layout.use_property_split = False
                layout.row().prop(params, parent_type + '_panel', expand=True)

            # Add parents
            add = layout.operator('pose.rigify_add_bendify_parent', text="Add " + text + " Parent", icon='PLUS')
            add.parent_type = parent_type.upper()

            # Parent loop
            for i, parent in enumerate(parents):
                box = layout.box()
                box.use_property_split = True
                col = box.column()
                r = col.row(align=True)
                r.prop(parent, 'name')
                remove = r.operator('pose.rigify_remove_bendify_parent', text="", icon='CANCEL')
                remove.parent_type = parent_type.upper()
                remove.index = i
                col.row().prop(parent, 'weight', slider=True)
                if scale:
                    col = box.column()
                    col.row().prop(parent, 'scale_offset', toggle=True)
                    if parent.scale_offset:
                        col.row().prop(parent, 'scale_source_x', expand=True)
                        col.row().prop(parent, 'scale_source_y', expand=True)
                        col.row().prop(parent, 'scale_source_z', expand=True)
            
            if not parents:
                layout.label(text="Using Default Parent", icon='INFO')


    @classmethod
    def parents_ui(self, layout, params):
        self.parents_component_ui(layout, params, 'parents_in', "Base")

    ####################################################
    # SETTINGS

    @classmethod
    def add_parameters(self, params):
        super().add_parameters(params)
        params.parents_in = CollectionProperty(type=ArmaConstraintTargets, name="Base Parents")

        params.parents_in_type_single = EnumProperty(
            name="Parenting Type",
            items=[
                ('CHILD_OF', "Child Of", "Child Of"),
                ('ARMATURE', "Armature", "Armature")
            ],
            default='CHILD_OF',
            description="Constraint type for single parenting. Use Armature to follow B-Bones.",
        )

        params.parents_in_panel = EnumProperty(
            name="Parenting Panel",
            items=[
                ('NONE', "No UI", "No UI"),
                ('SWITCH', "Switch", "Switch"),
                ('SLIDER', "Slider", "Slider"),
                ('INDIVIDUAL', "Individual", "Individual")
            ],
            default='NONE',
            description="Property and panel variation to be used for dynamic parenting",
        )

        params.parents_in_copy_rotation = StringProperty(
            name="World Rotation",
            default="",
            description="Copy world rotation from this bone",
        )

        params.parents_in_copy_rotation_default = FloatProperty(
            name="Default",
            default=1.0,
            min=0.0,
            max=1.0,
            description="Default value for world rotation",
        )

        params.parents_in_copy_rotation_panel = BoolProperty(
            name="World Rotation Panel",
            default=False,
            description="Add a panel for world rotation to the UI",
        )

        params.parents_in_copy_scale = StringProperty(
            name="World Scale",
            default="",
            description="Copy world scale from this bone",
        )

        params.parents_in_copy_scale_default = FloatProperty(
            name="Default",
            default=1.0,
            min=0.0,
            max=1.0,
            description="Default value for world scale",
        )

        params.parents_in_copy_scale_panel = BoolProperty(
            name="Copy Scale Panel",
            default=False,
            description="Add a panel for world scale to the UI",
        )

# NEEDS MERGE
class AlignedBendyRig(BendyRig):
    """
    Bendy rig with start and end Y-alignment to other bones
    """

    def initialize(self):
        super().initialize()

        self.align_base = self.params.align_base
        self.align_tip = self.params.align_tip
        self.align_base_axis = self.params.align_base_axis
        self.align_tip_axis = self.params.align_tip_axis
        self.align_base_preserve = self.params.align_base_preserve
        self.align_tip_preserve = self.params.align_tip_preserve

    ####################################################
    # Align

    @stage.apply_bones
    def align_tweak_mch_ends(self):
        mchs = self.attribute_return(['bones', 'mch', 'tweak'])
        if mchs:
            if self.align_base:
                self.align_bone_to_bone_axis(mchs[0], self.align_base, self.align_base_axis, self.align_base_preserve)
            if self.align_tip:
                self.align_bone_to_bone_axis(mchs[-1], self.align_tip, self.align_tip_axis, self.align_tip_preserve)

    @stage.apply_bones
    def align_tweak_ends(self):
        tweaks = self.attribute_return(['bones', 'ctrl', 'tweak'])
        if tweaks:
            if self.align_base:
                self.align_bone_to_bone_axis(tweaks[0], self.align_base, self.align_base_axis, self.align_base_preserve)
            if self.align_tip:
                self.align_bone_to_bone_axis(tweaks[-1], self.align_tip, self.align_tip_axis, self.align_tip_preserve)
        
    ####################################################
    # UI

    @classmethod
    def tweak_align_ui(self, layout, params):
        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.row().prop(params, 'align_base')
        if params.align_base:
            r = layout.row(align=True)
            r.prop(params, 'align_base_axis')
            r.prop(params, 'align_base_preserve', text="")
        
        layout.row().prop(params, 'align_tip')
        if params.align_tip:
            r = layout.row(align=True)
            r.prop(params, 'align_tip_axis')
            r.prop(params, 'align_tip_preserve', text="")

    ####################################################
    # SETTINGS

    @classmethod
    def add_parameters(self, params):
        super().add_parameters(params)

        axes = [
            ('X', "X", "X"),
            ('-X', "-X", "-X"),
            ('Y', "Y", "Y"),
            ('-Y', "-Y", "-Y"),
            ('Z', "Z", "Z"),
            ('-Z', "-Z", "-Z"),
        ]

        preserves = [
            ('X', "X Preserve", "X Preserve"),
            ('Z', "Z Preserve", "Z Preserve"),
        ]

        params.align_base_axis = EnumProperty(
            items=axes,
            name="Axis",
            default='Y',
            description="Orientation guide bone axis to use for base",
        )

        params.align_tip_axis = EnumProperty(
            items=axes,
            name="Axis",
            default='Y',
            description="Orientation guide bone axis to use for tip",
        )

        params.align_base_preserve = EnumProperty(
            items=preserves,
            name="Preserve",
            default='X',
            description="Preserve this axis while re-orienting base",
        )

        params.align_tip_preserve = EnumProperty(
            items=preserves,
            name="Preserve",
            default='Z',
            description="Preserve this axis while re-orienting tip",
        )

        params.align_base = StringProperty(
            name="Base Orientation",
            default="",
            description="Orientation guide bone for base",
        )


        params.align_tip = StringProperty(
            name="Tip Orientation",
            default="",
            description="Orientation guide bone for etipnd",
        )


    @classmethod
    def parameters_ui(self, layout, params):
        self.tweak_align_ui(layout, params)
        super().parameters_ui(layout, params)


class AttachedBendyRig(HandleBendyRig, ScaleOffsetMixin):
    """
    Stretchy rig with armature/child-of constrained start and end handles
    """

    def initialize(self):
        super().initialize()

        self.attach_base_type = self.params.attach_base_type
        self.attach_base = self.params.attach_base
        self.attach_base_scale_offset = self.params.attach_base_scale_offset
        self.attach_base_scale_x = self.params.attach_base_scale_x
        self.attach_base_scale_y = self.params.attach_base_scale_y
        self.attach_base_scale_z = self.params.attach_base_scale_z

        self.attach_tip = self.params.attach_tip
        self.attach_tip_scale_offset = self.params.attach_tip_scale_offset
        self.attach_tip_scale_x = self.params.attach_tip_scale_x
        self.attach_tip_scale_y = self.params.attach_tip_scale_y
        self.attach_tip_scale_z = self.params.attach_tip_scale_z

    ####################################################
    # Tweak chain

    @stage.parent_bones
    def check_attach_base(self):
        if self.attach_base_type == 'PARENT':
            if self.parent_org:
                self.attach_base = self.parent_org
            else:
                raise MetarigError("Bone {}: No parent found".format(self.bones.org[0]))

        elif self.attach_base_type == 'TWEAK':
            parent_tweaks = self.attribute_return(['rigify_parent', 'bones', 'ctrl', 'tweak'])
            if parent_tweaks:
                delta = self.distance(self.bones.mch.attach_base, parent_tweaks[0])
                self.attach_base = parent_tweaks[0]
                for tweak in parent_tweaks:
                    dist = self.distance(self.base_bone, tweak)
                    if dist < delta:
                        delta = dist
                        self.attach_base = tweak
            else:
                raise MetarigError("Bone {}: No tweaks found for parent".format(self.bones.org[0]))

    @stage.parent_bones
    def parent_tweak_chain(self):
        super().parent_tweak_chain()
        tweaks = self.bones.ctrl.tweak
        mchs = self.bones.mch
        ctrls = []
        parents = []
        if self.attach_base:
            ctrls.append(tweaks[0])
            parents.append(mchs.attach_base)
        if self.attach_tip:
            ctrls.append(tweaks[-1])
            parents.append(mchs.attach_tip)
        for ctrl, mch in zip(ctrls, parents):
            self.set_bone_parent(mch, self.root_bone_mch)
            self.set_bone_parent(ctrl, mch)

    @stage.configure_bones
    def rig_tweak_chain(self):
        tweaks = self.bones.ctrl.tweak
        if self.attach_base and self.attach_base_scale_offset:
            self.bone_scale_offset(
                tweaks[0],
                self.attach_base,
                self.attach_base_scale_x,
                self.attach_base_scale_y,
                self.attach_base_scale_z
            )
        if self.attach_tip and self.attach_tip_scale_offset:
            self.bone_scale_offset(
                tweaks[-1],
                self.attach_tip,
                self.attach_tip_scale_x,
                self.attach_tip_scale_y,
                self.attach_tip_scale_z
            )

    ####################################################
    # Tweak MCH chain

    @stage.generate_bones
    def make_tweak_mch_chain(self):
        super().make_tweak_mch_chain()
        mchs = self.bones.mch
        if not self.attach_base_type == 'BONE':
            self.attach_base = 'TMP'
        if self.attribute_return(['bones', 'mch', 'tweak']):
            mchs.attach_base = mchs.tweak[0] if self.attach_base else None
            mchs.attach_tip = mchs.tweak[-1] if self.attach_tip else None
        else:
            orgs = self.bones.org
            mchs.attach_base = self.make_tweak_mch_bone(0, orgs[0]) if self.attach_base else None
            mchs.attach_tip = self.make_tweak_mch_bone(len(orgs), orgs[-1]) if self.attach_tip else None
    
    @stage.parent_bones
    def parent_tweak_mch_chain(self):
        super().parent_tweak_mch_chain()
        mchs = self.bones.mch
        for mch in [mchs.attach_base, mchs.attach_tip]:
            if mch:
                self.set_bone_parent(mch, self.root_bone_mch)  

    @stage.finalize
    def finalize_tweak_mch_chain(self):
        mchs = self.bones.mch
        tweak_mchs = [mchs.attach_base, mchs.attach_tip]
        subtargets = [self.attach_base, self.attach_tip]
        scales = [self.attach_base_scale_offset, self.attach_tip_scale_offset]
        for mch, subtarget, scale in zip(tweak_mchs, subtargets, scales):
            if mch and subtarget:
                self.make_armature_constraint(mch, subtarget, weights_reset=True)
                #if scale:
                #    self.make_constraint(mch, 'COPY_SCALE', self.root_bone)

    ####################################################
    # UI

    @classmethod
    def tweak_attach_component_ui(self, layout, params, attach='base', attach_type=False):
        attach = "attach_" + attach
        attyp = attach + "_type"

        layout.use_property_split = True
        layout.use_property_decorate = False
        col = layout.column()
        if attach_type:
            col.row().prop(params, attyp)
        r = col.row(align=True)
        if attach_type:
            r.enabled = getattr(params, attyp) == 'BONE'
            r.prop(params, attach, text=" ")
        else:
            r.prop(params, attach)
        col = layout.column()
        r = col.row()
        r.prop(params, attach + '_scale_offset', toggle=True)#icon='CON_SIZELIKE')
        r.enabled = getattr(params, attach) is not "" or hasattr(params, attyp) and not getattr(params, attyp) == 'BONE'
        if r.enabled and getattr(params, attach + "_scale_offset"):
            col.row().prop(params, attach + '_scale_x', expand=True)
            col.row().prop(params, attach + '_scale_y', expand=True)
            col.row().prop(params, attach + '_scale_z', expand=True)

    @classmethod
    def tweak_attach_ui(self, layout, params):
        box = layout.box()
        self.tweak_attach_component_ui(box, params, 'base', True)
        box = layout.box()
        self.tweak_attach_component_ui(box, params, 'tip')

    ####################################################
    # SETTINGS

    @classmethod
    def add_parameters(self, params):
        super().add_parameters(params)

        attach_types = [
            ('PARENT', "To Parent", "Connect first tweak to parent"),
            ('TWEAK', "Merge Tweaks", "Merge with closest parent tweak"),
            ('BONE', "Define Bone", "Specify parent for first tweak by name")
        ]

        params.attach_base = StringProperty(
            name="Base Tweak Parent",
            default="",
            description="Set the parent for the first tweak",
        )

        params.attach_base_type = EnumProperty(
            items=attach_types,
            name="Base Tweak Parent",
            default='BONE',
            description="Connection point for the first tweak of the B-Bone chain",
        )

        params.attach_base_scale_offset = BoolProperty(
            name="Offset Scale",
            default=True,
            description="Set scale offset for base tweak",
        )

        params.attach_base_scale_x = EnumProperty(
            items=self.offset_axes,
            name="X Source Axis",
            default='X',
            description="Source axis for X scale base offset",
        )

        params.attach_base_scale_y = EnumProperty(
            items=self.offset_axes,
            name="Y Source Axis",
            default='Y',
            description="Source axis for Y scale base offset",
        )

        params.attach_base_scale_z = EnumProperty(
            items=self.offset_axes,
            name="Z Source Axis",
            default='Z',
            description="Source axis for Z scale base offset",
        )

        params.attach_tip = StringProperty(
            name="Tip Tweak Parent",
            default="",
            description="Set the parent for the last tweak",
        )

        params.attach_tip_type = EnumProperty(
            items=attach_types,
            name="Last Tweak",
            default='BONE',
            description="Connection point for the last tweak of the B-Bone chain",
        )

        params.attach_tip_scale_offset = BoolProperty(
            name="Offset Scale",
            default=True,
            description="Set scale offset for tip tweak",
        )

        params.attach_tip_scale_x = EnumProperty(
            items=self.offset_axes,
            name="X Source Axis",
            default='X',
            description="Source axis for X scale tip offset",
        )

        params.attach_tip_scale_y = EnumProperty(
            items=self.offset_axes,
            name="Y Source Axis",
            default='Y',
            description="Source axis for Y scale tip offset",
        )

        params.attach_tip_scale_z = EnumProperty(
            items=self.offset_axes,
            name="Z Source Axis",
            default='Z',
            description="Source axis for Z scale tip offset",
        )


# Use this OR AttachedBendyRig

class ConnectingBendyRig(AttachedBendyRig):
    """
    Bendy rig that can connect to a (tweak of its) parent.
    """

    def initialize(self):
        super().initialize()

        self.attach_base_connect = self.params.attach_base_connect
        self.attach_base_align = self.params.attach_base_align

        self.attach_tip_connect = self.params.attach_tip_connect
        self.attach_tip_align = self.params.attach_tip_align

    ####################################################
    # Connect all-in-one

    @stage.apply_bones
    def attach_connect_bones(self):
        #orgs = self.bones.org
        mchs = self.bones.mch
        deforms = self.bones.deform
        tweaks = self.bones.ctrl.tweak
        
        if self.attach_base:
            if self.attach_base_connect:
                #bases = [orgs[0], deforms[0], mchs.attach_base, tweaks[0]]
                bases = [deforms[0], mchs.attach_base, tweaks[0]]
                keeps = 1 * [False] + 2 * [True]
                for base, keep in zip(bases, keeps):
                    connect_bone_to_bone(self.obj, base, self.attach_base, keep_length=keep)
                    print(self.attach_base)
            
            if self.attach_base_align:
                for base in [mchs.attach_base, tweaks[0]]:
                    align_bone_orientation(self.obj, base, self.attach_base)
            
            if self.attach_base_connect or self.attach_base_align:
                self.align_tweak_mch_chain()
                self.align_tweak_chain()

        if self.attach_tip:
            if self.attach_tip_connect:
                """
                for tip in [orgs[-1], deforms[-1]]:
                    connect_bone_to_bone(self.obj, tip, tail1=True)
                """
                connect_bone_to_bone(self.obj, deforms[-1], tail1=True)
                for tweak in [mchs.attach_tip, tweaks[-1]]:
                    put_bone_to_bone(self.obj, tweak, self.attach_tip)

            if self.attach_tip_align:
                for tip in [mchs.attach_tip, tweaks[-1]]:
                    align_bone_orientation(self.obj, tip, self.attach_tip)


    ####################################################
    # Tweak chain

    @stage.generate_widgets
    def make_tweak_widgets(self):
        if self.attach_base_type == 'TWEAK' and self.attach_base:
            create_sub_tweak_widget(
                self.obj,
                self.bones.ctrl.tweak[0],
                size=0.1
            )
        super().make_tweak_widgets()

    ####################################################
    # UI

    @classmethod
    def tweak_attach_component_ui(self, layout, params, attach='base', attach_type=False):
        super().tweak_attach_component_ui(layout, params, attach, attach_type)
        attach = "attach_" + attach
        attype = attach + "_type"
        r = layout.row(align=True)
        r.enabled = getattr(params, attach) is not "" or hasattr(params, attype) and not getattr(params, attype) == 'BONE'
        r.prop(params, attach + "_connect", toggle=True)
        r.prop(params, attach + "_align", toggle=True)

    ##############################
    # Settings

    @classmethod
    def add_parameters(self, params):
        super().add_parameters(params)

        params.attach_base_connect = BoolProperty(
            name="Connect",
            default=True,
            description="Move first tweak to its parent",
        )

        params.attach_base_align = BoolProperty(
            name="Align",
            default=True,
            description="Align first tweak to its parent for a smooth curve",
        )

        params.attach_tip_connect = BoolProperty(
            name="Connect",
            default=True,
            description="Move last tweak to its parent",
        )

        params.attach_tip_align = BoolProperty(
            name="Align",
            default=True,
            description="Align last tweak to its parent for a smooth curve",
        )