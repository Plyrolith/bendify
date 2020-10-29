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

from rigify.utils.misc import map_list
from rigify.utils.layers import ControlLayersOption
from rigify.base_rig import stage
from rigify.rigs.spines.super_head import Rig as SuperHeadRig

from .bendy_chain_rigs import BaseBendyHeadTailRig

from ...utils.misc import threewise_nozip


class Rig(SuperHeadRig, BaseBendyHeadTailRig):
    """
    Head rig with long bendy neck support and connect option.
    """


    def initialize(self):
        super().initialize()

        self.use_connect_chain = False
        self.connected_tweak = None
    
    ####################################################
    # Tweak Targets

    def check_mch_parents(self):
        return self.bones.mch.chain

    def check_mch_targets(self):
        return threewise_nozip(self.bones.mch.chain)

    ####################################################
    # Tweak MCH chain
    
    @stage.parent_bones
    def parent_tweak_mch_chain(self):
        pass

    
    @stage.rig_bones
    def rig_tweak_mch_chain(self):
        pass

    ####################################################
    # MCH chain for the middle of the neck

    @stage.generate_bones
    def make_mch_chain(self):
        orgs = self.bones.org
        self.bones.mch.chain = map_list(self.make_mch_bone, orgs)

    @stage.parent_bones
    def parent_mch_chain(self):
        mch = self.bones.mch

        for bone in mch.chain[1:-1]:
            self.set_bone_parent(bone, mch.stretch, inherit_scale='NONE')
        self.set_bone_parent(
            mch.chain[0],
            self.incoming_tweak or self.bones.ctrl.neck
        )
        self.set_bone_parent(mch.chain[-1], self.bones.ctrl.head)
    
    @stage.parent_bones
    def align_tweak_mch_chain(self):
        mch = self.bones.mch
        targets = self.check_mch_targets()
        
        for args in zip(count(0), mch.chain, *targets):
            self.align_tweak_mch_bone(*args)
    
    @stage.rig_bones
    def rig_mch_chain(self):
        chain = self.bones.mch.chain
        parents = self.check_mch_parents()
        targets = self.check_mch_targets()

        if self.long_neck:
            ik = self.bones.mch.ik
            for args in zip(count(0), chain[1:-1], ik[1:]):
                self.rig_mch_bone_long(*args, len(chain))
        #else:
        #    for args in zip(count(0), chain, parents, *targets):
        #        self.rig_tweak_mch_bone(*args)


    ####################################################
    # Tweak chain
 
    @stage.generate_bones
    def make_tweak_chain(self):
        orgs = self.bones.org
        if self.has_neck:
            self.bones.ctrl.tweak = map_list(self.make_tweak_bone, count(0), orgs)

    @stage.parent_bones
    def parent_tweak_chain(self):
        ctrl = self.bones.ctrl
        mch = self.bones.mch

        if self.has_neck:
            for args in zip(ctrl.tweak, mch.chain):
                self.set_bone_parent(*args)
            last = self.get_bone(ctrl.tweak[-1])
            if len(ctrl.tweak) > 2:
                last.length = self.get_bone(ctrl.tweak[-2]).length
            else:
                last.length /= 12

    @stage.parent_bones
    def align_tweak_chain(self):
        ctrl = self.bones.ctrl
        targets = self.check_mch_targets()
        
        for args in zip(count(0), ctrl.tweak, *targets):
            self.align_tweak_bone(*args)  

    def configure_tweak_bone(self, i, tweak):
        # Fully unlocked tweaks
        tweak_pb = self.get_bone(tweak)
        tweak_pb.rotation_mode = 'ZXY'

    @stage.rig_bones
    def generate_neck_tweak_widget(self):
        pass

    ##############################
    # ORG chain

    def rig_org_bone(self, i, org, deform, tweaks):
        pass

    ####################################################
    # Deform bones

    @stage.generate_bones
    def register_parent_bones(self):
        None

    @stage.parent_bones
    def parent_deform_chain(self):
        BaseBendyHeadTailRig.parent_deform_chain(self)

    @stage.parent_bones
    def rig_deform_chain_easing(self):
        # New function to set bbone easing in edit mode
        tweaks = self.bones.ctrl.tweak
        for args in zip(count(0), self.bones.deform, tweaks, tweaks[1:]):
            self.rig_deform_easing(*args)

    @stage.rig_bones
    def rig_deform_chain(self):
        BaseBendyHeadTailRig.rig_deform_chain(self)

        deforms = self.bones.deform
        tweaks = self.bones.ctrl.tweak
        head = self.bones.ctrl.head
        self.make_constraint(deforms[-1], 'COPY_ROTATION', head)
        self.make_constraint(deforms[-1], 'COPY_LOCATION', tweaks[-1])
        self.make_constraint(deforms[-1], 'COPY_SCALE', head)
        self.make_constraint(deforms[-1], 'DAMPED_TRACK', head, head_tail=1)
        self.make_constraint(deforms[-1], 'STRETCH_TO', head, head_tail=1)            
        
    def rig_deform_easing(self, i, deform, tweak, next_tweak):
        # Easing per bone
        pbone = self.get_bone(deform)
        pbone.bbone_handle_type_start = 'TANGENT'
        pbone.bbone_handle_type_end = 'TANGENT'
        pbone.bbone_custom_handle_start = self.get_bone(tweak)
        pbone.bbone_custom_handle_end = self.get_bone(next_tweak)

    ####################################################
    # SETTINGS
    
    @stage.configure_bones
    def configure_armature_display(self):
        # New function to set rig viewport display
        self.obj.data.display_type = 'BBONE'

    @classmethod
    def parameters_ui(self, layout, params):
        BaseBendyHeadTailRig.parameters_ui(layout, params)

def create_sample(obj, *, parent=None):
    # generated by rigify.utils.write_metarig
    bpy.ops.object.mode_set(mode='EDIT')
    arm = obj.data

    bones = {}

    bone = arm.edit_bones.new('neck')
    bone.head[:] = 0.0000, 0.0114, 1.6582
    bone.tail[:] = 0.0000, -0.0130, 1.7197
    bone.roll = 0.0000
    bone.use_connect = False
    if parent:
        bone.parent = arm.edit_bones[parent]
    bones['neck'] = bone.name
    bone = arm.edit_bones.new('neck.001')
    bone.head[:] = 0.0000, -0.0130, 1.7197
    bone.tail[:] = 0.0000, -0.0247, 1.7813
    bone.roll = 0.0000
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['neck']]
    bones['neck.001'] = bone.name
    bone = arm.edit_bones.new('head')
    bone.head[:] = 0.0000, -0.0247, 1.7813
    bone.tail[:] = 0.0000, -0.0247, 1.9796
    bone.roll = 0.0000
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['neck.001']]
    bones['head'] = bone.name

    bpy.ops.object.mode_set(mode='OBJECT')
    pbone = obj.pose.bones[bones['neck']]
    pbone.rigify_type = 'bendy_chains.neck'
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
    pbone = obj.pose.bones[bones['neck.001']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['head']]
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
