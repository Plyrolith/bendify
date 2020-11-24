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
from rigify.utils.bones import align_bone_orientation, put_bone, flip_bone, is_same_position, is_connected_position, set_bone_widget_transform
from rigify.utils.widgets_basic import create_circle_widget
from rigify.rigs.widgets import create_gear_widget

from rigify.rigs.chain_rigs import TweakChainRig

from ...utils.bones import distance
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
        self.bbone_chain_length = 0

        #self.stretch_orgs_default = 1.0
        self.keep_axis = 'SWING_Y'

    ##############################
    # Utilities

    def align_bone(self, i, bone, prev_target, curr_target, next_target):
        # Realign bone between to targets
        if prev_target and next_target:
            b = self.get_bone(bone)
            length = b.length
            b.tail = b.head + self.get_bone(next_target).head - self.get_bone(prev_target).head
            b.length = length

    ##############################
    # Control chain

    @stage.parent_bones
    def parent_control_chain(self):
        # Disconnect controls
        self.parent_bone_chain(self.bones.ctrl.fk, use_connect=False, inherit_scale='ALIGNED')

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
            self.align_bone(*args)
    
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
        self.make_constraint(mch, 'COPY_SCALE', self.copy_scale_bone, use_make_uniform=True)

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
            self.align_bone(*args)   

    @stage.configure_bones
    def configure_tweak_chain(self):
        super().configure_tweak_chain()

        ControlLayersOption.TWEAK.assign(self.params, self.obj, self.bones.ctrl.tweak)

    def configure_tweak_bone(self, i, tweak):
        # Fully unlocked tweaks
        tweak_pb = self.get_bone(tweak)
        tweak_pb.rotation_mode = self.rotation_mode_tweak

    ##############################
    # ORG chain

    @stage.parent_bones
    def parent_org_chain(self):  
        orgs = self.bones.org
        ctrl = self.bones.ctrl
        for org, tweak in zip(orgs, ctrl.tweak):
            self.set_bone_parent(org, tweak, inherit_scale='NONE')

    @stage.rig_bones
    def rig_org_chain(self):
        for args in zip(count(0), self.bones.org):
            self.rig_org_bone(*args, self.rig_parent_bone)

    def rig_org_bone(self, i, org, target):
        self.make_constraint(org, 'COPY_SCALE', target)
        #con = self.make_constraint(org, 'COPY_TRANSFORMS', deform)
        #self.make_driver(con, 'influence', variables=[(self.bones.ctrl.master, 'stretch_orgs')])
        pass

    ####################################################
    # Deform bones

    @stage.generate_bones
    def make_deform_chain(self):
        super().make_deform_chain()
        self.bbone_chain_length = len(self.bones.deform) - 1

    @stage.parent_bones
    def ease_deform_chain(self):
        # New function to set bbone easing in edit mode
        tweaks = self.bones.ctrl.tweak

        for args in zip(count(0), self.bones.deform, tweaks, tweaks[1:]):
            self.ease_deform_bone(*args)
        
    def ease_deform_bone(self, i, deform, tweak, next_tweak):
        # Easing per bone
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
        ctrl = self.bones.ctrl
        for args in zip(count(0), self.bones.deform, ctrl.tweak, ctrl.tweak[1:], ctrl.fk):
            self.rig_deform_bone(*args)
    
    def rig_deform_bone(self, i, deform, tweak, next_tweak, fk):
        self.make_constraint(deform, 'COPY_LOCATION', tweak)
        self.make_constraint(deform, 'COPY_SCALE', fk)
        self.make_constraint(deform, 'COPY_SCALE', self.copy_scale_bone, use_offset=True, target_space='LOCAL', owner_space='LOCAL')
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
        # New function to set rig viewport display
        self.obj.data.display_type = 'BBONE'
    
    @classmethod
    def add_parameters(self, params):
        # Added rotation mode and bbone segments

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
            name        = 'Default Tweak Controller Rotation Mode',
            items       = rotation_modes,
            default     = 'ZXY',
            description = 'Default rotation mode for tweak control bones'
        )

        params.bbones_spine = bpy.props.IntProperty(
            name        = 'B-Bone Segments',
            default     = 8,
            min         = 1,
            max         = 32,
            description = 'Number of B-Bone segments'
        )

        params.bbones_easein = bpy.props.BoolProperty(
            name        = 'B-Bone Ease In',
            default     = True,
            description = 'B-Bone Easing in for First Bone of Chain'
        )

        params.bbones_easeout = bpy.props.BoolProperty(
            name        = 'B-Bone Ease Out',
            default     = True,
            description = 'B-Bone Easing out for Last Bone of Chain'
        )

    @classmethod
    def parameters_ui(self, layout, params):
        # Added rotation modes and bbone segments
        layout.row().prop(params, "rotation_mode_tweak", text="Tweaks")

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
        self.incoming_align = self.params.incoming_align
        self.incoming_parent = None
        self.incoming_tweak = None
        self.incoming_tweak_mch = None

    def prepare_bones(self):
        # Exactly match bone position to parent
        first_bone = self.get_bone(self.bones.org[0])
        if self.use_incoming_tweak and first_bone.parent:
            self.incoming_parent = first_bone.parent.name
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
        # Check for nearest Tweak of parent and move first org head there
        first_bone = self.bones.org[0]
        if self.use_incoming_tweak and self.get_bone_parent(first_bone):
            parent = self.rigify_parent
            if hasattr(parent.bones, 'ctrl') and hasattr(parent.bones.ctrl, 'tweak'):
                parent_tweaks = parent.bones.ctrl.tweak
                delta = distance(self.obj, first_bone, parent_tweaks[0])
                self.incoming_tweak = parent_tweaks[0]
                for tweak in parent_tweaks:
                    dist = distance(self.obj, first_bone, tweak)
                    if dist < delta:
                        delta = dist
                        self.incoming_tweak = tweak
            
                # Get incoming tweak mch, if existing
                if hasattr(parent.bones, 'mch') and hasattr(parent.bones.mch, 'tweak'):
                    if self.get_bone_parent(self.incoming_tweak) in parent.bones.mch.tweak:
                        self.incoming_tweak_mch = self.get_bone_parent(self.incoming_tweak)
                
                # Align
                if self.incoming_tweak and self.incoming_tweak_mch and self.incoming_align and len(parent_tweaks) > 1:
                    tweak = self.bones.ctrl.tweak
                    if self.incoming_tweak == parent_tweaks[0]:
                        self.align_bone(0, self.incoming_tweak, tweak[1], None, parent_tweaks[1])
                        self.align_bone(0, tweak[0], parent_tweaks[1], None, tweak[1])
                    elif self.incoming_tweak == parent_tweaks[-1]:
                        self.align_bone(0, self.incoming_tweak, parent_tweaks[-2], None, tweak[1])
                        self.align_bone(0, tweak[0], parent_tweaks[-2], None, tweak[1])
    
    @stage.generate_widgets
    def make_tweak_widgets(self):
        # Added counter
        for i, tweak in zip(count(0), self.bones.ctrl.tweak):
            self.make_tweak_widget(i, tweak)

    def make_tweak_widget(self, i, tweak):
        if i == 0 and self.incoming_tweak:
            create_sub_tweak_widget(self.obj, tweak, size=0.25)
        else:
            super().make_tweak_widget(tweak)


    ####################################################
    # Tweak MCH chain

    @stage.apply_bones
    def parent_tweak_mch_connected(self):
        # Re-parent first tweak mch to incoming tweak
        mch = self.bones.mch.tweak[0]
        if self.incoming_tweak:
            self.set_bone_parent(mch, self.incoming_tweak)
            self.get_bone(mch).inherit_scale = 'NONE'
            self.get_bone(self.incoming_tweak).length = self.get_bone(mch).length
        
        # If not tweak, parent to actual parent
        elif self.incoming_parent:
            self.set_bone_parent(mch, self.incoming_parent)
            self.get_bone(mch).inherit_scale = 'NONE'


    ####################################################
    # Deform bones

    def rig_deform_bone(self, i, deform, tweak, next_tweak, fk):
        if i == 0 and self.incoming_tweak:
            self.make_constraint(deform, 'COPY_LOCATION', tweak)
            self.make_constraint(deform, 'COPY_SCALE', fk)
            self.make_constraint(deform, 'COPY_SCALE', self.copy_scale_bone, use_offset=True, target_space='LOCAL', owner_space='LOCAL')
            self.make_constraint(deform, 'DAMPED_TRACK', next_tweak)
            stretch = self.make_constraint(deform, 'STRETCH_TO', next_tweak)
            total = self.bones.deform
            self.drivers_deform_bone(i, deform, stretch, self.incoming_tweak, next_tweak)
        else:
            super().rig_deform_bone(i, deform, tweak, next_tweak, fk)

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

        params.incoming_align = bpy.props.BoolProperty(
            name='Align Parent Tweak',
            default=False,
            description='Align nearest parent tweak to make the bridging B-Bone curve smoother (only activate for one connection at a time!)'
        )

    @classmethod
    def parameters_ui(self, layout, params):
        r = layout.row()
        r.prop(params, "incoming_tweak", toggle=True)
        r = layout.row()
        r.prop(params, "incoming_align")
        if not params.incoming_tweak:
            r.enabled = False

        super().parameters_ui(layout, params)


class RotMechBendyRig(ConnectingBendyRig):
    """
    Connecting Bendy rig that can copy or cancel its parent's rotation.
    """

    def initialize(self):
        super().initialize()

        self.rotation_bones = []

    # Widgets
    def make_control_widget(self, i, ctrl):
        create_circle_widget(self.obj, ctrl, radius=0.5, head_tail=0.75)

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
        #self.follow_bone = self.get_parent_master('root')
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