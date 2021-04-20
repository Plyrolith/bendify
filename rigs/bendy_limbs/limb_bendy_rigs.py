from bpy.props import *

from rigify.utils.bones import set_bone_widget_transform
from rigify.utils.layers import ControlLayersOption
from rigify.utils.misc import pairwise_nozip, padnone
from rigify.utils.naming import make_derived_name, strip_org
from rigify.base_rig import stage
from rigify.rigs.limbs.limb_rigs import BaseLimbRig

from ...utils.bones import align_bone_between_bones

from itertools import count


class BaseLimbBendyRig(BaseLimbRig):
    """Common base for bendy limb rigs."""

    ####################################################
    # BONES
    #
    # org:
    #   main[]:
    #     Main ORG bone chain
    # ctrl:
    #   master:
    #     Main property control.
    #   fk[]:
    #     FK control chain.
    #   tweak[]:
    #     Tweak control chain.
    #   ik_base, ik_pole, ik
    #     IK controls
    #   ik_vispole
    #     IK pole visualization.
    #   ik_pivot
    #     Custom IK pivot (optional).
    # mch:
    #   master:
    #     Parent of the master control.
    #   follow:
    #     FK follow behavior.
    #   fk[]:
    #     FK chain parents (or None)
    #   ik_pivot
    #     Custom IK pivot result (optional).
    #   ik_stretch
    #     IK stretch switch implementation.
    #   ik_target
    #     Corrected target position.
    #   ik_end
    #     End of the IK chain: [ik_base, ik_end]
    # deform[]:
    #   DEF bones
    #
    ####################################################

    props_options = {'LIBRARY_EDITABLE'}

    def initialize(self):
        # Bbone segments
        super().initialize()
        self.rotation_mode_ik = self.params.rotation_mode_ik
        self.rotation_mode_tweak = self.params.rotation_mode_tweak
        self.tweak_align_default = self.params.tweak_align_default
        self.tweak_align_panel = self.params.tweak_align_panel
        self.ease_in = self.params.ease_in
        self.ease_joints = self.params.ease_joints
        self.ease_out = self.params.ease_out
        self.volume_deform_default = self.params.limb_volume_deform_default
        self.volume_deform_panel = self.params.limb_volume_deform_panel
        self.keep_axis = 'SWING_Y'

    ##############################
    # Utilities

    def check_entry_targets(self, entry):
        '''Return ORG triple (previous, current & next) based on entry '''
        p = ([ s for s in self.segment_table_full if s.org_idx == entry.org_idx - 1 ][0].org)
        c = ([ s for s in self.segment_table_full if s.org_idx == entry.org_idx][0].org)
        n = ([ s for s in self.segment_table_full if s.org_idx == entry.org_idx + 1 ][0].org)
        return p, c, n

    ####################################################
    # Master control

    @stage.generate_bones
    def make_master_control(self):
        org = self.bones.org.main[0]
        self.bones.ctrl.master = name = self.copy_bone(org, make_derived_name(org, 'ctrl', '_parent'), scale=1/4)
        self.get_bone(name).roll = 0
        self.prop_bone = self.bones.ctrl.master

    @stage.parent_bones
    def parent_master_control(self):
        self.set_bone_parent(self.bones.ctrl.master, self.bones.mch.follow)

    @stage.rig_bones
    def rig_master_control(self):
        self.make_property(self.prop_bone, 'align_joint_tweaks', default=float(self.tweak_align_default))
        self.make_property(
            self.prop_bone,
            'volume_deform',
            default=self.volume_deform_default,
            max=100.0,
            soft_min=0.0,
            soft_max=max(self.volume_deform_default, 1.0),
            description='Volume variation for DEF bones'
        )
        
        panel = self.script.panel_with_selected_check(self, self.bones.ctrl.flatten())

        if self.tweak_align_panel:
            panel.custom_prop(
                self.prop_bone,
                'align_joint_tweaks',
                text=strip_org(self.base_bone) + ' Joint Tweaks Align',
                slider=True
            )

        if self.volume_deform_panel:
            panel.custom_prop(
                self.prop_bone,
                'volume_deform',
                text=strip_org(self.base_bone) + ' Deform Volume Variation',
                slider=True
            )

    @stage.configure_bones
    def configure_master_control(self):
        '''Unlocked master control scale'''
        super().configure_master_control()
        bone = self.get_bone(self.bones.ctrl.master)
        bone.lock_scale = (False, False, False)
    
    @stage.generate_widgets
    def make_master_control_widget(self):
        '''Set widget transform to first ORG'''
        super().make_master_control_widget()
        set_bone_widget_transform(self.obj, self.bones.ctrl.master, self.bones.org.main[0])

    ####################################################
    # IK controls

    @stage.configure_bones
    def configure_ik_controls(self):
        super().configure_ik_controls()
        ik = self.get_bone(self.bones.ctrl.ik)
        ik.rotation_mode = self.rotation_mode_ik

    ####################################################
    # FK control chain

    def parent_fk_control_bone(self, i, ctrl, prev, org, parent_mch):
        '''Disconnected FK control bones'''
        if parent_mch:
            self.set_bone_parent(ctrl, parent_mch)
        else:
            self.set_bone_parent(ctrl, prev)

    def configure_fk_control_bone(self, i, ctrl, org):
        # Unlocked FK control locations
        self.copy_bone_properties(org, ctrl)

    ####################################################
    # ORG chain

    @stage.parent_bones
    def parent_org_chain(self):
        '''Disconnect ALL org bones'''
        orgs = self.bones.org.main
        for org in orgs:
            self.get_bone(org).use_connect = False

    ####################################################
    # Tweak control chain

    @stage.parent_bones
    def parent_tweak_chain(self):
        for args in zip(count(0), self.bones.ctrl.tweak, self.bones.mch.tweak, self.segment_table_tweak):
            self.parent_tweak_bone(*args)

    def parent_tweak_bone(self, i, tweak, mch, entry):
        self.set_bone_parent(tweak, mch)
        if not i == 0 and entry.seg_idx == 0:
            p, c, n = self.check_entry_targets(entry)
            align_bone_between_bones(self.obj, tweak, p, c, n)

    def rig_tweak_bone(self, i, tweak, entry):
        super().rig_tweak_mch_bone(i, tweak, entry)
        if not i == 0 and entry.seg_idx == 0:
            p, c, n = self.check_entry_targets(entry)
            align_bone_between_bones(self.obj, tweak, p, c, n)

    def configure_tweak_bone(self, i, tweak, entry):
        '''Completely unlocked tweak'''
        tweak_pb = self.get_bone(tweak)
        tweak_pb.rotation_mode = self.rotation_mode_tweak

    ####################################################
    # Tweak MCH chain

    def parent_tweak_mch_bone(self, i, tweak, entry):
        super().parent_tweak_mch_bone(i, tweak, entry)
        if not i == 0 and entry.seg_idx == 0:
            p, c, n = self.check_entry_targets(entry)
            align_bone_between_bones(self.obj, tweak, p, c, n)

    @stage.rig_bones
    def rig_tweak_mch_chain(self):
        for args in zip(count(0), self.bones.mch.tweak, self.segment_table_tweak):
            self.rig_tweak_mch_bone(*args)

    def rig_tweak_mch_bone(self, i, tweak, entry):
        '''Removed mechanics, only copy scale'''
        if not i == 0 and entry.seg_idx == 0:
            prev_org = ([ s for s in self.segment_table_full if s.org_idx == entry.org_idx - 1 ][0].org)
            next_org = ([ s for s in self.segment_table_full if s.org_idx == entry.org_idx + 1 ][0].org)
            self.make_constraint(tweak, 'COPY_LOCATION', prev_org)
            align = self.make_constraint(tweak, 'STRETCH_TO', next_org, bulge=0, volume='NO_VOLUME', keep_axis=self.keep_axis)
            self.make_driver(align, 'influence', variables=[(self.prop_bone, 'align_joint_tweaks')])
            self.make_constraint(tweak, 'COPY_LOCATION', entry.org)
        self.make_constraint(tweak, 'COPY_SCALE', self.bones.ctrl.master, use_make_uniform=True)

    ####################################################
    # Deform chain
    
    @stage.parent_bones
    def parent_deform_chain(self):
        self.set_bone_parent(self.bones.deform[0], self.rig_parent_bone)
        self.parent_bone_chain(self.bones.deform)

    @stage.parent_bones
    def bbone_deform_chain(self):
        '''(New) ease settings on edit bones need to bo set in parenting stage'''
        tweaks = pairwise_nozip(padnone(self.bones.ctrl.tweak))
        entries = pairwise_nozip(padnone(self.segment_table_full))

        for args in zip(count(0), self.bones.deform, *tweaks, *entries):
            self.bbone_deform_bone(*args)
        
    def bbone_deform_bone(self, i, deform, tweak, next_tweak, entry, next_entry):
        '''Sub loop function for bbone easing'''
        pbone = self.get_bone(deform)
        pbone.bbone_handle_type_start = 'TANGENT'
        pbone.bbone_handle_type_end = 'TANGENT'
        pbone.bbone_custom_handle_start = self.get_bone(tweak)
        pbone.bbone_custom_handle_end = self.get_bone(next_tweak)
        #pbone.bbone_easein = 1.0 if entry.seg_idx and i > 0 else self.joints_ease
        #pbone.bbone_easeout = 1.0 if next_entry and next_entry.seg_idx else self.joints_ease

        if not entry.seg_idx is None:
            if entry.seg_idx == 0:
                if entry.org_idx == 0:
                    pbone.bbone_easein = self.ease_in
                else:
                    pbone.bbone_easein = self.ease_joints
            else:
                pbone.bbone_easein = 1.0

        if next_entry:
            if not next_entry.seg_idx is None:
                if next_entry.org_idx == entry.org_idx:
                    pbone.bbone_easeout = 1.0
                else:
                    pbone.bbone_easeout = self.ease_joints
            else:
                pbone.bbone_easeout = self.ease_out


        
    def rig_deform_bone(self, i, deform, entry, next_entry, tweak, next_tweak):
        '''Added copy scale constraint and bendy driver creation, excluded last deform segment'''
        if tweak and not i == len(self.bones.deform) - 1:
            self.make_constraint(deform, 'COPY_TRANSFORMS', tweak)
            self.make_constraint(deform, 'COPY_SCALE', self.bones.ctrl.master)
            if next_tweak:
                self.make_constraint(deform, 'DAMPED_TRACK', next_tweak)

                # Stretch
                stretch = self.make_constraint(deform, 'STRETCH_TO', next_tweak)
                self.make_driver(stretch, 'bulge', variables=[(self.prop_bone, 'volume_deform')])

                # Bendy
                self.bendy_drivers(i, deform, entry, next_entry, tweak, next_tweak)
            elif next_entry:
                self.make_constraint(deform, 'DAMPED_TRACK', next_entry.org)
                self.make_constraint(deform, 'STRETCH_TO', next_entry.org)

        else:
            self.make_constraint(deform, 'COPY_TRANSFORMS', entry.org)

    def bendy_drivers(self, i, deform, entry, next_entry, tweak, next_tweak):
        '''New function to create bendy bone drivers'''
        pbone = self.get_bone(deform)
        space = 'LOCAL_SPACE'
        v_type = 'TRANSFORMS'
        next_org = ([ s for s in self.segment_table_full if s.org_idx == entry.org_idx + 1 ][0].org)

        if entry.seg_idx is not None:
            ####################################################
            # Easing

            self.make_driver(
                pbone,
                'bbone_easein',
                expression='scale_y - 1',
                variables={
                    'scale_y': {
                        'type': v_type,
                        'targets':
                        [
                            {
                                'id': self.obj,
                                'bone_target': tweak,
                                'transform_type': 'SCALE_Y',
                                'transform_space': space,
                            }
                        ]
                    }
                }
            )

            self.make_driver(
                pbone,
                'bbone_easeout',
                expression='scale_y - 1',
                variables={
                    'scale_y': {
                        'type': v_type,
                        'targets':
                        [
                            {
                                'id': self.obj,
                                'bone_target': next_tweak,
                                'transform_type': 'SCALE_Y',
                                'transform_space': space,
                            }
                        ]
                    }
                }
            )

            ####################################################
            # Scale X

            self.make_driver(
                pbone,
                'bbone_scaleinx',
                variables={
                    'scale_x': {
                        'type': v_type,
                        'targets':
                        [
                            {
                                'id': self.obj,
                                'bone_target': tweak,
                                'transform_type': 'SCALE_X',
                                'transform_space': space,
                            }
                        ]
                    }
                }
            )

            self.make_driver(
                pbone,
                'bbone_scaleoutx',
                variables={
                    'scale_x': {
                        'type': v_type,
                        'targets':
                        [
                            {
                                'id': self.obj,
                                'bone_target': next_tweak,
                                'transform_type': 'SCALE_X',
                                'transform_space': space,
                            }
                        ]
                    }
                }
            )

            ####################################################
            # Scale Z

            self.make_driver(
                pbone,
                'bbone_scaleiny',
                variables={
                    'scale_z': {
                        'type': v_type,
                        'targets':
                        [
                            {
                                'id': self.obj,
                                'bone_target': tweak,
                                'transform_type': 'SCALE_Z',
                                'transform_space': space,
                            }
                        ]
                    }
                }
            )

            self.make_driver(
                pbone,
                'bbone_scaleouty',
                variables={
                    'scale_z': {
                        'type': v_type,
                        'targets':
                        [
                            {
                                'id': self.obj,
                                'bone_target': next_tweak,
                                'transform_type': 'SCALE_Z',
                                'transform_space': space,
                            }
                        ]
                    }
                }
            )

            ####################################################
            # Roll

            if entry.seg_idx > 0:
                if entry.org_idx == 0:
                    expr_rollin = 'swing_out * ' + str(entry.seg_idx) + ' / ' + str(self.segments) + ' - swing_in * ' + str(self.segments - entry.seg_idx) + ' / ' + str(self.segments)
                    variables_rollin = {
                        'swing_out': {
                            'type': v_type,
                            'targets':
                            [
                                {
                                    'id': self.obj,
                                    'bone_target': next_org,
                                    'transform_type': 'ROT_Y',
                                    'rotation_mode': 'SWING_TWIST_Y',
                                    'transform_space': space,
                                }
                            ]
                        },
                        'swing_in': {
                            'type': v_type,
                            'targets':
                            [
                                {
                                    'id': self.obj,
                                    'bone_target': entry.org,
                                    'transform_type': 'ROT_Y',
                                    'rotation_mode': 'SWING_TWIST_Y',
                                    'transform_space': space,
                                }
                            ]
                        }
                    }
                else:
                    expr_rollin = 'swing_out * ' + str(entry.seg_idx) + ' / ' + str(self.segments)
                    variables_rollin={
                        'swing_out': {
                            'type': v_type,
                            'targets':
                            [
                                {
                                    'id': self.obj,
                                    'bone_target': next_org,
                                    'transform_type': 'ROT_Y',
                                    'rotation_mode': 'SWING_TWIST_Y',
                                    'transform_space': space,
                                }
                            ]
                        }
                    }
                
                self.make_driver(
                    pbone,
                    'bbone_rollin',
                    expression=expr_rollin,
                    variables=variables_rollin
                )

            if entry.seg_idx < self.segments - 1:
                if entry.org_idx == 0:
                    expr_rollout = 'swing_out * ' + str(entry.seg_idx + 1) + ' / ' + str(self.segments) + ' - swing_in * ' + str(self.segments - entry.seg_idx - 1) + ' / ' + str(self.segments)
                    variables_rollout = {
                        'swing_out': {
                            'type': v_type,
                            'targets':
                            [
                                {
                                    'id': self.obj,
                                    'bone_target': next_org,
                                    'transform_type': 'ROT_Y',
                                    'rotation_mode': 'SWING_TWIST_Y',
                                    'transform_space': space,
                                }
                            ]
                        },
                        'swing_in': {
                            'type': v_type,
                            'targets':
                            [
                                {
                                    'id': self.obj,
                                    'bone_target': entry.org,
                                    'transform_type': 'ROT_Y',
                                    'rotation_mode': 'SWING_TWIST_Y',
                                    'transform_space': space,
                                }
                            ]
                        },
                    }
                else:
                    expr_rollout = 'swing_out * ' + str(entry.seg_idx + 1) + ' / ' + str(self.segments)
                    variables_rollout = {
                        'swing_out': {
                            'type': v_type,
                            'targets':
                            [
                                {
                                    'id': self.obj,
                                    'bone_target': next_org,
                                    'transform_type': 'ROT_Y',
                                    'rotation_mode': 'SWING_TWIST_Y',
                                    'transform_space': space,
                                }
                            ]
                        }
                    }

                self.make_driver(
                    pbone,
                    'bbone_rollout',
                    expression=expr_rollout,
                    variables=variables_rollout
                )

    ####################################################
    # UI

    @classmethod
    def tweak_align(self, layout, params):
        r = layout.row(align=True)
        r.prop(params, "tweak_align_default", toggle=True)
        r.prop(params, "tweak_align_panel", text="", icon='OPTIONS')

    @classmethod
    def ease(self, layout, params):
        r = layout.row(align=True)
        r.prop(params, "ease_in", toggle=True)
        r.prop(params, "ease_joints", toggle=True)
        r.prop(params, "ease_out", toggle=True)

    @classmethod
    def rotation_modes(self, layout, params):
        layout.row().prop(params, "rotation_mode_ik", text="IK")
        layout.row().prop(params, "rotation_mode_tweak", text="Tweaks")

    @classmethod
    def limb_volume_deform_ui(self, layout, params):
        r = layout.row(align=True)
        r.prop(params, 'limb_volume_deform_default', slider=True)
        r.prop(params, 'limb_volume_deform_panel', text="", icon='OPTIONS')

    ####################################################
    # Settings

    @stage.finalize
    def finalize_armature_display(self):
        '''New function to set rig viewport display'''
        self.obj.data.display_type = 'BBONE'

    @classmethod
    def add_parameters(self, params):
        super().add_parameters(params)

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

        params.rotation_mode_ik = EnumProperty(
            name        = 'Default IK Controller Rotation Mode',
            items       = rotation_modes,
            default     = 'QUATERNION',
            description = 'Default rotation mode for IK control bones',
        )

        params.rotation_mode_tweak = EnumProperty(
            name        = 'Default Tweak Controller Rotation Mode',
            items       = rotation_modes,
            default     = 'ZXY',
            description = 'Default rotation mode for tweak control bones',
        )

        params.tweak_align_default = BoolProperty(
            name='Align Joints',
            default=True,
            description='Align joint tweaks to interpolate between limb segments. This only affects the default, property can always be animated.',
        )

        params.tweak_align_panel = BoolProperty(
            name='Align Joints Panel UI',
            default=False,
            description='Add panel to control joint interpolation to the UI.',
        )

        params.ease_in = BoolProperty(
            name='Bend In',
            default=False,
            description='Make incoming joint bendy by default. Sets default ease for joint tweak to 1.',
        )

        params.ease_joints = BoolProperty(
            name='Bend Joints',
            default=False,
            description='Make main joints bendy by default. Sets default ease for joint tweaks to 1.',
        )

        params.ease_out = BoolProperty(
            name='Bend Out',
            default=False,
            description='Make outgoing joint bendy by default. Sets default ease for joint tweak to 1.',
        )

        params.limb_volume_deform_default = FloatProperty(
            name="Deform Volume Variation Default",
            default=1.0,
            soft_min=0.0,
            soft_max=1.0,
            description="Default value for deform bone chain stretch volume variation",
        )

        params.limb_volume_deform_panel = BoolProperty(
            name="Deform Volume Variation Panel",
            default=False,
            description="Add panel to control volume variation to the UI",
        )

    @classmethod
    def parameters_ui(self, layout, params):
        self.tweak_align(layout, params)
        self.limb_volume_deform_ui(layout, params)
        self.ease(layout, params)
        self.rotation_modes(layout, params)
        super().parameters_ui(layout, params)