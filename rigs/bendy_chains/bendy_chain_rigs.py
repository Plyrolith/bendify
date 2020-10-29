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
from rigify.utils.bones import put_bone, flip_bone, is_same_position, is_connected_position, set_bone_widget_transform
from rigify.rigs.widgets import create_gear_widget

from rigify.rigs.chain_rigs import TweakChainRig

from ...utils.bones import distance
from ...utils.misc import threewise_nozip

class BaseBendyRig(TweakChainRig):
    """
    Base bendy rig
    """

    min_chain_length = 1

    def initialize(self):
        # Bbone segments
        super().initialize()
        self.bbone_segments = self.params.bbones_spine
        self.bbone_easein = self.params.bbones_easein
        self.bbone_easeout = self.params.bbones_easeout

        self.keep_axis = 'SWING_Y'
    
    ##############################
    # Control chain

    @stage.parent_bones
    def parent_control_chain(self):
        # Disconnect controls
        self.parent_bone_chain(self.bones.ctrl.fk, use_connect=False)

    ####################################################
    # Master control

    @stage.generate_bones
    def make_master_control(self):
        org = self.bones.org[0]
        self.bones.ctrl.master = self.copy_bone(org, make_derived_name(org, 'ctrl', '_master'))
        self.default_prop_bone = self.bones.ctrl.master
        self.copy_scale_bone = self.bones.ctrl.master

    @stage.parent_bones
    def parent_master_control(self):
        self.set_bone_parent(self.bones.ctrl.master, self.rig_parent_bone)

    @stage.configure_bones
    def configure_master_control(self):
        ctrl = self.bones.ctrl
        master = self.bones.ctrl.master
        bone = self.get_bone(master)
        bone.lock_location = (True, True, True)
        bone.lock_rotation = (True, True, True)
        bone.lock_rotation_w = True
        bone.lock_scale = (False, True, False)

    @stage.configure_bones
    def configure_master_properties(self):
        ctrl = self.bones.ctrl
        master = self.bones.ctrl.master
        panel = self.script.panel_with_selected_check(self, ctrl.flatten())
        self.make_property(master, 'volume_variation', default=1.0, max=100.0, soft_max=1.0, description='Volume variation for DEF bones')
        panel.custom_prop(master, 'volume_variation', text='Volume Variation', slider=True)
        self.make_property(master, 'stretch_orgs', default=0.0, description='Stretch ORGs to Tweaks instead of following FK')
        panel.custom_prop(master, 'stretch_orgs', text='ORGs follow Tweaks', slider=True)

    @stage.generate_widgets
    def make_master_control_widget(self):
        bone = self.bones.ctrl.master
        orgs = self.bones.org
        create_gear_widget(self.obj, bone, size=4)
        set_bone_widget_transform(self.obj, bone, orgs[0])

    ####################################################
    # Tweak Targets

    def check_mch_parents(self):
        ctrl = self.bones.ctrl
        return ctrl.fk + ctrl.fk[-1:]

    def check_mch_targets(self):
        ctrl = self.bones.ctrl
        mch = self.bones.mch
        return threewise_nozip([*ctrl.fk, mch.tweak[-1]])
    
    ####################################################
    # Tweak MCH chain

    @stage.generate_bones
    def make_tweak_mch_chain(self):
        # Create (new) mch bones for tweaks
        orgs = self.bones.org
        self.bones.mch.tweak = map_list(self.make_tweak_mch_bone, count(0), orgs + orgs[-1:])

    def make_tweak_mch_bone(self, i, org):
        # Tweak mch creation loop
        name = make_derived_name(org, 'mch', '_tweak')
        name = self.copy_bone(org, name, parent=False, scale=0.5)

        if i == len(self.bones.org):
            put_bone(self.obj, name, self.get_bone(org).tail)
        
        return name

    @stage.parent_bones
    def parent_tweak_mch_chain(self):
        # Parent tweak mch to ctrl chain and realign
        mch = self.bones.mch
        parents = self.check_mch_parents()

        for args in zip(count(0), mch.tweak, parents):
            self.parent_tweak_mch_bone(*args)

    def parent_tweak_mch_bone(self, i, mch, parent):
        # Parent tweak mch
        self.set_bone_parent(mch, parent)

    @stage.parent_bones
    def align_tweak_mch_chain(self):
        mch = self.bones.mch
        targets = self.check_mch_targets()
        
        for args in zip(count(0), mch.tweak, *targets):
            self.align_tweak_mch_bone(*args)

    def align_tweak_mch_bone(self, i, mch, prev_target, curr_target, next_target):
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
        parents = self.check_mch_parents()
        targets = self.check_mch_targets()

        for args in zip(count(0), mch.tweak, parents, *targets):
            self.rig_tweak_mch_bone(*args)

    def rig_tweak_mch_bone(self, i, mch, parent, prev_target, curr_target, next_target):
        # Constraints to calculate tangent rotation between previous and next chain targets
        if prev_target and next_target:
            self.make_constraint(mch, 'COPY_LOCATION', prev_target)
            self.make_constraint(mch, 'STRETCH_TO', next_target, bulge=0, volume='NO_VOLUME', keep_axis=self.keep_axis)
            self.make_constraint(mch, 'COPY_LOCATION', curr_target)
        self.make_constraint(mch, 'COPY_SCALE', parent)  

    ####################################################
    # Tweak chain

    @stage.parent_bones
    def parent_tweak_chain(self):
        ctrl = self.bones.ctrl
        mch = self.bones.mch
        for args in zip(count(0), ctrl.tweak, mch.tweak):
            self.parent_tweak_bone(*args)

    def parent_tweak_bone(self, i, tweak, parent):
        # Parent tweak
        self.set_bone_parent(tweak, parent)

    @stage.parent_bones
    def align_tweak_chain(self):
        ctrl = self.bones.ctrl
        targets = self.check_mch_targets()
        
        for args in zip(count(0), ctrl.tweak, *targets):
            self.align_tweak_bone(*args)   

    def align_tweak_bone(self, i, tweak, prev_target, curr_target, next_target):
        # Realign tweak
        if prev_target and next_target:
            tweak_bone = self.get_bone(tweak)
            length = tweak_bone.length
            tweak_bone.tail = tweak_bone.head + self.get_bone(next_target).head - self.get_bone(prev_target).head
            tweak_bone.length = length

    @stage.configure_bones
    def configure_tweak_chain(self):
        super().configure_tweak_chain()

        ControlLayersOption.TWEAK.assign(self.params, self.obj, self.bones.ctrl.tweak)

    def configure_tweak_bone(self, i, tweak):
        # Fully unlocked tweaks
        tweak_pb = self.get_bone(tweak)
        tweak_pb.rotation_mode = 'ZXY'

    ##############################
    # ORG chain

    @stage.parent_bones
    def parent_org_chain(self):
        ctrl = self.bones.ctrl
        org = self.bones.org
        for fk, org in zip(ctrl.fk, org):
            self.set_bone_parent(org, fk)

    @stage.rig_bones
    def rig_org_chain(self):
        for args in zip(count(0), self.bones.org, self.bones.deform):
            self.rig_org_bone(*args)

    def rig_org_bone(self, i, org, deform):
        con = self.make_constraint(org, 'COPY_TRANSFORMS', deform)
        self.make_driver(con, 'influence', variables=[(self.bones.ctrl.master, 'stretch_orgs')])

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
        pbone.bbone_custom_handle_start = self.get_bone(tweak)
        pbone.bbone_custom_handle_end = self.get_bone(next_tweak)

    @stage.rig_bones
    def rig_deform_chain(self):
        tweaks = self.bones.ctrl.tweak
        for args in zip(count(0), self.bones.deform, tweaks, tweaks[1:]):
            self.rig_deform_bone(*args)
    
    def rig_deform_bone(self, i, deform, tweak, next_tweak):
        self.make_constraint(deform, 'COPY_LOCATION', tweak)
        self.make_constraint(deform, 'COPY_SCALE', self.copy_scale_bone)
        self.make_constraint(deform, 'DAMPED_TRACK', next_tweak)
        stretch = self.make_constraint(deform, 'STRETCH_TO', next_tweak)
        self.drivers_deform_bone(i, deform, stretch, tweak, next_tweak)

    def drivers_deform_bone(self, i, deform, stretch, tweak, next_tweak):
        # New function to create bendy bone drivers
        pbone = self.get_bone(deform)
        space = 'LOCAL_SPACE'
        v_type = 'TRANSFORMS'

        ####################################################
        # Volume Variation

        self.make_driver(stretch, 'bulge', variables=[(self.bones.ctrl.master, 'volume_variation')])

        ####################################################
        # Easing

        self.make_driver(
            pbone.bone,
            'bbone_easein',
            expression='scale_y - 1' if i == 0 and not self.bbone_easein else None,
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
            expression='scale_y - 1' if i == len(self.bones.deform) - 1 and not self.bbone_easeout else None,
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

        params.bbones_spine = bpy.props.IntProperty(
            name        = 'B-Bone Segments',
            default     = 8,
            min         = 1,
            description = 'Number of B-Bone segments'
        )

        params.bbones_easein = bpy.props.BoolProperty(
            name        = 'B-Bone Ease In',
            default     = True,
            description = 'B-Bone Easing in for First Bone of Chain'
        )

        params.bbones_easeout = bpy.props.BoolProperty(
            name        = 'B-Bone Ease Out',
            default     = False,
            description = 'B-Bone Easing out for Last Bone of Chain'
        )

    @classmethod
    def parameters_ui(self, layout, params):
        # Added bbone segments
        r = layout.row()
        r.prop(params, "bbones_spine")

        r = layout.row(align=True)
        r.prop(params, "bbones_easein", text="Ease In", toggle=True)
        r.prop(params, "bbones_easeout", text="Ease Out", toggle=True)

        ControlLayersOption.TWEAK.parameters_ui(layout, params)


class ConnectingBendyRig(BaseBendyRig):
    """
    Bendy rig that can attach to a tweak of its parent.
    """

    def initialize(self):
        super().initialize()

        self.use_incoming_tweak = self.params.incoming_tweak
        self.incoming_tweak = None

    def prepare_bones(self):
        # Exactly match bone position to parent
        first_bone = self.get_bone(self.bones.org[0])
        if self.use_incoming_tweak and first_bone.parent:
            d_head = (first_bone.head - first_bone.parent.head).length
            d_tail = (first_bone.head - first_bone.parent.tail).length
            if d_head < d_tail:
                first_bone.head = first_bone.parent.head
            else:
                first_bone.head = first_bone.parent.tail

    ####################################################
    # Master control

    @stage.generate_widgets
    def make_master_control_widget(self):
        bone = self.bones.ctrl.master
        orgs = self.bones.org
        create_gear_widget(self.obj, bone, size=4)
        set_bone_widget_transform(self.obj, bone, orgs[1 if self.incoming_tweak else 0])

    ####################################################
    # Tweak chain

    @stage.parent_bones
    def check_incoming_tweak(self):
        if self.use_incoming_tweak:
            first_bone = self.bones.org[0]
            parent_tweaks = self.rigify_parent.bones.ctrl.tweak
            delta = distance(self.obj, first_bone, parent_tweaks[0])
            self.incoming_tweak = parent_tweaks[0]
            for tweak in parent_tweaks:
                dist = distance(self.obj, first_bone, tweak)
                if dist < delta:
                    delta = dist
                    self.incoming_tweak = tweak
            # Dirty
            tweak = self.bones.mch.tweak[0]
            self.set_bone_parent(tweak, self.incoming_tweak)
            self.get_bone(tweak).inherit_scale = 'NONE'

            conn = self.get_bone(self.incoming_tweak)
            self.get_bone(self.bones.ctrl.tweak[0]).length = conn.length / 2

    ####################################################
    # Tweak MCH chain

    def parent_tweak_mch_bone(self, i, mch, parent):
        if i == 0 and self.incoming_tweak:
            self.set_bone_parent(mch, self.incoming_tweak)
            
        else:
            super().parent_tweak_mch_bone(i, mch, parent)

    ####################################################
    # Deform bones

    def rig_deform_bone(self, i, deform, tweak, next_tweak):
        if i == 0 and self.incoming_tweak:
            tweak = self.incoming_tweak
        super().rig_deform_bone(i, deform, tweak, next_tweak)


    ##############################
    # Settings

    @classmethod
    def add_parameters(self, params):
        super().add_parameters(params)

        params.incoming_tweak = bpy.props.BoolProperty(
            name='Connect Tweaks',
            default=False,
            description='Connect the B-Bone chain to the nearest parent tweak'
        )

    @classmethod
    def parameters_ui(self, layout, params):
        r = layout.row()
        r.prop(params, "incoming_tweak")

        super().parameters_ui(layout, params)


class BaseBendyHeadTailRig(ConnectingBendyRig):
    """ Bendy base for head and tail rigs. """

    def initialize(self):
        super().initialize()

        self.rotation_bones = []

    ####################################################
    # Utilities

    def get_parent_master(self, default_bone):
        """ Return the parent's master control bone if connecting and found. """

        if self.use_incoming_tweak and 'master' in self.rigify_parent.bones.ctrl:
            return self.rigify_parent.bones.ctrl.master
        else:
            return default_bone

    def get_parent_master_panel(self, default_bone):
        """ Return the parent's master control bone if connecting and found, and script panel. """

        controls = self.bones.ctrl.flatten()
        prop_bone = self.get_parent_master(default_bone)

        if prop_bone != default_bone:
            owner = self.rigify_parent
            controls += self.rigify_parent.bones.ctrl.flatten()
        else:
            owner = self

        return prop_bone, self.script.panel_with_selected_check(owner, controls)

    ####################################################
    # Rotation follow

    def make_mch_follow_bone(self, org, name, defval, *, copy_scale=False):
        bone = self.copy_bone(org, make_derived_name('ROT-'+name, 'mch'), parent=True)
        self.rotation_bones.append((org, name, bone, defval, copy_scale))
        return bone

    @stage.parent_bones
    def align_mch_follow_bones(self):
        self.follow_bone = self.get_parent_master('root')

        for org, name, bone, defval, copy_scale in self.rotation_bones:
            align_bone_orientation(self.obj, bone, self.follow_bone)

    @stage.configure_bones
    def configure_mch_follow_bones(self):
        self.prop_bone, panel = self.get_parent_master_panel(self.default_prop_bone)

        for org, name, bone, defval, copy_scale in self.rotation_bones:
            textname = name.replace('_',' ').title() + ' Follow'

            self.make_property(self.prop_bone, name+'_follow', default=float(defval))
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

