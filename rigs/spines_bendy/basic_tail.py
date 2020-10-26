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

from itertools import count

from rigify.base_rig import stage
from rigify.utils.naming import strip_org, make_derived_name
from rigify.utils.misc import map_list
from rigify.utils.layers import ControlLayersOption
from rigify.utils.bones import put_bone, flip_bone
from rigify.rigs.spines.basic_tail import Rig as TailRig

from ...utils.misc import threewise_nozip

class Rig(TailRig):
    """
    Bendy tail rig with connect option.
    """

    min_chain_length = 1

    def initialize(self):
        # Bbone segments
        super().initialize()
        self.bbone_segments = self.params.bbones_tail
        self.use_connect_reverse = False

    ####################################################
    # Control bones

    def rig_control_bone(self, i, ctrl, prev_ctrl):
        self.make_constraint(
            ctrl, 'COPY_ROTATION', self.bones.ctrl.master,
            use_xyz=self.copy_rotation_axes,
            space='LOCAL', mix_mode='BEFORE',
        )
    
    ####################################################
    # Tweak MCH chain

    @stage.generate_bones
    def make_tweak_mch_chain(self):
        # Create (new) mch bones for tweaks
        orgs = self.bones.org
        self.bones.mch.tweak = map_list(self.make_tweak_mch_bone, count(0), orgs + orgs[-1:])

    def make_tweak_mch_bone(self, i, org):
        # Tweak mch creation loop
        name = self.copy_bone(org, make_derived_name(org, 'mch', '_tweak'), parent=False, scale=0.5)

        if i == len(self.bones.org):
            put_bone(self.obj, name, self.get_bone(org).tail)
        
        return name

    @stage.parent_bones
    def parent_tweak_mch_chain(self):
        # Parent tweak mch to ctrl chain and realign
        mch = self.bones.mch
        ctrl = self.bones.ctrl
        targets = threewise_nozip([*ctrl.fk, mch.tweak[-1]])

        for args in zip(count(0), mch.tweak, ctrl.fk + ctrl.fk[-1:]):
            self.parent_tweak_mch_bone(*args)
        
        for args in zip(mch.tweak, *targets):
            self.align_tweak_mch_bone(*args)
        
    def parent_tweak_mch_bone(self, i, mch, parent):
        # Parent tweak mch
        if i == 0 and self.use_connect_chain:
            self.set_bone_parent(mch, self.bones.ctrl.tweak[0])
        else:
            self.set_bone_parent(mch, parent)

    def align_tweak_mch_bone(self, mch, prev_target, curr_target, next_target):
        # Realign tweak mch
        if prev_target and next_target:
            mch_bone = self.get_bone(mch)
            length = mch_bone.length
            mch_bone.tail = mch_bone.head + self.get_bone(next_target).head - self.get_bone(prev_target).head
            mch_bone.length = length

    @stage.rig_bones
    def rig_tweak_mch_chain(self):
        # Create tweak mch constraints
        mch = self.bones.mch
        ctrl = self.bones.ctrl
        targets = threewise_nozip([*ctrl.fk, mch.tweak[-1]])

        for args in zip(count(0), mch.tweak, *targets):
            self.rig_tweak_mch_bone(*args)

    def rig_tweak_mch_bone(self, i, mch, prev_target, curr_target, next_target):
        # Constraints to calculate tangent rotation between previous and next chain targets
        if prev_target and next_target:
            self.make_constraint(mch, 'COPY_LOCATION', prev_target)
            self.make_constraint(mch, 'STRETCH_TO', next_target, bulge=0, volume='NO_VOLUME', keep_axis='PLANE_Z')
            self.make_constraint(mch, 'COPY_LOCATION', curr_target)
        self.make_constraint(mch, 'COPY_SCALE', self.bones.ctrl.master)  

    ####################################################
    # Tweak chain
    
    @stage.generate_bones
    def make_tweak_chain(self):
        orgs = self.bones.org
        self.bones.ctrl.tweak = map_list(self.make_tweak_bone, count(0), orgs + orgs[-1:])

    def make_tweak_bone(self, i, org):
        if i == 0 and self.check_connect_tweak(org):
            return self.connected_tweak
        
        else:
            name = self.copy_bone(org, 'tweak_' + strip_org(org), parent=False, scale=0.5)
            if i == len(self.bones.org):
                put_bone(self.obj, name, self.get_bone(org).tail)
        
        return name

    @stage.parent_bones
    def parent_tweak_chain(self):
        ctrl = self.bones.ctrl
        mch = self.bones.mch
        targets = threewise_nozip([*ctrl.fk, mch.tweak[-1]])
        for i, tweak, mch in zip(count(0), ctrl.tweak, mch.tweak):
            if not self.use_connect_chain or i != 0:
                self.set_bone_parent(tweak, mch)
        
        for args in zip(ctrl.tweak, *targets):
            self.align_tweak_bone(*args)
        
    def parent_tweak_bone(self, i, tweak, parent):
        # Parent tweak
        if i == 0 and self.use_connect_chain:
            self.set_bone_parent(tweak, self.bones.ctrl.tweak[0])
        else:
            self.set_bone_parent(tweak, parent)

    def align_tweak_bone(self, tweak, prev_target, curr_target, next_target):
        # Realign tweak
        if prev_target and next_target:
            tweak_bone = self.get_bone(tweak)
            length = tweak_bone.length
            tweak_bone.tail = tweak_bone.head + self.get_bone(next_target).head - self.get_bone(prev_target).head
            tweak_bone.length = length

    def configure_tweak_bone(self, i, tweak):
        # Fully unlocked tweaks
        tweak_pb = self.get_bone(tweak)
        tweak_pb.rotation_mode = 'ZXY'
    
    ##############################
    # ORG chain

    def rig_org_bone(self, i, org, tweak, next_tweak):
        pass

    ####################################################
    # Deform bones

    @stage.parent_bones
    def rig_deform_chain_easing(self):
        # New function to set bbone easing in edit mode
        tweaks = self.bones.ctrl.tweak

        for args in zip(count(0), self.bones.deform, tweaks, tweaks[1:]):
            self.rig_deform_easing(*args)
        
    def rig_deform_easing(self, i, deform, tweak, next_tweak):
        # Easing per bone
        pbone = self.get_bone(deform)
        pbone.bbone_segments = self.bbone_segments
        pbone.bbone_handle_type_start = 'TANGENT'
        pbone.bbone_handle_type_end = 'TANGENT'

        if i == 0 and self.use_connect_chain:
            pbone.bbone_custom_handle_start = self.get_bone(self.bones.mch.tweak[0])
        else:
            pbone.bbone_custom_handle_start = self.get_bone(tweak)
        pbone.bbone_custom_handle_end = self.get_bone(next_tweak)

    @stage.rig_bones
    def rig_deform_chain(self):
        tweaks = self.bones.ctrl.tweak
        for args in zip(count(0), self.bones.deform, tweaks, tweaks[1:]):
            self.rig_deform_bone(*args)

    def rig_deform_bone(self, i, deform, tweak, next_tweak):
        # Added copy scale
        self.make_constraint(deform, 'COPY_TRANSFORMS', tweak)
        self.make_constraint(deform, 'COPY_SCALE', self.bones.ctrl.master)
        if next_tweak:
            self.make_constraint(deform, 'DAMPED_TRACK', next_tweak)
            self.make_constraint(deform, 'STRETCH_TO', next_tweak)
        self.rig_drivers_bendy(i, deform, tweak, next_tweak)

    def rig_drivers_bendy(self, i, deform, tweak, next_tweak):
        # New function to create bendy bone drivers
        pbone = self.get_bone(deform)
        space = 'LOCAL_SPACE'
        v_type = 'TRANSFORMS'

        ####################################################
        # Easing

        self.make_driver(
            pbone.bone,
            'bbone_easein',
            #expression='scale_y - 1' if i == 0 else None,
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
            pbone.bone,
            'bbone_easeout',
            expression='scale_y - 1' if i == 0 else None,
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
    # SETTINGS
    
    @stage.configure_bones
    def configure_armature_display(self):
        # New function to set rig viewport display
        self.obj.data.display_type = 'BBONE'
    
    @classmethod
    def add_parameters(self, params):
        # Added bbone segments
        super().add_parameters(params)

        params.bbones_tail = bpy.props.IntProperty(
            name        = 'B-Bone Segments',
            default     = 8,
            min         = 1,
            description = 'Number of B-Bone segments'
        )

    @classmethod
    def parameters_ui(self, layout, params):
        # Added bbone segments
        r = layout.row()
        r.prop(params, "bbones_tail")

        super().parameters_ui(layout, params)


def create_sample(obj, *, parent=None):
    # generated by rigify.utils.write_metarig
    bpy.ops.object.mode_set(mode='EDIT')
    arm = obj.data

    bones = {}

    bone = arm.edit_bones.new('tail')
    bone.head[:] = 0.0000, 0.0552, 1.0099
    bone.tail[:] = -0.0000, 0.0582, 0.8669
    bone.roll = 0.0000
    bone.use_connect = False
    if parent:
        bone.parent = arm.edit_bones[parent]
    bones['tail'] = bone.name
    bone = arm.edit_bones.new('tail.001')
    bone.head[:] = -0.0000, 0.0582, 0.8669
    bone.tail[:] = -0.0000, 0.0365, 0.7674
    bone.roll = 0.0000
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['tail']]
    bones['tail.001'] = bone.name
    bone = arm.edit_bones.new('tail.002')
    bone.head[:] = -0.0000, 0.0365, 0.7674
    bone.tail[:] = -0.0000, 0.0010, 0.6984
    bone.roll = 0.0000
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['tail.001']]
    bones['tail.002'] = bone.name

    bpy.ops.object.mode_set(mode='OBJECT')
    pbone = obj.pose.bones[bones['tail']]
    pbone.rigify_type = 'spines_bendy.basic_tail'
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    try:
        pbone.rigify_parameters.connect_chain = bool(parent)
    except AttributeError:
        pass
    try:
        pbone.rigify_parameters.tweak_layers = [False, False, False, False, True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False]
    except AttributeError:
        pass
    try:
        pbone.rigify_parameters.copy_rotation_axes = [True, True, True]
    except AttributeError:
        pass
    pbone = obj.pose.bones[bones['tail.001']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['tail.002']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'

    bpy.ops.object.mode_set(mode='EDIT')
    for bone in arm.edit_bones:
        bone.select = False
        bone.select_head = False
        bone.select_tail = False
    for b in bones:
        bone = arm.edit_bones[bones[b]]
        bone.select = True
        bone.select_head = True
        bone.select_tail = True
        arm.edit_bones.active = bone
