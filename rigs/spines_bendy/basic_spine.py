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

from rigify.utils.layers import ControlLayersOption
from rigify.base_rig import stage
from rigify.rigs.spines.basic_spine import Rig as SpineRig


class Rig(SpineRig):
    """
    Bendy spine rig with fixed pivot, hip/chest controls and tweaks.
    """

    ####################################################
    # BONES
    #
    # ctrl:
    #   master
    #     Main control.
    #   master_pivot
    #     Custom pivot under the master control.
    # mch:
    #   master_pivot
    #     Final output of the custom pivot.
    #
    ####################################################

    ####################################################
    # ORG bones

    @stage.parent_bones
    def parent_org_chain(self):
        # Set org parents to ctrl instead of tweak
        for fk, org in zip(self.bones.ctrl.fk, self.bones.org):
            self.set_bone_parent(org, fk)

    ####################################################
    # Tweak bones

    def configure_tweak_bone(self, i, tweak):
        # Fully unlocked tweaks
        tweak_pb = self.get_bone(tweak)
        tweak_pb.rotation_mode = 'ZXY'
    
    ####################################################
    # Deform bones
    @stage.parent_bones
    def parent_deform_chain(self):
        # New loop for parenting
        for args in zip(count(0), self.bones.deform, self.bones.org):
            self.parent_deform_bone(*args)

    def parent_deform_bone(self, i, deform, org):
        # New, set deform parent to org
        if i == 0:
            self.set_bone_parent(deform, self.bones.ctrl.master)
        else:
            self.set_bone_parent(deform, org)

    @stage.parent_bones
    def rig_deform_chain_easing(self):
        # New function to set bbone easing in edit mode
        tweaks = self.bones.ctrl.tweak
        for args in zip(count(0), self.bones.deform, tweaks, tweaks[1:]):
            self.rig_deform_easing(*args)
        
    def rig_deform_easing(self, i, deform, tweak, next_tweak):
        # Easing per bone
        pbone = self.get_bone(deform)
        pbone.bbone_handle_type_start = 'TANGENT'
        pbone.bbone_handle_type_end = 'ABSOLUTE'
        pbone.bbone_custom_handle_start = self.get_bone(tweak)
        pbone.bbone_custom_handle_end = self.get_bone(next_tweak)    

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

        #expr_in = ' - 1' if i == 0 else ''
        self.make_driver(
            pbone.bone,
            'bbone_easein',
            #expression='scale_y' + expr_in,
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

        #expr_out = ''
        self.make_driver(
            pbone.bone,
            'bbone_easeout',
            #expression='scale_y' + expr_out,
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


def create_sample(obj):
    # generated by rigify.utils.write_metarig
    bpy.ops.object.mode_set(mode='EDIT')
    arm = obj.data

    bones = {}

    bone = arm.edit_bones.new('spine')
    bone.head[:] = 0.0000, 0.0552, 1.0099
    bone.tail[:] = 0.0000, 0.0172, 1.1573
    bone.roll = 0.0000
    bone.use_connect = False
    bones['spine'] = bone.name

    bone = arm.edit_bones.new('spine.001')
    bone.head[:] = 0.0000, 0.0172, 1.1573
    bone.tail[:] = 0.0000, 0.0004, 1.2929
    bone.roll = 0.0000
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['spine']]
    bones['spine.001'] = bone.name

    bone = arm.edit_bones.new('spine.002')
    bone.head[:] = 0.0000, 0.0004, 1.2929
    bone.tail[:] = 0.0000, 0.0059, 1.4657
    bone.roll = 0.0000
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['spine.001']]
    bones['spine.002'] = bone.name

    bone = arm.edit_bones.new('spine.003')
    bone.head[:] = 0.0000, 0.0059, 1.4657
    bone.tail[:] = 0.0000, 0.0114, 1.6582
    bone.roll = 0.0000
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['spine.002']]
    bones['spine.003'] = bone.name


    bpy.ops.object.mode_set(mode='OBJECT')
    pbone = obj.pose.bones[bones['spine']]
    pbone.rigify_type = 'spines_bendy.basic_spine'
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'

    try:
        pbone.rigify_parameters.tweak_layers = [False, False, False, False, True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False]
    except AttributeError:
        pass
    pbone = obj.pose.bones[bones['spine.001']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['spine.002']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['spine.003']]
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

    return bones
