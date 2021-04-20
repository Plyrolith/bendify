import bpy
from bpy.props import BoolProperty

from itertools import count

from rigify.utils.bones import set_bone_widget_transform, is_same_position
from rigify.utils.layers import ControlLayersOption
from rigify.utils.misc import map_list
from rigify.utils.naming import make_derived_name
from rigify.utils.widgets_basic import create_circle_widget
from rigify.utils.widgets_special import create_neck_tweak_widget
from rigify.base_rig import stage
from rigify.rigs.spines.super_head import Rig as SuperHeadRig
from rigify.rigs.widgets import create_gear_widget

from .chain_bendy_rigs import ConnectingChainBendyRig

from ...utils.bones import align_bone_between_bones
from ...utils.misc import threewise_nozip


class Rig(SuperHeadRig, ConnectingChainBendyRig):
    """
    Head rig with long bendy neck support and connect option.
    """

    def initialize(self):
        '''Don't use basic connection; bendy init, neck checks'''
        super().initialize()
        self.create_head_def = self.params.create_head_def

        # Deactivate
        self.use_connect_chain = False
        self.connected_tweak = None
        self.attach_tip = None

        ConnectingChainBendyRig.initialize(self)

        self.long_neck = len(self.bones.org) > 3
        self.has_neck = len(self.bones.org) > 1
        self.rotation_bones = []

        self.bbone_handles = 'TANGENT'

    ####################################################
    # Main control bones  

    def make_neck_widget(self, ctrl):
        '''Widget based on orgs instead of chain mch'''
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
        ctrls = self.bones.ctrl
        orgs = self.bones.org
        if self.long_neck:
            parents = [mch.tweak[0], *mch.chain, ctrls.head, ctrls.head]
        elif self.has_neck and len(orgs) == 3:
            parents = [ctrls.neck, mch.stretch, ctrls.head, ctrls.head]
        elif self.has_neck and len(orgs) == 2:
            parents = [ctrls.neck, ctrls.head, ctrls.head]
        else:
            parents = [ctrls.head, ctrls.head]
        return parents

    def check_mch_targets(self):
        return threewise_nozip(self.check_mch_parents()[:-1])

    ####################################################
    # Tweak MCH chain

    @stage.rig_bones
    def rig_tweak_mch_chain(self):
        mch = self.bones.mch
        if self.long_neck:
            targets = self.check_mch_targets()

            for i, mch_tweak, p, c, n in zip(count(0), mch.tweak[:-1], *targets):
                self.rig_tweak_mch_bone(i, mch_tweak, self.bones.ctrl.neck, p, c, n)
        
        elif self.has_neck:
            for mch_tweak in mch.tweak[:-1]:
                self.make_constraint(mch_tweak, 'COPY_SCALE', self.bones.ctrl.neck, use_make_uniform=True)
    
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
            ConnectingChainBendyRig.make_mch_chain(self)

    @stage.parent_bones
    def align_mch_chain(self):
        # Chain only for long neck
        if self.long_neck:
            ConnectingChainBendyRig.align_mch_chain(self)

    @stage.parent_bones
    def parent_mch_chain(self):
        # Chain only for long neck
        if self.long_neck:
            ConnectingChainBendyRig.parent_mch_chain(self)
    
    @stage.rig_bones
    def rig_mch_chain(self):
        # Chain only for long neck
        if self.long_neck:
            ConnectingChainBendyRig.rig_mch_chain(self)

    ####################################################
    # Tweak chain
 
    @stage.generate_bones
    def make_tweak_chain(self):
        ConnectingChainBendyRig.make_tweak_chain(self)

    @stage.parent_bones
    def parent_tweak_chain(self):
        ConnectingChainBendyRig.parent_tweak_chain(self)
    
    @stage.parent_bones
    def align_tweak_chain(self):
        if self.has_neck:
            tweak = self.bones.ctrl.tweak
            length = self.get_bone(tweak[-3]).length
            self.get_bone(tweak[-1]).length = length
            self.get_bone(tweak[-2]).length = length
        ConnectingChainBendyRig.align_tweak_chain(self)

    @stage.parent_bones
    def resize_last_tweak(self):
        ctrls = self.bones.ctrl
        last = self.get_bone(ctrls.tweak[-1])
        if len(ctrls.tweak) > 2:
            last.length = self.get_bone(ctrls.tweak[-2]).length
        else:
            last.length /= 12

    def configure_tweak_bone(self, i, tweak):
        ConnectingChainBendyRig.configure_tweak_bone(self, i, tweak)

    @stage.rig_bones
    def generate_neck_tweak_widget(self):
        # Generate the widget early to override connected parent
        if self.long_neck:
            bone = self.attach_base if self.attach_base_type == 'TWEAK' and self.attach_base else self.bones.ctrl.tweak[0]
            create_neck_tweak_widget(self.obj, bone, size=1.0)

    ##############################
    # ORG chain

    @stage.parent_bones
    def parent_org_chain(self):  
        ConnectingChainBendyRig.parent_org_chain(self)
                
    @stage.rig_bones
    def rig_org_chain(self): 
        # Head ORG
        ctrls = self.bones.ctrl
        last_org = self.bones.org[-1]
        self.make_constraint(last_org, 'COPY_TRANSFORMS', ctrls.tweak[-2])
        self.make_constraint(last_org, 'COPY_SCALE', ctrls.head)
        self.make_constraint(last_org, 'DAMPED_TRACK', ctrls.tweak[-2])
        stretch = self.make_constraint(last_org, 'STRETCH_TO', ctrls.tweak[-1])
        self.make_driver(stretch, 'bulge', variables=[(self.default_prop_bone, 'volume_deform')])

        # Rest
        if self.has_neck:
            orgs = self.bones.org[:-1]
            for org, deform in zip(orgs, self.bones.deform):
                self.make_constraint(org, 'COPY_TRANSFORMS', deform)

    ####################################################
    # Deform bones

    @stage.generate_bones
    def make_deform_chain(self):
        # Optional head DEF
        orgs = self.bones.org
        self.bones.deform = map_list(self.make_deform_bone, count(0), orgs[:-1])
        if self.create_head_def:
            self.bones.deform_head = self.make_deform_bone(0, orgs[-1])
        #self.bbone_chain_length = len(self.bones.deform) - 1 - self.create_head_def

    @stage.generate_bones
    def register_parent_bones(self):
        # Removed
        pass

    @stage.parent_bones
    def parent_deform_chain(self):
        if self.has_neck:
            ConnectingChainBendyRig.parent_deform_chain(self)
            self.set_bone_parent(self.bones.deform[0], self.bones.ctrl.neck)
        if self.create_head_def:
            self.set_bone_parent(self.bones.deform_head, self.bones.deform[0] if self.has_neck else self.bones.ctrl.neck)

    @stage.parent_bones
    def bbone_deform_chain(self):
        if self.has_neck:
            ConnectingChainBendyRig.bbone_deform_chain(self)

    @stage.rig_bones
    def rig_deform_chain(self):
        ctrls = self.bones.ctrl

        if self.create_head_def:
            self.make_constraint(self.bones.deform_head, 'COPY_TRANSFORMS', self.bones.org[-1])

        if self.has_neck:
            deforms = self.bones.deform
            tweaks = ctrls.tweak
            length = len(self.bones.deform)
            for i, deform, tweak, next_tweak in zip(count(0), deforms, tweaks, tweaks[1:]):
                ConnectingChainBendyRig.rig_deform_bone(self, deform, tweak, next_tweak, ctrls.neck)
                self.drivers_deform_roll_bone(i, deform, length)

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
        
        if i == 0 or i < length - 1:
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
        pass

    ####################################################
    # UI

    @classmethod
    def head_def_ui(self, layout, params):
        layout.row().prop(params, "create_head_def", toggle=True)

    ####################################################
    # SETTINGS

    @classmethod
    def add_parameters(self, params):
        params.create_head_def = BoolProperty(
            name='Create head DEF',
            default=True,
            description='Create a deformation bone for the head itself',
        )

    @classmethod
    def parameters_ui(self, layout, params):
        self.head_def_ui(layout, params)
        ControlLayersOption.TWEAK.parameters_ui(layout, params)

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