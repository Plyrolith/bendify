#====================== BEGIN GPL LICENSE BLOCK ======================
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
#======================= END GPL LICENSE BLOCK ========================

# <pep8 compliant>

import bpy

from rigify.utils.bones import set_bone_widget_transform
from rigify.utils.layers import ControlLayersOption
from rigify.utils.misc import pairwise_nozip, padnone
from rigify.utils.naming import make_derived_name
from rigify.base_rig import stage
from rigify.rigs.limbs.limb_rigs import BaseLimbRig

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
        ctrl = self.bones.ctrl
        panel = self.script.panel_with_selected_check(self, ctrl.flatten())
        self.make_property(ctrl.master, 'volume_variation', default=1.0, max=100.0, soft_max=1.0, description='Volume variation for DEF bones')
        panel.custom_prop(ctrl.master, 'volume_variation', text='Volume Variation', slider=True)

    @stage.configure_bones
    def configure_master_control(self):
        # Unlocked master control scale
        super().configure_master_control()
        bone = self.get_bone(self.bones.ctrl.master)
        bone.lock_scale = (False, False, False)
    
    @stage.generate_widgets
    def make_master_control_widget(self):
        super().make_master_control_widget()
        set_bone_widget_transform(self.obj, self.bones.ctrl.master, self.bones.org.main[0])

    ####################################################
    # FK control chain

    def parent_fk_control_bone(self, i, ctrl, prev, org, parent_mch):
        # Disconnected FK control bones
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
        # Disconnect ALL org bones
        orgs = self.bones.org.main
        for org in orgs:
            self.get_bone(org).use_connect = False

    ####################################################
    # Tweak control chain

    @stage.parent_bones
    def parent_tweak_chain(self):
        # Added count to zip and created sub function
        for args in zip(count(0), self.bones.ctrl.tweak, self.segment_table_tweak):
            self.parent_tweak_bone(*args)

    def parent_tweak_bone(self, i, tweak, entry):
        super().parent_tweak_mch_bone(i, tweak, entry)

    def configure_tweak_bone(self, i, tweak, entry):
        # Completely unlocked tweak
        tweak_pb = self.get_bone(tweak)
        tweak_pb.rotation_mode = 'ZXY'

    ####################################################
    # Tweak MCH chain

    @stage.generate_bones
    def make_tweak_mch_chain(self):
        # Removed tweak mch
        pass

    @stage.parent_bones
    def parent_tweak_mch_chain(self):
        # Removed tweak mch
        pass

    @stage.rig_bones
    def rig_tweak_mch_chain(self):
        # Removed tweak mch
        pass

    ####################################################
    # Deform chain
    
    @stage.parent_bones
    def parent_deform_chain(self):
        self.set_bone_parent(self.bones.deform[0], self.rig_parent_bone)
        self.parent_bone_chain(self.bones.deform)

    @stage.parent_bones
    def rig_deform_chain_easing(self):
        # (New) ease settings on edit bones need to bo set in parenting stage
        tweaks = pairwise_nozip(padnone(self.bones.ctrl.tweak))

        for args in zip(count(0), self.bones.deform, *tweaks):
            self.rig_deform_easing(*args)
        
    def rig_deform_easing(self, i, deform, tweak, next_tweak):
        # Sub loop function for bbone easing
        pbone = self.get_bone(deform)
        pbone.bbone_handle_type_start = 'TANGENT'
        pbone.bbone_handle_type_end = 'TANGENT'
        pbone.bbone_custom_handle_start = self.get_bone(tweak)
        pbone.bbone_custom_handle_end = self.get_bone(next_tweak)

    def rig_deform_bone(self, i, deform, entry, next_entry, tweak, next_tweak):
        # Added copy scale constraint and bendy driver creation, excluded last deform segment
        if tweak and not i == len(self.bones.deform) - 1:
            self.make_constraint(deform, 'COPY_LOCATION', tweak)
            self.make_constraint(deform, 'COPY_SCALE', self.bones.ctrl.master)
            if next_tweak:
                self.make_constraint(deform, 'DAMPED_TRACK', next_tweak)
                stretch = self.make_constraint(deform, 'STRETCH_TO', next_tweak)
                self.drivers_deform_bone(i, deform, stretch, entry, next_entry, tweak, next_tweak)
            elif next_entry:
                self.make_constraint(deform, 'DAMPED_TRACK', next_entry.org)
                self.make_constraint(deform, 'STRETCH_TO', next_entry.org)

        else:
            self.make_constraint(deform, 'COPY_TRANSFORMS', entry.org)

    def drivers_deform_bone(self, i, deform, stretch, entry, next_entry, tweak, next_tweak):
        # New function to create bendy bone drivers
        pbone = self.get_bone(deform)
        space = 'LOCAL_SPACE'
        v_type = 'TRANSFORMS'
        next_org = ([ s for s in self.segment_table_full if s.org_idx == entry.org_idx + 1 ][0].org)

        ####################################################
        # Volume Variation

        self.make_driver(pbone.constraints["Stretch To"], 'bulge', variables=[(self.bones.ctrl.master, 'volume_variation')])

        if entry.seg_idx is not None:
            ####################################################
            # Easing

            expr_in = '' if entry.seg_idx and i > 0 else ' - 1'
            self.make_driver(
                pbone.bone,
                'bbone_easein',
                expression='scale_y' + expr_in,
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

            expr_out = '' if next_entry.seg_idx else ' - 1'
            self.make_driver(
                pbone.bone,
                'bbone_easeout',
                expression='scale_y' + expr_out,
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
                pbone.bone,
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
                pbone.bone,
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
                pbone.bone,
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
                pbone.bone,
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
                    pbone.bone,
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
                    pbone.bone,
                    'bbone_rollout',
                    expression=expr_rollout,
                    variables=variables_rollout
                )

    ####################################################
    # Settings

    @stage.configure_bones
    def configure_armature_display(self):
        # New function to set rig viewport display
        self.obj.data.display_type = 'BBONE'