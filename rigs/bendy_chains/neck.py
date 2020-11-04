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
    # Utilities

    def get_parent_master(self, default_bone):
        if self.incoming_tweak and 'master' in self.rigify_parent.bones.ctrl:
            return self.rigify_parent.bones.ctrl.master
        else:
            return default_bone

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
            parents = [mch.tweak[0], *mch.chain, ctrl.head]
        elif self.has_neck:
            parents = [ctrl.neck, mch.stretch, ctrl.head]
        else:
            parents = ctrl.head
        return parents

    def check_mch_targets(self):
        return threewise_nozip(self.check_mch_parents())

    ####################################################
    # Incoming Tweak

    @stage.apply_bones
    def apply_tweak_incoming(self):
        if self.incoming_tweak and not self.incoming_tweak_mch:
            self.set_bone_parent(self.incoming_tweak, self.bones.ctrl.neck)
    
    @stage.rig_bones
    def rig_mch_tweak_incoming(self):
        if self.incoming_tweak:
            if self.incoming_tweak_mch:
                self.make_constraint(self.incoming_tweak_mch, 'COPY_LOCATION', self.bones.ctrl.neck)
            else:
                pass

    ####################################################
    # Tweak MCH chain
    
    @stage.parent_bones
    def parent_tweak_mch_chain(self):
        mch = self.bones.mch
        parents = self.check_mch_parents()

        for args in zip(count(0), mch.tweak, parents + [self.bones.ctrl.head]):
            self.parent_tweak_mch_bone(*args)

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
    # MCH IK chain for the long neck
    
    def rig_mch_ik_bone(self, i, mch, ik_len, head):
        if i == 0:
            self.make_constraint(mch, 'COPY_SCALE', self.bones.ctrl.neck, use_make_uniform=True)
        super().rig_mch_ik_bone(i, mch, ik_len, head)
    

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
        ConnectingBendyRig.make_tweak_chain(self)
    #    # No tweak for head tip
    #    orgs = self.bones.org
    #    self.bones.ctrl.tweak = map_list(self.make_tweak_bone, count(0), orgs)

    @stage.parent_bones
    def parent_tweak_chain(self):
        ConnectingBendyRig.parent_tweak_chain(self)
    
    @stage.parent_bones
    def align_tweak_chain(self):
        if self.has_neck:
            tweak = self.bones.ctrl.tweak
            length = self.get_bone(tweak[-3]).length
            self.get_bone(tweak[-1]).length = length
            self.get_bone(tweak[-2]).length = length
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
        ConnectingBendyRig.parent_org_chain(self)
        self.set_bone_parent(self.bones.org[-1], self.bones.ctrl.head)

        
    @stage.rig_bones
    def rig_org_chain(self):
        ctrl = self.bones.ctrl
        
        self.rig_org_head_bone(self.bones.org[-1], ctrl.tweak[-2], ctrl.tweak[-1])

        if self.has_neck:
            orgs = self.bones.org[:-1]
           
            for args in zip(count(0), orgs):
                self.rig_org_bone(*args, self.bones.mch.rot_neck)
    
    def rig_org_head_bone(self, org, tweak, next_tweak):
        self.make_constraint(org, 'COPY_LOCATION', tweak)
        self.make_constraint(org, 'DAMPED_TRACK', tweak)
        stretch = self.make_constraint(org, 'STRETCH_TO', next_tweak)
        self.make_driver(stretch, 'bulge', variables=[(self.bones.ctrl.master, 'volume_variation')])

    def rig_org_bone(self, i, org, target):
        ConnectingBendyRig.rig_org_bone(self, i, org, target)

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
        ctrl = self.bones.ctrl

        self.make_constraint(self.bones.deform[-1], 'COPY_TRANSFORMS', self.bones.org[-1])

        if self.has_neck:
            deforms = self.bones.deform[:-1] if self.create_head_def else self.bones.deform
            tweaks = self.bones.ctrl.tweak
            for args in zip(count(0), deforms, tweaks, tweaks[1:]):
                self.rig_deform_bone(*args, ctrl.neck)

            for i, deform in zip(count(0), deforms):
                self.drivers_deform_roll_bone(i, deform, len(self.bones.deform) - 1)

    def drivers_deform_roll_bone(self, i, deform, length):
        pbone = self.get_bone(deform)
        space = 'LOCAL_SPACE'
        v_type = 'TRANSFORMS'
        head = self.bones.ctrl.head

        ####################################################
        # Roll

        if i > 0:
            self.make_driver(
                pbone,
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
            pbone,
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

def create_sample(obj):
    # generated by rigify.utils.write_metarig
    bpy.ops.object.mode_set(mode='EDIT')
    arm = obj.data

    bones = {}

    bone = arm.edit_bones.new('neck')
    bone.head = 0.0000, 0.0114, 1.6582
    bone.tail = 0.0000, -0.0130, 1.7197
    bone.roll = 0.0000
    bone.use_connect = False
    bones['neck'] = bone.name
    bone = arm.edit_bones.new('neck.001')
    bone.head = 0.0000, -0.0130, 1.7197
    bone.tail = 0.0000, -0.0247, 1.7813
    bone.roll = 0.0000
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['neck']]
    bones['neck.001'] = bone.name
    bone = arm.edit_bones.new('head')
    bone.head = 0.0000, -0.0247, 1.7813
    bone.tail = 0.0000, -0.0247, 1.9796
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
        pbone.rigify_parameters.connect_chain = False
    except AttributeError:
        pass
    try:
        pbone.rigify_parameters.tweak_layers = [False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False]
    except AttributeError:
        pass
    try:
        pbone.rigify_parameters.incoming_tweak = True
    except AttributeError:
        pass
    try:
        pbone.rigify_parameters.incoming_align = True
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
        bone.bbone_x = bone.bbone_z = bone.length * 0.05
        arm.edit_bones.active = bone

    return bones