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
from rigify.utils.bones import align_bone_orientation, align_bone_roll, align_bone_x_axis, align_bone_y_axis, put_bone, set_bone_widget_transform
from rigify.utils.widgets_basic import create_circle_widget
from rigify.rigs.widgets import create_ballsocket_widget, create_gear_widget

from rigify.rigs.chain_rigs import TweakChainRig

from ...utils.bones import align_bone, distance
from ...utils.misc import threewise_nozip
from ...utils.widgets_bendy import create_sub_tweak_widget

class BaseBendyRig(TweakChainRig):
    """
    Base bendy rig
    """

    min_chain_length = 1

    def initialize(self):
        # Bbone segments
        super().initialize()
        self.rotation_mode_tweak = self.params.rotation_mode_tweak
        self.bbone_segments = self.params.bbones_spine
        self.bbone_easein = self.params.bbones_easein
        self.bbone_easeout = self.params.bbones_easeout
        self.org_transform = self.params.org_transform
        self.bbone_chain_length = 0
        self.keep_axis = 'SWING_Y'
        
        self.root_bone = self.get_bone(self.bones.org[0]).parent.name if self.get_bone(self.bones.org[0]).parent else "root"
        self.default_prop_bone = None

    ####################################################
    # Master control

    @stage.configure_bones
    def configure_master_properties(self):
        ctrls = self.bones.ctrl
        master = self.default_prop_bone
        panel = self.script.panel_with_selected_check(self, ctrls.flatten())
        self.make_property(master, 'volume_variation', default=1.0, max=100.0, soft_max=1.0, description='Volume variation for DEF bones')
        panel.custom_prop(master, 'volume_variation', text='Volume Variation', slider=True)

    ##############################
    # Control chain

    @stage.generate_bones
    def make_control_chain(self):
        '''Add first FK as default_prop_bone'''
        self.bones.ctrl.fk = map_list(self.make_control_bone, count(0), self.bones.org)
        self.default_prop_bone = self.bones.ctrl.fk[0]

    @stage.parent_bones
    def parent_control_chain(self):
        '''Disconnect controls, first to root_bone'''
        self.parent_bone_chain(self.bones.ctrl.fk, use_connect=False)
        self.set_bone_parent(self.bones.ctrl.fk[0], self.root_bone)

    ####################################################
    # Tweak Targets

    def check_mch_parents(self):
        '''Return array of parents for Tweak MCHs'''
        ctrls = self.bones.ctrl
        return ctrls.fk + ctrls.fk[-1:]

    def check_mch_targets(self):
        '''Return array of triple target lists (previous, current & next tweak MCH)'''
        ctrls = self.bones.ctrl
        mch = self.bones.mch
        return threewise_nozip([*ctrls.fk, mch.tweak[-1]])
    
    ####################################################
    # Tweak MCH chain

    @stage.generate_bones
    def make_tweak_mch_chain(self):
        '''Create (new) MCH bones for tweaks'''
        orgs = self.bones.org
        self.bones.mch.tweak = map_list(self.make_tweak_mch_bone, count(0), orgs + orgs[-1:])

    def make_tweak_mch_bone(self, i, org):
        '''Tweak MCH creation loop'''
        name = make_derived_name(org, 'mch', '_tweak')
        name = self.copy_bone(org, name, parent=False, scale=0.5)

        if i == len(self.bones.org):
            put_bone(self.obj, name, self.get_bone(org).tail)
        
        return name

    @stage.parent_bones
    def parent_tweak_mch_chain(self):
        '''Parent tweak MCH to CTRL chain and realign'''
        mch = self.bones.mch
        parents = self.check_mch_parents()

        for args in zip(count(0), mch.tweak, parents):
            self.parent_tweak_mch_bone(*args)

    def parent_tweak_mch_bone(self, i, mch, parent):
        '''Parent tweak MCH'''
        self.set_bone_parent(mch, parent)
        self.get_bone(mch).inherit_scale = 'NONE'

    @stage.parent_bones
    def align_tweak_mch_chain(self):
        '''Align tweak MCH between current and next MCH'''
        mch = self.bones.mch
        targets = self.check_mch_targets()
        
        for args in zip(mch.tweak, *targets):
            align_bone(self.obj, *args)
    
    @stage.rig_bones
    def rig_tweak_mch_chain(self):
        '''Create tweak MCH constraints'''
        mch = self.bones.mch
        parents = self.check_mch_parents()
        targets = self.check_mch_targets()

        for args in zip(count(0), mch.tweak, parents, *targets):
            self.rig_tweak_mch_bone(*args)

    def rig_tweak_mch_bone(self, i, mch, scale_bone, prev_target, curr_target, next_target):
        '''Constraints to calculate tangent rotation between previous and next chain targets'''
        if prev_target and next_target:
            self.make_constraint(mch, 'COPY_LOCATION', prev_target)
            self.make_constraint(mch, 'STRETCH_TO', next_target, bulge=0, volume='NO_VOLUME', keep_axis=self.keep_axis)
            self.make_constraint(mch, 'COPY_LOCATION', curr_target)
        self.make_constraint(mch, 'COPY_SCALE', scale_bone, use_make_uniform=True)

    ####################################################
    # Tweak chain

    @stage.parent_bones
    def parent_tweak_chain(self):
        '''Parent tweaks to tweak MCHs'''
        ctrls = self.bones.ctrl
        mch = self.bones.mch
        for args in zip(count(0), ctrls.tweak, mch.tweak):
            self.parent_tweak_bone(*args)

    def parent_tweak_bone(self, i, tweak, parent):
        '''Parent tweak'''
        self.set_bone_parent(tweak, parent)

    @stage.parent_bones
    def align_tweak_chain(self):
        '''Align tweaks between previous and next CTRL'''
        ctrls = self.bones.ctrl
        targets = self.check_mch_targets()
        
        for args in zip(ctrls.tweak, *targets):
            align_bone(self.obj, *args)   

    @stage.configure_bones
    def configure_tweak_chain(self):
        super().configure_tweak_chain()

        ControlLayersOption.TWEAK.assign(self.params, self.obj, self.bones.ctrl.tweak)

    def configure_tweak_bone(self, i, tweak):
        '''Fully unlocked tweaks'''
        tweak_pb = self.get_bone(tweak)
        tweak_pb.rotation_mode = self.rotation_mode_tweak

    ##############################
    # ORG chain

    @stage.parent_bones
    def parent_org_chain(self):
        '''Parent ORGs to FKs'''
        for org, fk in zip(self.bones.org, self.bones.ctrl.fk):
            self.set_bone_parent(org, fk)

    @stage.rig_bones
    def rig_org_chain(self):
        '''Set ORG transformation according to rig setting'''
        ctrls = self.bones.ctrl
        for org, deform, tweak, next_tweak in zip(self.bones.org, self.bones.deform, ctrls.tweak, ctrls.tweak[1:]): #, ctrls.fk):
            if self.org_transform == 'TWEAKS':
                self.make_constraint(org, 'COPY_TRANSFORMS', deform)
                self.make_constraint(org, 'COPY_SCALE', tweak, use_y=False, power=0.5, use_offset=True, target_space='LOCAL', owner_space='LOCAL')
                self.make_constraint(org, 'COPY_SCALE', next_tweak, use_y=False, power=0.5, use_offset=True, target_space='LOCAL', owner_space='LOCAL')
            elif self.org_transform == 'TWEAK':
                self.make_constraint(org, 'COPY_TRANSFORMS', deform)
                self.make_constraint(org, 'COPY_SCALE', tweak, use_y=False, use_offset=True, target_space='LOCAL', owner_space='LOCAL')
            elif self.org_transform == 'DEF':
                self.make_constraint(org, 'COPY_TRANSFORMS', deform)
            #elif self.org_transform == 'FK':
            #    self.make_constraint(org, 'COPY_TRANSFORMS', fk)

    ####################################################
    # Deform bones

    @stage.generate_bones
    def make_deform_chain(self):
        '''Set bbone chain length'''
        super().make_deform_chain()
        self.bbone_chain_length = len(self.bones.deform) - 1

    @stage.parent_bones
    def parent_deform_chain(self):
        '''Parent DEFs to FKs'''
        for deform, fk in zip(self.bones.deform, self.bones.ctrl.fk):
            self.set_bone_parent(deform, fk)

    @stage.parent_bones
    def ease_deform_chain(self):
        '''Set bbone easing in edit mode'''
        tweaks = self.bones.ctrl.tweak

        for args in zip(count(0), self.bones.deform, tweaks, tweaks[1:]):
            self.ease_deform_bone(*args)
        
    def ease_deform_bone(self, i, deform, tweak, next_tweak):
        '''Easing per bone'''
        pbone = self.get_bone(deform)
        pbone.bbone_segments = self.bbone_segments
        pbone.bbone_handle_type_start = 'TANGENT'
        pbone.bbone_handle_type_end = 'TANGENT'
        pbone.bbone_custom_handle_start = self.get_bone(tweak)
        pbone.bbone_custom_handle_end = self.get_bone(next_tweak)
        pbone.bbone_easein = 0.0 if i == 0 and not self.bbone_easein else 1.0
        pbone.bbone_easeout = 0.0 if i == self.bbone_chain_length and not self.bbone_easeout else 1.0

    @stage.rig_bones
    def rig_deform_chain(self):
        '''DEF constraint chain'''
        ctrls = self.bones.ctrl
        for args in zip(count(0), self.bones.deform, ctrls.tweak, ctrls.tweak[1:], ctrls.fk):
            self.rig_deform_bone(*args)
    
    def rig_deform_bone(self, i, deform, tweak, next_tweak, fk):
        '''DEF constraints'''
        self.make_constraint(deform, 'COPY_TRANSFORMS', tweak)
        self.make_constraint(deform, 'COPY_SCALE', fk)
        self.make_constraint(deform, 'DAMPED_TRACK', next_tweak)
        stretch = self.make_constraint(deform, 'STRETCH_TO', next_tweak)
        self.drivers_deform_bone(i, deform, stretch, tweak, next_tweak)

    def drivers_deform_bone(self, i, deform, stretch, tweak, next_tweak):
        '''New function to create bendy bone drivers'''
        pbone = self.get_bone(deform)
        space = 'LOCAL_SPACE'
        v_type = 'TRANSFORMS'

        ####################################################
        # Volume Variation

        self.make_driver(stretch, 'bulge', variables=[(self.default_prop_bone, 'volume_variation')])

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
    # SETTINGS
    
    @stage.configure_bones
    def configure_armature_display(self):
        '''New function to set rig viewport display'''
        self.obj.data.display_type = 'BBONE'
    
    @classmethod
    def add_parameters(self, params):
        '''Added more parameters'''

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

        params.rotation_mode_tweak = bpy.props.EnumProperty(
            name="Default Tweak Controller Rotation Mode",
            items=rotation_modes,
            default='ZXY',
            description="Default rotation mode for tweak control bones"
        )

        params.bbones_spine = bpy.props.IntProperty(
            name="B-Bone Segments",
            default=8,
            min=1,
            max=32,
            description="Number of B-Bone segments"
        )

        params.bbones_easein = bpy.props.BoolProperty(
            name="B-Bone Ease In",
            default=True,
            description="B-Bone Easing in for First Bone of Chain"
        )

        params.bbones_easeout = bpy.props.BoolProperty(
            name="B-Bone Ease Out",
            default=True,
            description="B-Bone Easing out for Last Bone of Chain"
        )

        params.org_transform = bpy.props.EnumProperty(
            name="ORG Transform base",
            items=[
                ('FK', "FK", "FK"),
                ('DEF', "Deforms", "Deforms"),
                ('TWEAK', "Single Tweak", "Single Tweak"),
                ('TWEAKS', "Between Tweaks", "BetweenTweaks"),
            ],
            default='FK',
            description="Source of ORG transformation; useful to determine children's behaviour"
        )

    @classmethod
    def parameters_ui(self, layout, params):
        '''More modes'''
        layout.row().prop(params, 'rotation_mode_tweak', text="Tweaks")
        layout.row().prop(params, 'org_transform', text="ORGs")
        layout.row().prop(params, 'bbones_spine')

        r = layout.row(align=True)
        r.prop(params, 'bbones_easein', text="Ease In", toggle=True)
        r.prop(params, 'bbones_easeout', text="Ease Out", toggle=True)

        ControlLayersOption.TWEAK.parameters_ui(layout, params)


# Combine between the following

class SegmentedBendyRig(BaseBendyRig):
    """
    Bendy chain with indivdually scaling fk segments
    """

    ##############################
    # Utilities

    def copy_scale_bone(self):
        if hasattr(self.bones.ctrl, 'master'):
            return self.bones.ctrl.master
        elif hasattr(self.bones.mch, 'rot'):
            return self.bones.mch.rot
        elif hasattr(self.bones.mch, 'parent'):
            return self.bones.mch.parent
        else:
            return self.root_bone

    ####################################################
    # Control chain

    @stage.parent_bones
    def parent_control_chain(self):
        for fk, parent in zip(self.bones.ctrl.fk, self.bones.mch.fk):
            self.set_bone_parent(fk, parent)

    ####################################################
    # FK MCH chain

    @stage.generate_bones
    def make_fk_mch_chain(self):
        # Create (new) mch bones for controllers
        self.bones.mch.fk = map_list(self.make_fk_mch_bone, count(0), self.bones.org)

    def make_fk_mch_bone(self, i, org):
        # FK mch creation loop
        name = make_derived_name(org, 'mch')
        name = self.copy_bone(org, name, parent=False)
        
        return name

    @stage.parent_bones
    def parent_fk_mch_chain(self):
        for mch, parent in zip(self.bones.mch.fk, [self.root_bone] + self.bones.ctrl.fk):
            self.set_bone_parent(mch, parent, inherit_scale='NONE')

    @stage.rig_bones
    def rig_fk_mch_chain(self):
        ctrls = self.bones.ctrl
        for mch in self.bones.mch.fk:
            self.make_constraint(mch, 'COPY_SCALE', self.root_bone)

            # Add master control constraint if necessary
            if hasattr(self, 'master_control') and self.master_control == 'ROTATION' and len(ctrls.fk) > 1:
                self.make_constraint(mch, 'COPY_ROTATION', ctrls.master, space='LOCAL')

    ####################################################
    # Tweak MCH chain

    @stage.rig_bones
    def rig_tweak_mch_chain(self):
        # Create tweak mch constraints
        mch = self.bones.mch
        targets = self.check_mch_targets()

        for i, mch, p, c, n in zip(count(0), mch.tweak, *targets):
            self.rig_tweak_mch_bone(i, mch, self.copy_scale_bone() or self.root_bone, p, c, n)

    ####################################################
    # Deform bones

    def rig_deform_bone(self, i, deform, tweak, next_tweak, fk):
        # Constraints/drivers for segmented scaling
        self.make_constraint(deform, 'COPY_TRANSFORMS', tweak)
        self.make_constraint(deform, 'COPY_SCALE', self.copy_scale_bone() or self.root_bone)
        counter_volume = self.make_constraint(deform, 'COPY_SCALE', fk, use_offset=True, use_y=False, target_space='LOCAL', owner_space='LOCAL')
        self.make_constraint(deform, 'DAMPED_TRACK', next_tweak)
        stretch = self.make_constraint(deform, 'STRETCH_TO', next_tweak)
        self.drivers_deform_bone(i, deform, stretch, tweak, next_tweak)

        self.make_driver(counter_volume, 'power', expression='1 - var * 0.5', variables=[(self.default_prop_bone, 'volume_variation')])

        # Add master control constraint if necessary
        if hasattr(self, 'master_control') and not self.master_control == 'NONE':
            self.make_constraint(deform, 'COPY_SCALE', self.bones.ctrl.master, use_y=False, use_offset=True, target_space='LOCAL', owner_space='LOCAL')


class ConnectingBendyRig(BaseBendyRig):
    """
    Bendy rig that can connect to a (tweak of its) parent, as well as attach its tip to another bone.
    """

    def initialize(self):
        super().initialize()

        self.incoming = self.params.incoming
        self.tip_parent_bone = self.params.tip_parent_bone
        self.tip_scale = self.params.tip_scale
        self.tip_scale_uniform = self.params.tip_scale_uniform
        self.incoming_tweak = None
        self.incoming_parent = None
        self.first_bone_matrix = None
        self.first_bone_length = None
        self.first_bone_x_axis = None
        self.first_bone_y_axis = None
        
    def prepare_bones(self):
        '''Find connection parent'''
        first_bone = self.get_bone(self.bones.org[0])
        if not self.incoming == 'NONE' and hasattr(self, 'rigify_parent') and self.rigify_parent:
            self.incoming_parent = self.get_bone(self.bones.org[0]).parent.name

            # Match position of first bone head if desired
            match = ('PARENT', 'TWEAK', 'MERGE')
            if self.incoming in match:

                self.first_bone_matrix = first_bone.matrix
                self.first_bone_length = first_bone.length
                self.first_bone_x_axis = first_bone.x_axis
                self.first_bone_y_axis = first_bone.y_axis

                x_axis = first_bone.x_axis
                d_head = (first_bone.head - first_bone.parent.head).length
                d_tail = (first_bone.head - first_bone.parent.tail).length
                if d_head < d_tail:
                    first_bone.head = first_bone.parent.head
                else:
                    first_bone.head = first_bone.parent.tail
                # Fix roll
                align_bone_x_axis(self.obj, self.bones.org[0], x_axis)

    ####################################################
    # Control chain

    @stage.parent_bones
    def position_first_control(self):
        '''Restore bone positions if first head was moved'''
        if self.first_bone_matrix and self.first_bone_length:
            if self.org_transform == 'FK':
                first_org = self.get_bone(self.bones.org[0])
                first_org.matrix = self.first_bone_matrix
                first_org.length = self.first_bone_length
            if hasattr(self.bones.ctrl, 'fk'):
                first_fk = self.get_bone(self.bones.ctrl.fk[0])
                first_fk.matrix = self.first_bone_matrix
                first_fk.length = self.first_bone_length
            if hasattr(self.bones.mch, 'fk'):
                first_mch = self.get_bone(self.bones.mch.fk[0])
                first_mch.matrix = self.first_bone_matrix
                first_mch.length = self.first_bone_length
            if hasattr(self.bones.ctrl, 'master'):
                master = self.get_bone(self.bones.ctrl.master)
                master.matrix = self.first_bone_matrix
                master.length = self.first_bone_length
            #Align tip with original position if chain has only one segment
            if len(self.bones.org) == 1:
                align_bone_y_axis(self.obj, self.bones.mch.tweak[-1], self.first_bone_y_axis)
                align_bone_x_axis(self.obj, self.bones.mch.tweak[-1], self.first_bone_x_axis)
                align_bone_y_axis(self.obj, self.bones.ctrl.tweak[-1], self.first_bone_y_axis)
                align_bone_x_axis(self.obj, self.bones.ctrl.tweak[-1], self.first_bone_x_axis)

    ####################################################
    # Tweak chain

    @stage.parent_bones
    def check_incoming_tweak(self):
        '''Check for nearest Tweak of parent and move first org head there'''
        move = ('TWEAK', 'MERGE')
        first_bone = self.bones.org[0]
        if self.incoming in move and hasattr(self, 'rigify_parent'):
            parent = self.rigify_parent
            if parent and hasattr(parent.bones, 'ctrl') and hasattr(parent.bones.ctrl, 'tweak'):
                parent_tweaks = parent.bones.ctrl.tweak
                delta = distance(self.obj, first_bone, parent_tweaks[0])
                self.incoming_tweak = parent_tweaks[0]
                for tweak in parent_tweaks:
                    dist = distance(self.obj, first_bone, tweak)
                    if dist < delta:
                        delta = dist
                        self.incoming_tweak = tweak
                
                # Merge align
                if self.incoming_tweak and self.incoming == 'MERGE':
                    bone_in = self.get_bone(self.incoming_tweak)
                    first_tweak = self.bones.ctrl.tweak[0]
                    first_tweak_mch = self.bones.mch.tweak[0]

                    if self.incoming_tweak == parent_tweaks[0]:
                        vec = bone_in.head - bone_in.tail

                    elif self.incoming_tweak == parent_tweaks[-1]:
                        vec = bone_in.tail - bone_in.head

                    align_bone_y_axis(self.obj, first_tweak, vec)
                    align_bone_y_axis(self.obj, first_tweak_mch, vec)
                    align_bone_roll(self.obj, first_tweak, self.incoming_tweak)
                    align_bone_roll(self.obj, first_tweak_mch, self.incoming_tweak)

    @stage.rig_bones
    def rig_tweak_chain(self):
        '''Copy scale offset for connected tweak'''
        if self.incoming_tweak and self.incoming == 'MERGE':
            if len(self.rigify_parent.bones.ctrl.tweak) > 1:
                self.make_constraint(self.bones.ctrl.tweak[0], 'COPY_SCALE', self.incoming_tweak, use_offset=True, target_space='LOCAL', owner_space='LOCAL')

        # Tip scale offset
        if self.tip_parent_bone and self.tip_parent_bone in self.obj.pose.bones:
            self.make_constraint(
                self.bones.ctrl.tweak[-1],
                'COPY_SCALE',
                self.tip_parent_bone,
                use_make_uniform=self.tip_scale_uniform,
                use_offset=True,
                target_space='LOCAL',
                owner_space='LOCAL'
            )

    @stage.generate_widgets
    def make_tweak_widgets(self):
        '''Connecting tweak widget'''
        tweaks = self.bones.ctrl.tweak

        if self.incoming_tweak:
            create_sub_tweak_widget(self.obj, tweaks[0], size=0.25)
            tweaks = tweaks[1:]
        
        for tweak in tweaks:
            super().make_tweak_widget(tweak)

    ####################################################
    # Tweak MCH chain

    @stage.apply_bones
    def parent_tweak_mch_apply(self):
        '''Re-parent first and tip tweak MCH'''
        mch = self.bones.mch.tweak[0]

        if self.incoming_tweak:
            # Parent first tweak MCH to incoming tweak
            self.set_bone_parent(mch, self.incoming_tweak)
            #self.get_bone(self.incoming_tweak).length = self.get_bone(mch).length
        
        elif self.incoming_parent:
            # If not tweak, parent to actual parent
            self.set_bone_parent(mch, self.incoming_parent)
        
        elif not self.incoming == 'NONE':
            # Without parent use root
            self.set_bone_parent(mch, self.root_bone)
        
        # Re-parent tip tweak mch
        if self.tip_parent_bone and self.tip_parent_bone in self.obj.data.edit_bones:
            mch = self.bones.mch.tweak[-1]
            self.set_bone_parent(mch, self.tip_parent_bone)

    ##############################
    # Settings

    @classmethod
    def add_parameters(self, params):
        super().add_parameters(params)

        params.incoming = bpy.props.EnumProperty(
            items=[
                ('NONE', "Free", "Free"),
                ('ATTACH', "Attach to Parent", "Attach first tweak to parent without moving"),
                ('PARENT', "Connect to Parent", "Connect first tweak to parent"),
                ('TWEAK', "Connect to Tweak", "Connect to closest parent tweak"),
                ('MERGE', "Merge Tweaks & Align", "Merge with closest parent tweak and align for a smooth curve")
            ],
            name="First Tweak",
            default='NONE',
            description="Connection point for the first tweak of the B-Bone chain"
        )

        params.incoming_tweak = bpy.props.BoolProperty(
            name="Connect Tweaks",
            default=False,
            description="Connect the B-Bone chain to the nearest parent tweak"
        )

        params.tip_parent_bone = bpy.props.StringProperty(
            name="Tip Parent",
            default="",
            description="Parent for the tip tweak; leave empty for regular chain hierarchy"
        )

        params.tip_scale = bpy.props.BoolProperty(
            name="Tip Scale Offset",
            default=True,
            description="Add copy scale constraint to tip tweak, offsetting it by its parent's scale"
        )

        params.tip_scale_uniform = bpy.props.BoolProperty(
            name="Make Uniform",
            default=False,
            description="Make tip scale offset uniform"
        )

    @classmethod
    def parameters_ui(self, layout, params):
        layout.row().prop(params, 'incoming')
        layout.row().prop(params, 'tip_parent_bone')

        split = layout.split(align=True)
        r = split.row(align=True)
        r.prop(params, 'tip_scale', toggle=True)
        if not params.tip_parent_bone:
            r.enabled = False
        r = split.row(align=True)
        r.prop(params, 'tip_scale_uniform', toggle=True)
        if not params.tip_parent_bone or not params.tip_scale:
            r.enabled = False
        super().parameters_ui(layout, params)


class MasterControlBendyRig(BaseBendyRig):
    """
    Connecting Bendy with a master controller.
    """

    def initialize(self):
        super().initialize()

        self.master_control = self.params.master_control

    ####################################################
    # Master control

    @stage.generate_bones
    def make_master_control(self):
        if not self.master_control == 'NONE':
            org = self.bones.org[0]
            self.bones.ctrl.master = self.copy_bone(org, make_derived_name(org, 'ctrl', '_master'))
    
    @stage.parent_bones
    def parent_master_control(self):
        if not self.master_control == 'NONE':
            self.set_bone_parent(self.bones.ctrl.master, self.root_bone)

    @stage.configure_bones
    def configure_master_control(self):
        if not self.master_control == 'NONE':
            master = self.bones.ctrl.master
            bone = self.get_bone(master)
            bone.lock_location = (True, True, True)
            bone.lock_scale = (False, True, False)

            if self.master_control == 'SCALE':
                bone.lock_rotation = (True, True, True)
                bone.lock_rotation_w = True

    @stage.generate_widgets
    def make_master_control_widget(self):
        if not self.master_control == 'NONE':
            ctrls = self.bones.ctrl
            bone = ctrls.master
            if self.master_control == 'ROTATION':
                create_ballsocket_widget(self.obj, bone, size=0.7)
                transform = ctrls.fk[-1] if self.tip_parent_bone else ctrls.tweak[-1]
            else:
                create_gear_widget(self.obj, bone, size=4)
                transform = ctrls.fk[0]
            set_bone_widget_transform(self.obj, bone, transform)
    
    ####################################################
    # Control chain

    @stage.rig_bones
    def rig_control_chain(self):
        '''Add master control constraints if no MCH found'''
        if not self.master_control == 'NONE' and not hasattr(self.bones.mch, 'fk'):
            for ctrl in self.bones.ctrl.fk:
                self.make_constraint(ctrl, 'COPY_ROTATION', self.bones.ctrl.master, mix_mode='BEFORE', target_space='LOCAL', owner_space='LOCAL')

    ####################################################
    # Deform chain

    def rig_deform_bone(self, i, deform, tweak, next_tweak, fk):
        super().rig_deform_bone(i, deform, tweak, next_tweak, fk)
        if not self.master_control == 'NONE':
            self.make_constraint(deform, 'COPY_SCALE', self.bones.ctrl.master, use_y=False, use_offset=True, target_space='LOCAL', owner_space='LOCAL')

    ####################################################
    # SETTINGS

    @classmethod
    def add_parameters(self, params):
        super().add_parameters(params)

        params.master_control = bpy.props.EnumProperty(
            items=[
                ('NONE', "None", "None"),
                ('SCALE', "Scale", "Scale"),
                ('ROTATION', "Rotation & Scale", "Rotation & Scale"),
            ],
            name="Master Control",
            description="Add master controller for the whole chain",
            default='NONE'
            )

    @classmethod
    def parameters_ui(self, layout, params):
        layout.row().prop(params, "master_control")

        super().parameters_ui(layout, params)


class ParentSwitchBendyRig(BaseBendyRig):
    """
    Connecting Bendy switchable parenting.
    """

    ####################################################
    # Parent MCH

    @stage.generate_bones
    def make_parent_mch(self):
        org = self.bones.org[0]
        self.bones.mch.parent = self.copy_bone(org, make_derived_name(strip_org(org), 'mch', '.parent'))

        # Check if self is a RotMechBendyRig and only set root if that's the case
        if not hasattr(self, 'rotation_bones'):
            self.root_bone = self.bones.mch.parent

    @stage.parent_bones
    def parent_parent_mch(self):
        self.set_bone_parent(self.bones.mch.parent, self.rig_parent_bone, inherit_scale='FIX_SHEAR')


class RotMechBendyRig(BaseBendyRig):
    """
    Connecting Bendy rig that can copy or cancel its parent's rotation.
    """

    def initialize(self):
        super().initialize()
        
        self.rotation_bones = []

    ####################################################
    # Utilities

    def get_parent_parent_mch(self, default_bone):
        """ Return the parent's master control bone if connecting and found. """

        if not self.incoming == 'NONE' and self.rigify_parent and hasattr(self.rigify_parent.bones.ctrl, 'master'):
            return self.rigify_parent.bones.ctrl.master
        else:
            return default_bone

    def get_parent_master_panel(self, default_bone):
        """ Return the parent's master control bone if connecting and found, and script panel. """

        controls = self.bones.ctrl.flatten()
        prop_bone = self.get_parent_parent_mch(default_bone)

        if prop_bone != default_bone:
            owner = self.rigify_parent
            controls += self.rigify_parent.bones.ctrl.flatten()
        else:
            owner = self

        return prop_bone, self.script.panel_with_selected_check(owner, controls)

    ####################################################
    # Rotation follow

    @stage.generate_bones
    def make_mch_control_bones(self):
        self.bones.mch.rot = self.make_mch_follow_bone(self.bones.org[0], self.bones.org[0], 1.0)
        self.root_bone = self.bones.mch.rot

    def make_mch_follow_bone(self, org, name, defval, *, copy_scale=False):
        bone = self.copy_bone(org, make_derived_name('ROT-'+name, 'mch'), parent=True)
        self.rotation_bones.append((org, name, bone, defval, copy_scale))
        return bone

    ####################################################
    # MCH bones associated with main controls

    @stage.parent_bones
    def parent_mch_control_bones(self):
        self.set_bone_parent(self.bones.mch.rot, self.rig_parent_bone)

    @stage.parent_bones
    def align_mch_follow_bones(self):
        #self.follow_bone = self.get_parent_parent_mch('root')
        self.follow_bone = 'root'

        for org, name, bone, defval, copy_scale in self.rotation_bones:
            align_bone_orientation(self.obj, bone, self.follow_bone)

    @stage.configure_bones
    def configure_mch_follow_bones(self):
        self.prop_bone, panel = self.get_parent_master_panel(self.default_prop_bone)

        for org, name, bone, defval, copy_scale in self.rotation_bones:
            textname = name.replace('_',' ').title() + ' Follow'

            self.make_property(self.prop_bone, name+'_follow', default=defval)
            panel.custom_prop(self.prop_bone, name+'_follow', text=textname, slider=True)

    @stage.rig_bones
    def rig_mch_follow_bones(self):
        for org, name, bone, defval, copy_scale in self.rotation_bones:
            self.rig_mch_rotation_bone(bone, name+'_follow', copy_scale)

    def rig_mch_rotation_bone(self, mch, prop_name, copy_scale):
        con = self.make_constraint(mch, 'COPY_ROTATION', self.follow_bone)

        self.make_driver(con, 'influence', variables=[(self.prop_bone, prop_name)], polynomial=[1,-1])

        if copy_scale:
            self.make_constraint(mch, 'COPY_SCALE', self.follow_bone)