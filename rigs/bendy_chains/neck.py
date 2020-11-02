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
from rigify.utils.widgets_basic import create_circle_widget
from rigify.utils.widgets_special import create_neck_tweak_widget
from rigify.base_rig import stage
from rigify.rigs.spines.super_head import Rig as SuperHeadRig

from .bendy_chain_rigs import ConnectingBendyRig

from ...utils.misc import threewise_nozip


class Rig(SuperHeadRig, ConnectingBendyRig):
    """
    Head rig with long bendy neck support and connect option.
    """


    def initialize(self):
        # Don't use basic connection, bendy init, neck checks
        self.create_head_def = self.params.create_head_def
        self.use_connect_chain = False
        self.connected_tweak = None

        ConnectingBendyRig.initialize(self)

        self.long_neck = len(self.bones.org) > 3
        self.has_neck = len(self.bones.org) > 1
        self.rotation_bones = []
    
    def prepare_bones(self):
        ConnectingBendyRig.prepare_bones(self)

    ####################################################
    # Main control bones   

    @stage.parent_bones
    def parent_master_control(self):
        self.set_bone_parent(self.bones.ctrl.master, self.bones.mch.rot_neck)

    def make_neck_widget(self, ctrl):
        # Widget based on orgs instead of chain mch
        radius = 1/max(1, len(self.bones.org[1:-1]))

        create_circle_widget(
            self.obj, ctrl,
            radius=radius,
            head_tail=0.5,
        )

    ####################################################
    # Tweak Targets

    def check_mch_parents(self):
        mch = self.bones.mch
        ctrl = self.bones.ctrl
        if self.long_neck:
            parents = mch.chain
        elif self.has_neck:
            parents = [ctrl.neck, mch.stretch, ctrl.head]
        else:
            parents = ctrl.head
        return parents

    def check_mch_targets(self):
        return threewise_nozip(self.check_mch_parents())


    ####################################################
    # Tweak MCH chain
    
    @stage.generate_bones
    def make_tweak_mch_chain(self):
        # No mch for head tip
        orgs = self.bones.org
        self.bones.mch.tweak = map_list(self.make_tweak_mch_bone, count(0), orgs)

    @stage.rig_bones
    def rig_tweak_mch_chain(self):
        if self.long_neck:
            ConnectingBendyRig.rig_tweak_mch_chain(self)
        elif self.has_neck:
            mch = self.bones.mch
            ctrl = self.bones.ctrl
            for mch_tweak in mch.tweak:
                self.make_constraint(mch_tweak, 'COPY_SCALE', ctrl.master, use_make_uniform=True) 

    ####################################################
    # MCH chain for the middle of the neck

    @stage.generate_bones
    def make_mch_chain(self):
        # Chain only for long neck
        if self.long_neck:
            super().make_mch_chain()

    @stage.parent_bones
    def align_mch_chain(self):
        # Chain only for long neck
        if self.long_neck:
            super().align_mch_chain()

    @stage.parent_bones
    def parent_mch_chain(self):
        # Chain only for long neck
        if self.long_neck:
            super().parent_mch_chain()
    
    @stage.rig_bones
    def rig_mch_chain(self):
        # Chain only for long neck
        if self.long_neck:
            super().rig_mch_chain()

    ####################################################
    # Tweak chain
 
    @stage.generate_bones
    def make_tweak_chain(self):
        # No tweak for head tip
        orgs = self.bones.org
        self.bones.ctrl.tweak = map_list(self.make_tweak_bone, count(0), orgs)

    @stage.parent_bones
    def parent_tweak_chain(self):
        ConnectingBendyRig.parent_tweak_chain(self)
    
    @stage.parent_bones
    def align_tweak_chain(self):
        ConnectingBendyRig.align_tweak_chain(self)

    @stage.parent_bones
    def resize_last_tweak(self):
        ctrl = self.bones.ctrl
        last = self.get_bone(ctrl.tweak[-1])
        if len(ctrl.tweak) > 2:
            last.length = self.get_bone(ctrl.tweak[-2]).length
        else:
            last.length /= 12

    def configure_tweak_bone(self, i, tweak):
        ConnectingBendyRig.configure_tweak_bone(self, i, tweak)

    @stage.rig_bones
    def generate_neck_tweak_widget(self):
        # Generate the widget early to override connected parent
        if self.long_neck:
            bone = self.incoming_tweak or self.bones.ctrl.tweak[0]
            create_neck_tweak_widget(self.obj, bone, size=1.0)

    ##############################
    # ORG chain
    @stage.parent_bones
    def parent_org_chain(self):  
        orgs = self.bones.org
        if self.has_neck:
            for mch, org in zip(self.bones.mch.tweak, orgs):
                self.set_bone_parent(org, mch)
        else:
            self.set_bone_parent(orgs[0], self.bones.ctrl.head)
        
    @stage.rig_bones
    def rig_org_chain(self):
        if self.has_neck:
            orgs = self.bones.org
            if not self.create_head_def:
                orgs = self.bones.org[:-1]
                self.rig_deform_head(
                    self.bones.org[-1],
                    self.bones.ctrl.head,
                    self.bones.ctrl.tweak[-1]
                )

            for args in zip(count(0), orgs, self.bones.deform):
                self.rig_org_bone(*args)
    
    def rig_org_bone(self, i, org, deform):
        self.make_constraint(org, 'COPY_SCALE', self.bones.mch.rot_neck)
        ConnectingBendyRig.rig_org_bone(self, i, org, deform)

    ####################################################
    # Deform bones

    @stage.generate_bones
    def make_deform_chain(self):
        # Optional head DEF
        orgs = self.bones.org if self.create_head_def else self.bones.org[:-1]
        self.bones.deform = map_list(self.make_deform_bone, count(0), orgs)
        self.bbone_chain_length = len(self.bones.deform) - 1 - self.create_head_def

    @stage.generate_bones
    def register_parent_bones(self):
        # Removed
        pass

    @stage.parent_bones
    def parent_deform_chain(self):
        ConnectingBendyRig.parent_deform_chain(self)

    @stage.parent_bones
    def ease_deform_chain(self):
        if self.has_neck:
            ConnectingBendyRig.ease_deform_chain(self)

    @stage.rig_bones
    def rig_deform_chain(self):
        if self.has_neck:
            tweaks = self.bones.ctrl.tweak
            for args in zip(count(0), self.bones.deform, tweaks, tweaks[1:]):
                self.rig_deform_bone(*args)

        deforms = self.bones.deform

        if self.create_head_def:
            self.rig_deform_head(
                self.bones.deform[-1],
                self.bones.ctrl.head,
                self.bones.ctrl.tweak[-1]
            )
            deforms = self.bones.deform[:-1]

        for i, deform in zip(count(0), deforms):
            self.drivers_deform_roll_bone(i, deform, len(self.bones.deform) - 1)

    def rig_deform_head(self, bone, ctrl, tweak):
        self.make_constraint(bone, 'COPY_ROTATION', ctrl)
        self.make_constraint(bone, 'COPY_LOCATION', tweak)
        self.make_constraint(bone, 'COPY_SCALE', ctrl)
        self.make_constraint(bone, 'DAMPED_TRACK', ctrl, head_tail=1)
        self.make_constraint(bone, 'STRETCH_TO', ctrl, head_tail=1)

    def drivers_deform_roll_bone(self, i, deform, length):
        pbone = self.get_bone(deform)
        space = 'LOCAL_SPACE'
        v_type = 'TRANSFORMS'
        head = self.bones.ctrl.head

        ####################################################
        # Roll

        if i > 0:
            self.make_driver(
                pbone.bone,
                'bbone_rollin',
                expression='swing_out * ' + str(i) + ' / ' + str(length),
                variables={
                    'swing_out': {
                        'type': v_type,
                        'targets':
                        [
                            {
                                'id': self.obj,
                                'bone_target': head,
                                'transform_type': 'ROT_Y',
                                'rotation_mode': 'SWING_TWIST_Y',
                                'transform_space': space,
                            }
                        ]
                    }
                }
            )
        
        self.make_driver(
            pbone.bone,
            'bbone_rollout',
            expression='swing_out * ' + str(i + 1) + ' / ' + str(length),
            variables={
                'swing_out': {
                    'type': v_type,
                    'targets':
                    [
                        {
                            'id': self.obj,
                            'bone_target': head,
                            'transform_type': 'ROT_Y',
                            'rotation_mode': 'SWING_TWIST_Y',
                            'transform_space': space,
                        }
                    ]
                }
            }
        )

    @stage.configure_bones
    def configure_bbone_chain(self):
        if self.create_head_def:
            super().configure_bbone_chain()

    ####################################################
    # SETTINGS
    
    @stage.configure_bones
    def configure_armature_display(self):
        # New function to set rig viewport display
        self.obj.data.display_type = 'BBONE'

    @classmethod
    def add_parameters(self, params):
        params.create_head_def = bpy.props.BoolProperty(
            name='Create head DEF',
            default=True,
            description='Create a deformation bone for the head itself'
        )

    @classmethod
    def parameters_ui(self, layout, params):
        r = layout.row()
        r.prop(params, "create_head_def", toggle=True)

        ConnectingBendyRig.parameters_ui(layout, params)

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
