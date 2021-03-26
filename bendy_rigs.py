from bpy.props import *

from collections.abc import Mapping
from itertools import count

from rigify.base_rig import BaseRig, stage
from rigify.utils.naming import strip_org, make_derived_name
from rigify.utils.misc import map_list
from rigify.utils.layers import ControlLayersOption
from rigify.utils.rig import connected_children_names
from rigify.utils.bones import put_bone, copy_bone_position, align_bone_roll, align_bone_x_axis, align_bone_y_axis
from rigify.utils.widgets_basic import create_sphere_widget

from .props import ArmaConstraintTargets
from .utils.bones import align_bone, align_bone_to_bone_axis, distance, real_bone
from .utils.mechanism import make_armature_constraint
from .utils.misc import threewise_nozip, attribute_return, var_name
from .utils.widgets_bendy import create_sub_tweak_widget, create_simple_arrow_widget


# Rigs


class BendyBoneMixin():
    """
    Bone utilities for Bendy Rigs
    """

    def real_bone(self, bone_name):
        return real_bone(self.obj, bone_name)

    def distance(self, bone_name1, bone_name2, tail=False):
        return distance(self.obj, bone_name1, bone_name2, tail)
    
    def align_bone_to_bone_axis(self, bone_name1, bone_name2, axis='Y', preserve='X'):
        align_bone_to_bone_axis(self.obj, bone_name1, bone_name2, axis, preserve)

    def align_bone(self, bone_name, prev_target, roll_target, next_target, prev_tail=False, next_tail=False):
        align_bone(self.obj, bone_name, prev_target, roll_target, next_target, prev_tail, next_tail)

    def attribute_return(self, attributes, iterable=False):
        return attribute_return(self, attributes, iterable)


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


class BendyRig(BaseRig, BendyBoneMixin):
    """
    Base bendy rig with driven B-Bones
    """

    def find_org_bones(self, bone):
        return [bone.name] + connected_children_names(self.obj, bone.name)

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
        
        self.bbones_copy_properties = self.params.bbones_copy_properties
        self.bbone_segments = self.params.bbones_spine
        self.bbone_easein = self.params.bbones_easein
        self.bbone_easeout = self.params.bbones_easeout
        self.bbone_ease = self.params.bbone_ease
        self.bbone_scale = self.params.bbone_scale

        self.rotation_mode_tweak = self.params.rotation_mode_tweak
        self.org_transform = self.params.org_transform

        self.volume_deform_default = self.params.volume_deform_default
        self.volume_deform_panel = self.params.volume_deform_panel

        self.keep_axis = 'SWING_Y'
        self.root_bone = self.get_bone(self.base_bone).parent.name if self.get_bone(self.base_bone).parent else "root"
        self.default_prop_bone = None

    def parent_bones(self):
        self.rig_parent_bone = self.get_bone_parent(self.bones.org[0])

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
    # B-Bone Utils

    def setup_bbone(
        self,
        bone,
        segments=8,
        easein=1.0,
        easeout=1.0,
        handle_start=None,
        handle_end=None,
        curveinx=0.0,
        curveiny=0.0,
        curveoutx=0.0,
        curveouty=0.0,
        rollin=0.0,
        rollout=0.0,
        use_endroll_as_inroll=False,
        scaleinx=1.0,
        scaleiny=1.0,
        scaleoutx=1.0,
        scaleouty=1.0,
        handle_type_start=None,
        handle_type_end=None
        ):
        bbone = self.get_bone(bone)
        bbone.bbone_segments = segments
        #bbone.bbone_x = bbone_x
        #bbone.bbone_z = bbone_z
        bbone.bbone_curveinx = curveinx
        bbone.bbone_curveiny = curveiny
        bbone.bbone_curveoutx = curveoutx
        bbone.bbone_curveouty = curveouty
        bbone.bbone_rollin = rollin
        bbone.bbone_rollout = rollout
        bbone.use_endroll_as_inroll = use_endroll_as_inroll
        bbone.bbone_scaleinx = scaleinx
        bbone.bbone_scaleiny = scaleiny
        bbone.bbone_scaleoutx = scaleoutx
        bbone.bbone_scaleouty = scaleouty
        bbone.bbone_easein = easein
        bbone.bbone_easeout = easeout
        bbone.bbone_custom_handle_start = self.get_bone(handle_start)
        if handle_type_start:
            bbone.bbone_handle_type_start = handle_type_start
        else:
            bbone.bbone_handle_type_start = 'TANGENT' if handle_start else 'AUTO'
        bbone.bbone_custom_handle_end = self.get_bone(handle_end)
        if handle_type_end:
            bbone.bbone_handle_type_end = handle_type_end
        else:
            bbone.bbone_handle_type_end = 'TANGENT' if handle_start else 'AUTO'

    def copy_bbone(self, bbone, bbone_source, handle_start=None, handle_end=None):
        bbs = self.get_bone(bbone_source)
        self.setup_bbone(
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

    ####################################################
    # Tweak chain

    @stage.generate_bones
    def make_tweak_chain(self):
        orgs = self.bones.org
        self.bones.ctrl.tweak = map_list(self.make_tweak_bone, count(0), orgs + orgs[-1:])
        self.default_prop_bone = self.bones.ctrl.tweak[0]

    def make_tweak_bone(self, i, org):
        name = self.copy_bone(org, 'tweak_' + strip_org(org), parent=False, scale=0.5)

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
        create_sphere_widget(self.obj, tweak)

    ##############################
    # ORG chain

    @stage.parent_bones
    def parent_org_chain(self):
        orgs = self.bones.org
        self.parent_bone_chain(orgs, use_connect=False)
        self.set_bone_parent(orgs[0], self.root_bone)

    @stage.apply_bones
    def bbone_org_chain(self):
        for org in self.bones.org:
            self.setup_bbone(org, 1)
    
    @stage.rig_bones
    def rig_org_chain(self):
        ctrls = self.bones.ctrl
        for args in zip(self.bones.org, self.bones.deform, ctrls.tweak, ctrls.tweak[1:]):
            self.rig_org_bone(*args)
            
    def rig_org_bone(self, org, deform, tweak, next_tweak):
        self.make_constraint(org, 'COPY_TRANSFORMS', deform)
        if self.org_transform == 'TWEAKS':
            self.make_constraint(org, 'COPY_SCALE', tweak, use_y=False, power=0.5, use_offset=True, target_space='LOCAL', owner_space='LOCAL')
            self.make_constraint(org, 'COPY_SCALE', next_tweak, use_y=False, power=0.5, use_offset=True, target_space='LOCAL', owner_space='LOCAL')
        elif self.org_transform == 'TWEAK':
            self.make_constraint(org, 'COPY_SCALE', tweak, use_y=False, use_offset=True, target_space='LOCAL', owner_space='LOCAL')

    ####################################################
    # Deform bones

    @stage.generate_bones
    def make_deform_chain(self):
        self.bones.deform = map_list(self.make_deform_bone, count(0), self.bones.org)

    def make_deform_bone(self, i, org):
        return self.copy_bone(org, make_derived_name(org, 'def'), parent=True, bbone=True)

    @stage.parent_bones
    def parent_deform_chain(self):
        deforms = self.bones.deform
        self.parent_bone_chain(deforms, use_connect=True)
        self.set_bone_parent(deforms[0], self.root_bone)

    @stage.parent_bones
    def bbone_deform_chain(self):
        tweaks = self.bones.ctrl.tweak
        for i, deform, tweak, next_tweak, org in zip(count(0), self.bones.deform, tweaks, tweaks[1:], self.bones.org):
            if self.bbones_copy_properties:
                self.copy_bbone(deform, org)
            else:
                ease_in = 0.0 if i == 0 and not self.bbone_easein else 1.0
                ease_out = 0.0 if i == len(self.bones.deform) - 1 and not self.bbone_easeout else 1.0
                self.setup_bbone(deform, self.bbone_segments, ease_in, ease_out, tweak, next_tweak)

    @stage.rig_bones
    def rig_deform_chain(self):
        ctrls = self.bones.ctrl
        for args in zip(self.bones.deform, ctrls.tweak, ctrls.tweak[1:]):
            self.rig_deform_bone(*args, self.root_bone)
    
    def rig_deform_bone(self, bone, handle_start, handle_end, scale):
        self.make_constraint(bone, 'COPY_LOCATION', handle_start)

        if not self.bbone_handles == 'NONE':
            self.make_constraint(bone, 'COPY_ROTATION', handle_start)
        
        self.make_constraint(bone, 'COPY_SCALE', scale, space='CUSTOM', space_object=self.obj, space_subtarget=self.root_bone)
        
        self.make_constraint(bone, 'DAMPED_TRACK', handle_end)
        stretch = self.make_constraint(bone, 'STRETCH_TO', handle_end)
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
    
    def org_transform_ui(self, layout, params):
        layout.row().prop(params, 'org_transform', text="ORGs")

    def bbones_ui(self, layout, params):
        r = layout.row(align=True)
        r.prop(params, 'bbone_ease', text="Ease Drivers", toggle=True)
        r.prop(params, 'bbone_scale', text="Scale Drivers", toggle=True)
        layout.row().prop(params, 'bbones_copy_properties')
        if not params.bbones_copy_properties:
            layout.row().prop(params, 'bbones_spine')
            r = layout.row(align=True)
            r.prop(params, 'bbones_easein', text="Ease In", toggle=True)
            r.prop(params, 'bbones_easeout', text="Ease Out", toggle=True)

    def volume_ui(self, layout, params):
        r = layout.row(align=True)
        r.prop(params, 'volume_deform_default', slider=True)
        r.prop(params, 'volume_deform_panel', text="", icon='OPTIONS')

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
        params.show_advanced = BoolProperty(
            name="Show Advanced Settings",
            default=False,
            description="Show more settings to fine-tune the rig"
        )

        params.bbones_copy_properties = BoolProperty(
            name="Individual B-Bone Properties",
            default=False,
            description="Copy original B-Bone settings per bone"
        )

        params.bbones_spine = IntProperty(
            name="B-Bone Segments",
            default=8,
            min=1,
            max=32,
            description="Number of B-Bone segments"
        )

        params.bbones_easein = BoolProperty(
            name="B-Bone Ease In",
            default=True,
            description="Deform easing in for first bone of chain"
        )

        params.bbones_easeout = BoolProperty(
            name="B-Bone Ease Out",
            default=True,
            description="Deform easing out for last bone of chain"
        )

        params.bbone_ease = BoolProperty(
            name="Ease Drivers",
            default=True,
            description="B-Bone easing driven by tweak"
        )

        params.bbone_scale = BoolProperty(
            name="Scale Drivers",
            default=True,
            description="B-Bone scaling driven by tweak"
        )

        params.rotation_mode_tweak = EnumProperty(
            name="Default Tweak Controller Rotation Mode",
            items=self.rotation_modes,
            default='ZXY',
            description="Default rotation mode for tweak control bones"
        )

        params.org_transform = EnumProperty(
            name="ORG Transform base",
            items=(
                ('DEF', "Deforms", "Deforms"),
                ('TWEAK', "Single Tweak", "Single Tweak"),
                ('TWEAKS', "Between Tweaks", "BetweenTweaks")
            ),
            default='DEF',
            description="Source of ORG transformation; useful to determine children's behaviour"
        )

        params.volume_deform_default = FloatProperty(
            name="Deform Volume Variation Default",
            default=1.0,
            soft_min=0.0,
            soft_max=1.0,
            description="Default value for deform bone chain stretch volume variation"
        )

        params.volume_deform_panel = BoolProperty(
            name="Deform Volume Variation Panel",
            default=False,
            description="Add panel to control volume variation to the UI"
        )

    @classmethod
    def parameters_ui(self, layout, params):
        self.org_transform_ui(self, layout, params)
        self.bbones_ui(self, layout, params)
        self.volume_ui(self, layout, params)


# Advanced variations, mixable

class HandleBendyRig(BendyRig):
    """
    Bendy rig with prerequisites for autmatic handles
    """

    def initialize(self):
        super().initialize()
        self.bbone_handles = self.params.bbone_handles

    ####################################################
    # Tweak Targets

    def check_mch_parents(self):
        '''Return array of parents for tweak MCHs'''
        return [self.root_bone] * (len(self.bones.org) + 1)

    def check_mch_targets(self):
        '''Return array of triple target lists (previous, current & next)'''
        return threewise_nozip(self.check_mch_parents())
    
    ####################################################
    # Tweak MCH chain

    @stage.generate_bones
    def make_tweak_mch_chain(self):
        if self.bbone_handles == 'TANGENT':
            orgs = self.bones.org
            self.bones.mch.tweak = map_list(self.make_tweak_mch_bone, count(0), orgs + orgs[-1:])

    def make_tweak_mch_bone(self, i, org):
        name = make_derived_name(org, 'mch', '_tweak')
        name = self.copy_bone(org, name, parent=False, scale=0.5)

        if i == len(self.bones.org):
            put_bone(self.obj, name, self.get_bone(org).tail)
        
        return name

    @stage.parent_bones
    def parent_tweak_mch_chain(self):
        if self.bbone_handles == 'TANGENT':
            mchs = self.bones.mch.tweak
            parents = self.check_mch_parents()

            for mch, parent in zip(mchs, parents):
                self.set_bone_parent(mch, parent, inherit_scale='FIX_SHEAR')

    @stage.parent_bones
    def align_tweak_mch_chain(self):
        if self.bbone_handles == 'TANGENT':
            mchs = self.bones.mch.tweak
            targets = self.check_mch_targets()
            
            for tweak, p, c, n in zip(mchs, *targets):
                self.align_bone(tweak, p, c, n, next_tail=True if c == n else False)
    
    @stage.rig_bones
    def rig_tweak_mch_chain(self):
        if self.bbone_handles == 'TANGENT':
            mchs = self.bones.mch
            parents = self.check_mch_parents()
            targets = self.check_mch_targets()

            for args in zip(count(0), mchs.tweak, parents, *targets):
                self.rig_tweak_mch_bone(*args)

    def rig_tweak_mch_bone(self, i, mch, scale_bone, prev_target, curr_target, next_target):
        if prev_target and next_target:
            self.make_constraint(mch, 'COPY_LOCATION', prev_target)
            #self.make_constraint(mch, 'DAMPED_TRACK', next_target, head_tail=1 if curr_target == next_target else 0)
            self.make_constraint(mch, 'STRETCH_TO', next_target, head_tail=1 if curr_target == next_target else 0, bulge=0, volume='NO_VOLUME', keep_axis=self.keep_axis)
            self.make_constraint(mch, 'COPY_LOCATION', curr_target)
        self.make_constraint(mch, 'COPY_SCALE', scale_bone, space='CUSTOM', space_object=self.obj, space_subtarget=self.root_bone)#, use_make_uniform=True)

    ####################################################
    # Tweak chain

    @stage.parent_bones
    def parent_tweak_chain(self):
        tweaks = self.bones.ctrl.tweak
        parents = self.bones.mch.tweak if self.bbone_handles == 'TANGENT' else self.check_mch_parents()
        inherit = {
            'NONE': 'AVERAGE',
            'Y': 'FIX_SHEAR',
            'TANGENT': 'FULL',
        }
        for tweak, parent in zip(tweaks, parents):
            self.set_bone_parent(tweak, parent, inherit_scale=inherit[self.bbone_handles])

    @stage.parent_bones
    def align_tweak_chain(self):
        if self.bbone_handles == 'TANGENT':
            tweaks = self.bones.ctrl.tweak
            targets = self.check_mch_targets()
            
            for tweak, p, c, n in zip(tweaks, *targets):
                self.align_bone(tweak, p, c, n, next_tail=True if c == n else False)
    
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
        tweaks = self.bones.ctrl.tweak
        for i, deform, tweak, next_tweak, org in zip(count(0), self.bones.deform, tweaks, tweaks[1:], self.bones.org):
            handle_start = tweak if self.bbone_handles == 'TANGENT' else None
            handle_end = next_tweak if self.bbone_handles == 'TANGENT' else None
            if self.bbones_copy_properties:
                self.copy_bbone(deform, org, handle_start, handle_end)
            else:
                ease_in = 0.0 if i == 0 and not self.bbone_easein else 1.0
                ease_out = 0.0 if i == len(self.bones.deform) - 1 and not self.bbone_easeout else 1.0
                self.setup_bbone(deform, self.bbone_segments, ease_in, ease_out, handle_start, handle_end)
            

    ####################################################
    # UI

    def rotation_mode_tweak_ui(self, layout, params):
        layout.row().prop(params, 'rotation_mode_tweak', text="Tweaks")

    def bbones_ui(self, layout, params):
        layout.row().prop(params, 'bbone_handles', text="Handles", toggle=True)
        super().bbones_ui(self, layout, params)

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
            description="B-Bone handles alignment"
        )

    @classmethod
    def parameters_ui(self, layout, params):
        self.rotation_mode_tweak_ui(self, layout, params)
        super().parameters_ui(layout, params)


class ComplexBendyRig(BendyRig):
    """
    Bendy rig with copied stretch constraints for better non-uniform scalability
    """

    def initialize(self):
        super().initialize()

        self.complex_stretch = self.params.complex_stretch
    
    ####################################################
    # Deform MCH

    @stage.generate_bones
    def make_deform_mch_chain(self):
        if self.complex_stretch:
            self.bones.mch.deform = map_list(self.make_deform_mch_bone, count(0), self.bones.org)

    def make_deform_mch_bone(self, i, org):
        name = self.copy_bone(org, make_derived_name(org, 'mch', "_deform"), parent=True)
        return name

    @stage.parent_bones
    def parent_deform_mch_chain(self):
        if self.complex_stretch:
            for mch in self.bones.mch.deform:
                self.set_bone_parent(mch, self.root_bone)

    @stage.apply_bones
    def apply_deform_mch_chain(self):
        if self.complex_stretch:
            for deform, mch in zip(self.bones.deform, self.bones.mch.deform):
                copy_bone_position(self.obj, deform, mch)

    @stage.rig_bones
    def rig_deform_mch_chain(self):
        if self.complex_stretch:
            ctrls = self.bones.ctrl
            for args in zip(count(0), self.bones.mch.deform, ctrls.tweak, ctrls.tweak[1:]):
                self.rig_deform_mch_bone(*args)

    def rig_deform_mch_bone(self, i, bone, handle_start, handle_end, scale=None):
        self.make_constraint(bone, 'COPY_LOCATION', handle_start)
        if scale:
            self.make_constraint(bone, 'COPY_SCALE', scale)
        #self.make_constraint(bone, 'DAMPED_TRACK', handle_end)
        stretch = self.make_constraint(bone, 'STRETCH_TO', handle_end)
        self.make_driver(stretch, 'bulge', variables=[(self.default_prop_bone, 'volume_deform')])

    ####################################################
    # Deform bones

    @stage.rig_bones
    def rig_deform_chain(self):
        if self.complex_stretch:
            ctrls = self.bones.ctrl
            for args in zip(self.bones.deform, ctrls.tweak, ctrls.tweak[1:], self.bones.mch.deform):
                self.rig_deform_bone(*args)
        else:
            super().rig_deform_chain()

    def rig_deform_bone(self, bone, handle_start, handle_end, scale):
        if self.complex_stretch:
            self.make_constraint(bone, 'COPY_LOCATION', handle_start)
            if not self.bbone_handles == 'NONE':
                self.make_constraint(bone, 'COPY_ROTATION', handle_start, space='CUSTOM', space_object=self.obj, space_subtarget=self.root_bone)
            self.make_constraint(bone, 'DAMPED_TRACK', handle_end)
            self.make_constraint(bone, 'COPY_SCALE', scale)  
        else:
            super().rig_deform_bone(bone, handle_start, handle_end, scale)

    ####################################################
    # UI

    def complex_stretch_ui(self, layout, params):
        layout.row().prop(params, "complex_stretch", toggle=True)

    ####################################################
    # SETTINGS

    @classmethod
    def add_parameters(self, params):
        super().add_parameters(params)

        params.complex_stretch = BoolProperty(
            name="Complex Stretch Mechanics",
            description="Additional mechanical layer to separate stretch matrix and enable better non-uniform scaling at cost of additional complexity and non-standard hierarchy; worse export compatibiliy",
            default=False
            )

    @classmethod
    def parameters_ui(self, layout, params):
        self.complex_stretch_ui(self, layout, params)
        super().parameters_ui(layout, params)


class AlignedBendyRig(BendyRig):
    """
    Bendy rig with start and end Y-alignment to other bones
    """

    def initialize(self):
        super().initialize()

        self.align_y_start = self.params.align_y_start
        self.align_y_end = self.params.align_y_end
        self.align_y_start_axis = self.params.align_y_start_axis
        self.align_y_end_axis = self.params.align_y_end_axis
        self.align_y_start_preserve = self.params.align_y_start_preserve
        self.align_y_end_preserve = self.params.align_y_end_preserve

    ####################################################
    # Align

    @stage.apply_bones
    def align_tweak_mch_ends(self):
        mchs = self.attribute_return(['bones', 'mch', 'tweak'])
        if mchs:
            if self.real_bone(self.align_y_start):
                self.align_bone_to_bone_axis(mchs[0], self.align_y_start, self.align_y_start_axis, self.align_y_start_preserve)
            if self.real_bone(self.align_y_end):
                self.align_bone_to_bone_axis(mchs[-1], self.align_y_end, self.align_y_end_axis, self.align_y_end_preserve)

    @stage.apply_bones
    def align_tweak_ends(self):
        tweaks = self.attribute_return(['bones', 'ctrl', 'tweak'])
        if tweaks:
            if self.real_bone(self.align_y_start):
                self.align_bone_to_bone_axis(tweaks[0], self.align_y_start, self.align_y_start_axis, self.align_y_start_preserve)
            if self.real_bone(self.align_y_end):
                self.align_bone_to_bone_axis(tweaks[-1], self.align_y_end, self.align_y_end_axis, self.align_y_end_preserve)
        
    ####################################################
    # UI

    def align_ui(self, layout, params):
        layout.row().prop(params, 'align_y_start')
        if params.align_y_start:
            r = layout.row(align=True)
            r.prop(params, 'align_y_start_axis')
            r.prop(params, 'align_y_start_preserve', text="")
        
        layout.row().prop(params, 'align_y_end')
        if params.align_y_end:
            r = layout.row(align=True)
            r.prop(params, 'align_y_end_axis')
            r.prop(params, 'align_y_end_preserve', text="")

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

        params.align_y_start_axis = EnumProperty(
            items=axes,
            name="Axis",
            default='Y',
            description="Orientation guide bone axis to use for start"
        )

        params.align_y_end_axis = EnumProperty(
            items=axes,
            name="Axis",
            default='Y',
            description="Orientation guide bone axis to use for end"
        )

        params.align_y_start_preserve = EnumProperty(
            items=preserves,
            name="Preserve",
            default='X',
            description="Preserve this axis while re-orienting start"
        )

        params.align_y_end_preserve = EnumProperty(
            items=preserves,
            name="Preserve",
            default='Z',
            description="Preserve this axis while re-orienting end"
        )

        params.align_y_start = StringProperty(
            name="Start Orientation",
            default="",
            description="Orientation guide bone for start"
        )


        params.align_y_end = StringProperty(
            name="End Orientation",
            default="",
            description="Orientation guide bone for end"
        )


    @classmethod
    def parameters_ui(self, layout, params):
        self.align_ui(self, layout, params)
        super().parameters_ui(layout, params)


class AttachedBendyRig(HandleBendyRig, ScaleOffsetMixin):
    """
    Stretchy rig with armature constrained start and end handles
    """

    def initialize(self):
        super().initialize()

        self.parents_base = self.params.parents_base
        self.parents_tip = self.params.parents_tip

        self.base_use_current_location = self.params.base_use_current_location
        self.tip_use_current_location = self.params.tip_use_current_location

    ##############################
    # Controls & MCHs

    @stage.configure_bones
    def offset_scale_tweaks(self):
        tweaks = self.bones.ctrl.tweak
        for parent_base in self.parents_base:
            if self.real_bone(parent_base.name) and parent_base.scale_offset:
                self.bone_scale_offset(
                    tweaks[0],
                    parent_base.name,
                    parent_base.scale_source_x,
                    parent_base.scale_source_y,
                    parent_base.scale_source_z
                )
        for parent_tip in self.parents_tip:
            if self.real_bone(parent_tip.name) and parent_tip.scale_offset:
                self.bone_scale_offset(
                    tweaks[-1],
                    parent_tip.name,
                    parent_tip.scale_source_x,
                    parent_tip.scale_source_y,
                    parent_tip.scale_source_z
                )

    @stage.rig_bones
    def arma_constraint_tweak_mchs(self):
        mchs = self.bones.mch
        tweak_mchs = [mchs.base, mchs.tip]
        parent_lists = [self.parents_base, self.parents_tip]
        current_locs = [self.base_use_current_location, self.tip_use_current_location]

        for mch, parent_list, current_loc in zip(tweak_mchs, parent_lists, current_locs):
            if mch:
                for parent in parent_list:
                    if self.real_bone(parent.name):
                        make_armature_constraint(self.obj, self.get_bone(mch), [subtarget])
                        if scale:
                            self.make_constraint(mch, 'COPY_SCALE', self.root_bone)

    @stage.apply_bones
    def reparent_tweak_mchs_tweaks(self):
        tweaks = self.bones.ctrl.tweak
        ctrls = [tweaks[0], tweaks[-1]]
        mchs = self.bones.mch
        mchs_arma = [mchs.base, mchs.tip]
        checks = [self.base, self.tip]
        for mch, ctrl, check in zip(mchs_arma, ctrls, checks):
            if mch and self.real_bone(check):
                self.get_bone(mch).parent = None
                self.set_bone_parent(ctrl, mch)

    ####################################################
    # Tweak MCH chain

    @stage.generate_bones
    def make_tweak_mch_chain(self):
        mchs = self.bones.mch
        if self.attribute_return(['bbone_handles']) == 'TANGENT':
            super().make_tweak_mch_chain()
            mchs.base = mchs.tweak[0]
            mchs.tip = mchs.tweak[-1]
        else:
            orgs = self.bones.org
            if self.base:
                mchs.base = self.make_tweak_mch_bone(0, orgs[0])
            else:
                mchs.base = None
            if self.tip:
                mchs.tip = self.make_tweak_mch_bone(len(self.bones.org), orgs[-1])
            else:
                mchs.tip = None

    ####################################################
    # UI

    def attached_ui(self, layout, params, parent_type='parents_base'):
        box = layout.box()
        for parent in getattr(self, parent_type):
            r = box.row(align=True)
            r.prop(parent, 'name')
            r.prop(parent, 'scale_offset', text="", icon='CON_SIZELIKE')
            if parent.scale_offset:
                r = layout.row()
                r.prop(params, 'scale_source_x', text="X")
                r.prop(params, 'scale_source_y', text="Y")
                r.prop(params, 'scale_source_z', text="Z")
        box.operator('pose.rigify_add_bendify_parent', text = "+ " + parent_type.replace("parents_", "").capitalize())

    def parents_ui(self, layout, params):
        col = layout.column()
        self.attached_ui(self, col, params, 'parents_base')
        self.attached_ui(self, col, params, 'parents_tip')

    ####################################################
    # SETTINGS

    @classmethod
    def add_parameters(self, params):
        super().add_parameters(params)

        params.parents_base = CollectionProperty(type=ArmaConstraintTargets, name="Base Parents")
        #params.parents_curve = CollectionProperty(type=ArmaConstraintTargets, name="Curve Parents")
        params.parents_tip = CollectionProperty(type=ArmaConstraintTargets, name="Tip Parents")

        params.base_use_current_location = BoolProperty(
            name="Base Current Location",
            default=False,
            description="Use the current bone location for the chain base"
        )

        params.tip_use_current_location = BoolProperty(
            name="Tip Current Location",
            default=False,
            description="Use the current bone location for the chain tip"
        )

# Use this OR "Attached"

class ConnectingBendyRig(AttachedBendyRig):
    """
    Bendy rig that can connect to a (tweak of its) parent, as well as attach its tip to another bone.
    """

    def initialize(self):
        super().initialize()

        self.base_type = self.params.base_type
        if self.params.base_type == 'PARENT' or self.params.base_type == 'TWEAK':
            self.base = "TMP_PLACEHOLDER"
        self.base_connect = self.params.base_connect
        self.base_align = self.params.base_align

        self.base_parent = self.get_bone_parent(self.base_bone)

    ####################################################
    # Control chain

    def connect_base(self, bone_name, connect, x_axis, keep_length=False):
        bone = self.get_bone(bone_name)
        length = bone.length
        bone.head = connect
        align_bone_x_axis(self.obj, bone_name, x_axis)
        if keep_length:
            bone.length = length

    def align_base(self, bone_name, align, roll):
        align_bone_y_axis(self.obj, bone_name, align)
        align_bone_roll(self.obj, bone_name, roll)

    @stage.parent_bones
    def prepare_connection(self):
        '''Check if connecting parents exist and move tweaks'''
        if not self.base_type == 'NONE':
            base_bone = self.get_bone(self.base_bone)
            base_mch = self.bones.mch.base
            base_tweak = self.bones.ctrl.tweak[0]
        
            x_axis = base_bone.x_axis
            connect = None
            align = None

            # Incoming tweak
            parent_tweaks = self.attribute_return(['rigify_parent', 'bones', 'ctrl', 'tweak'])
            if self.base_type == 'TWEAK' and parent_tweaks:
                delta = self.distance(self.base_bone, parent_tweaks[0])
                self.base = parent_tweaks[0]
                for tweak in parent_tweaks:
                    dist = self.distance(self.base_bone, tweak)
                    if dist < delta:
                        delta = dist
                        self.base = tweak
                bone_in = self.get_bone(self.base)

                connect = bone_in.head
                if self.base == parent_tweaks[0]:
                    align = bone_in.head - bone_in.tail
                elif self.base == parent_tweaks[-1]:
                    align = bone_in.tail - bone_in.head
                roll = self.base
            
            # Incoming parent
            elif self.base_type == 'PARENT' and self.base_parent:
                self.base = self.base_parent
                bone_in = self.get_bone(self.base)
                d_head = (base_bone.head - bone_in.head).length
                d_tail = (base_bone.head - bone_in.tail).length
                head = True if d_head < d_tail else False

                connect = bone_in.head if head else bone_in.tail
                align = bone_in.head - bone_in.tail if head else bone_in.tail - bone_in.head
                roll = self.base_parent

            # Incoming bone
            elif self.base_type == 'BONE' and self.real_bone(self.base):
                bone_in = self.get_bone(self.base)

                connect = bone_in.head
                roll = self.base
                align = bone_in.tail - bone_in.head

            # No match
            else:
                error = "CONNECTING ERROR: {org} couldn't connect to {type}: {base}. Skipping.".format(
                    org=self.base_bone,
                    type=self.base_type,
                    base=self.base
                )
                print(error)
                self.base = None
                self.base_type == 'NONE'

            # Connect
            if connect:
                if self.attribute_return(['bones', 'deform']):
                    self.connect_base(self.bones.deform[0], connect, x_axis)
                self.connect_base(base_tweak, connect, x_axis, True)
                self.connect_base(base_mch, connect, x_axis, True)
                if not self.org_transform == 'FK':
                    self.connect_base(self.base_bone, connect, x_axis)

            # Align
            if align:
                self.align_base(base_mch, align, roll)
                self.align_base(base_tweak, align, roll)

    ####################################################
    # Tweak chain

    @stage.generate_widgets
    def make_tweak_widgets(self):
        if self.base_type == 'TWEAK' and self.real_bone(self.base):
            create_sub_tweak_widget(
                self.obj,
                self.bones.ctrl.tweak[0],
                size=0.25
            )
        super().make_tweak_widgets()

    ####################################################
    # Deform chain

    @stage.parent_bones
    def align_first_deform(self):
        if self.bones.deform and self.real_bone(self.base) and self.base_align:
            first_def = self.get_bone(self.bones.deform[0])
            first_tweak = self.get_bone(self.bones.ctrl.tweak[0])
            first_def.bbone_handle_type_start = 'TANGENT'
            first_def.bbone_custom_handle_start = first_tweak

    ####################################################
    # UI

    def base_ui(self, layout, params):
        r = layout.row(align=True)
        r.prop(params, 'base_type')
        if params.base_type == 'BONE':
            r = layout.row(align=True)
            r.prop(params, 'base')
        if not params.base_type == 'NONE':
            r = layout.row(align=True)
            #if not params.base_type == 'TWEAK':
            r.prop(params, 'base_connect', toggle=True)
            r.prop(params, 'base_align', toggle=True)
            r.prop(params, 'base_scale_offset', text="", icon='CON_SIZELIKE')
            if params.base_scale_offset:
                r = layout.row()
                r.prop(params, 'base_scale_x', text="X")
                r.prop(params, 'base_scale_y', text="Y")
                r.prop(params, 'base_scale_z', text="Z")

    ##############################
    # Settings

    @classmethod
    def add_parameters(self, params):
        super().add_parameters(params)

        params.base_type = EnumProperty(
            items=[
                ('NONE', "Default", "Default"),
                ('PARENT', "To Parent", "Connect first tweak to parent"),
                ('TWEAK', "Merge Tweaks", "Merge with closest parent tweak"),
                ('BONE', "Define Bone", "Specify parent for first tweak by name"),
            ],
            name="First Tweak",
            default='NONE',
            description="Connection point for the first tweak of the B-Bone chain"
        )

        params.base_connect = BoolProperty(
            name="Connect First",
            default=True,
            description="Move first tweak to its parent"
        )

        params.base_align = BoolProperty(
            name="Align First",
            default=True,
            description="Align first tweak to its parent for a smooth curve"
        )