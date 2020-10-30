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

from rigify.utils.bones import put_bone
from rigify.utils.layers import ControlLayersOption
from rigify.utils.naming import make_derived_name
from rigify.utils.misc import map_list
from rigify.base_rig import stage
from rigify.rigs.widgets import create_gear_widget

from rigify.rigs.spines.basic_spine import Rig as SpineRig

from .bendy_chain_rigs import BaseBendyRig

from ...utils.misc import threewise_nozip


class Rig(SpineRig, BaseBendyRig):
    """
    Bendy spine rig with fixed pivot, hip/chest controls and tweaks.
    """

    ####################################################
    # Volume control

    @stage.generate_bones
    def make_volume_control(self):
        org = self.bones.org[self.pivot_pos]
        self.bones.ctrl.volume = self.copy_bone(org, 'spine_volume')
        self.copy_scale_bone = self.bones.ctrl.volume

    @stage.parent_bones
    def parent_volume_control(self):
        self.set_bone_parent(self.bones.ctrl.volume, self.bones.ctrl.master)

    @stage.configure_bones
    def configure_volume_control(self):
        bone = self.get_bone(self.bones.ctrl.volume)
        bone.lock_location = (True, True, True)
        bone.lock_rotation = (True, True, True)
        bone.lock_rotation_w = True
        bone.lock_scale = (False, True, False)

    @stage.generate_widgets
    def make_volume_control_widget(self):
        bone = self.bones.ctrl.volume
        create_gear_widget(self.obj, bone, size=4)

    ####################################################
    # MCH bones associated with main controls

    @stage.rig_bones
    def rig_mch_control_bones(self):
        # Pivot constraint changed to only copy location
        mch = self.bones.mch
        self.make_constraint(mch.pivot, 'COPY_LOCATION', self.fk_result.hips[-1], influence=0.5)

    ####################################################
    # Tweak Targets
    
    def check_mch_parents(self):
        mch = self.bones.mch
        chain = self.fk_result
        return [chain.hips[0], *chain.hips[0:-1], mch.pivot, *chain.chest[1:], chain.chest[-1]]

    def check_mch_targets(self):
        mch = self.bones.mch
        chain = self.fk_result
        return threewise_nozip([mch.tweak[0], *chain.hips[0:-1], mch.pivot, *chain.chest[1:], mch.tweak[-1]])      

    ####################################################
    # Tweak chain

    @stage.parent_bones
    def parent_tweak_chain(self):
        BaseBendyRig.parent_tweak_chain(self)

    def align_tweak_bone(self, i, tweak, prev_target, curr_target, next_target):
        # Realign tweak
        if prev_target and next_target:
            tweak_bone = self.get_bone(tweak)
            length = tweak_bone.length
            tweak_bone.tail = tweak_bone.head + self.get_bone(next_target).head - self.get_bone(prev_target).head
            tweak_bone.length = length

    def configure_tweak_bone(self, i, tweak):
        BaseBendyRig.configure_tweak_bone(self, i, tweak)

    ####################################################
    # Deform bones

    def rig_deform_bone(self, i, deform, tweak, next_tweak, total):
        BaseBendyRig.rig_deform_bone(self, i, deform, tweak, next_tweak, total)

    @stage.configure_bones
    def configure_bbone_chain(self):
        pass

    ##############################
    # ORG chain

    @stage.parent_bones
    def parent_org_chain(self):
        ctrl = self.bones.ctrl
        org = self.bones.org
        for fk, org in zip(ctrl.fk.hips + ctrl.fk.chest, org):
            self.set_bone_parent(org, fk)
    
    def rig_org_bone(self, i, org, deform):
        BaseBendyRig.rig_org_bone(self, i, org, deform)

    ####################################################
    # SETTINGS

    @classmethod
    def parameters_ui(self, layout, params):
        # Added bbone segments
        r = layout.row()
        r.prop(params, "bbones_spine")

        r = layout.row(align=True)
        r.prop(params, "bbones_easein", text="Ease In", toggle=True)
        r.prop(params, "bbones_easeout", text="Ease Out", toggle=True)

        super().parameters_ui(layout, params)


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
    pbone.rigify_type = 'bendy_chains.spine'
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
