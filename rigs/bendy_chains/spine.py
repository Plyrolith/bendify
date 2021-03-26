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

from rigify.utils.layers import ControlLayersOption
from rigify.base_rig import stage

from rigify.rigs.spines.basic_spine import Rig as SpineRig

from .chain_bendy_rigs import ChainBendyRig

from ...utils.misc import threewise_nozip


class Rig(SpineRig, ChainBendyRig):
    """
    Bendy spine rig with fixed pivot, hip/chest controls and tweaks.
    """

    def initialize(self):
        super().initialize()
        ChainBendyRig.initialize(self)
        self.rotation_mode_end = self.params.rotation_mode_end
        self.org_transform = 'FK'

    ####################################################
    # Master control bone

    @stage.generate_bones
    def make_master_control(self):
        # Set master control as default prop bone
        super().make_master_control()
        self.default_prop_bone = self.bones.ctrl.master

    ####################################################
    # Main control bones

    @stage.configure_bones
    def configure_end_control_bones(self):
        hips_pb = self.get_bone(self.bones.ctrl.hips)
        chest_pb = self.get_bone(self.bones.ctrl.chest)
        hips_pb.rotation_mode = self.rotation_mode_end
        chest_pb.rotation_mode = self.rotation_mode_end

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
        ChainBendyRig.parent_tweak_chain(self)

    def configure_tweak_bone(self, i, tweak):
        ChainBendyRig.configure_tweak_bone(self, i, tweak)

    ####################################################
    # Deform bones

    """
    @stage.parent_bones
    def parent_deform_chain(self):
        ctrls = self.bones.ctrl
        for deform, fk in zip(self.bones.deform, ctrls.fk.hips + ctrls.fk.chest):
            self.set_bone_parent(deform, fk, use_connect=False)
    """

    @stage.rig_bones
    def rig_deform_chain(self):
        ctrls = self.bones.ctrl
        for args in zip(self.bones.deform, ctrls.tweak, ctrls.tweak[1:], ctrls.fk.hips + ctrls.fk.chest):
            ChainBendyRig.rig_deform_bone(self, *args)

    @stage.configure_bones
    def configure_bbone_chain(self):
        pass

    ##############################
    # ORG chain

    @stage.parent_bones
    def parent_org_chain(self):
        orgs = self.bones.org
        fks = self.bones.ctrl.fk
        for org, fk in zip(orgs, fks.hips + fks.chest):
            self.set_bone_parent(org, fk)
        
    ####################################################
    # UI

    def pivot_ui(self, layout, params):
        layout.row().prop(params, 'make_custom_pivot', toggle=True)
        layout.row().prop(params, 'pivot_pos', text="Pivot Position")
    
    def chest_hips_ui(self, layout, params):
        layout.row().prop(params, 'rotation_mode_end', text="Chest & Hips")
    

    ####################################################
    # SETTINGS

    @classmethod
    def add_parameters(self, params):
        super().add_parameters(params)

        params.rotation_mode_end = bpy.props.EnumProperty(
            name='Default Chest & Hip Rotation Mode',
            items=self.rotation_modes,
            default='QUATERNION',
            description='Default rotation mode for chest and hip control bones'
        )
    
    @classmethod
    def parameters_ui(self, layout, params):
        box = layout.box()
        self.pivot_ui(self, box, params)
        self.chest_hips_ui(self, box, params)
        layout.row().prop(params, 'show_advanced')
        if params.show_advanced:
            box = layout.box()
            #self.complex_stretch_ui(self, box, params)
            self.rotation_mode_tweak_ui(self, box, params)
            self.volume_ui(self, box, params)
        box = layout.box()
        self.bbones_ui(self, box, params)
        ControlLayersOption.FK.parameters_ui(layout, params)


import bpy


from mathutils import Color


def create_sample(obj):
    # generated by rigify.utils.write_metarig
    bpy.ops.object.mode_set(mode='EDIT')
    arm = obj.data

    bones = {}

    bone = arm.edit_bones.new('spine')
    bone.head = 0.0000, 0.0552, 1.0099
    bone.tail = 0.0000, 0.0172, 1.1573
    bone.roll = 0.0000
    bone.use_connect = False
    bones['spine'] = bone.name
    bone = arm.edit_bones.new('spine.001')
    bone.head = 0.0000, 0.0172, 1.1573
    bone.tail = 0.0000, 0.0004, 1.2929
    bone.roll = 0.0000
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['spine']]
    bones['spine.001'] = bone.name
    bone = arm.edit_bones.new('spine.002')
    bone.head = 0.0000, 0.0004, 1.2929
    bone.tail = 0.0000, 0.0059, 1.4657
    bone.roll = 0.0000
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['spine.001']]
    bones['spine.002'] = bone.name
    bone = arm.edit_bones.new('spine.003')
    bone.head = 0.0000, 0.0059, 1.4657
    bone.tail = 0.0000, 0.0114, 1.6582
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
        pbone.rigify_parameters.tweak_layers = [False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False]
    except AttributeError:
        pass
    try:
        pbone.rigify_parameters.bbones_easeout = True
    except AttributeError:
        pass
    try:
        pbone.rigify_parameters.bbones_easein = False
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
        bone.bbone_x = bone.bbone_z = bone.length * 0.05
        arm.edit_bones.active = bone

    return bones