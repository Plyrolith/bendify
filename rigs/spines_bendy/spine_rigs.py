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
from rigify.utils.bones import put_bone, flip_bone, is_same_position, is_connected_position
from rigify.rigs.widgets import create_gear_widget

from rigify.rigs.chain_rigs import TweakChainRig

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
        self.volume_variation = self.params.volume_variation
    
    ##############################
    # Control chain

    @stage.parent_bones
    # Disconnect controls
    def parent_control_chain(self):
        self.parent_bone_chain(self.bones.ctrl.fk, use_connect=False)

    ####################################################
    # Master control

    @stage.generate_bones
    def make_master_control(self):
        org = self.bones.org[0]
        self.bones.ctrl.master = self.copy_bone(org, make_derived_name(org, 'ctrl', '_master'))
        self.default_prop_bone = self.bones.ctrl.master

    @stage.parent_bones
    def parent_master_control(self):
        self.set_bone_parent(self.bones.ctrl.master, self.rig_parent_bone)

    @stage.configure_bones
    def configure_master_control(self):
        bone = self.get_bone(self.bones.ctrl.master)
        bone.lock_location = (True, True, True)
        bone.lock_rotation = (False, False, False)
        bone.lock_rotation_w = False
        bone.lock_scale = (False, True, False)

    @stage.generate_widgets
    def make_master_control_widget(self):
        bone = self.bones.ctrl.master
        create_gear_widget(self.obj, bone, size=0.7)

    ####################################################
    # Tweak MCH chain

    @stage.generate_bones
    def make_tweak_mch_chain(self):
        # Create (new) mch bones for tweaks
        orgs = self.bones.org
        self.bones.mch.tweak = map_list(self.make_tweak_mch_bone, count(0), orgs + orgs[-1:])

    def make_tweak_mch_bone(self, i, org):
        # Tweak mch creation loop
        name = self.copy_bone(org, make_derived_name(org, 'mch', '_tweak'), parent=False, scale=0.5)

        if i == len(self.bones.org):
            put_bone(self.obj, name, self.get_bone(org).tail)
        
        return name

    @stage.parent_bones
    def parent_tweak_mch_chain(self):
        # Parent tweak mch to ctrl chain and realign
        mch = self.bones.mch
        ctrl = self.bones.ctrl
        targets = threewise_nozip([*ctrl.fk, mch.tweak[-1]])

        for args in zip(count(0), mch.tweak, ctrl.fk + ctrl.fk[-1:]):
            self.parent_tweak_mch_bone(*args)
        
        for args in zip(mch.tweak, *targets):
            self.align_tweak_mch_bone(*args)
        
    def parent_tweak_mch_bone(self, i, mch, parent):
        # Parent tweak mch
        self.set_bone_parent(mch, parent)

    def align_tweak_mch_bone(self, mch, prev_target, curr_target, next_target):
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
        ctrl = self.bones.ctrl
        targets = threewise_nozip([*ctrl.fk, mch.tweak[-1]])

        for args in zip(count(0), mch.tweak, ctrl.fk, *targets):
            self.rig_tweak_mch_bone(*args)

    def rig_tweak_mch_bone(self, i, mch, fk, prev_target, curr_target, next_target):
        # Constraints to calculate tangent rotation between previous and next chain targets
        if prev_target and next_target:
            self.make_constraint(mch, 'COPY_LOCATION', prev_target)
            self.make_constraint(mch, 'STRETCH_TO', next_target, bulge=0, volume='NO_VOLUME', keep_axis='PLANE_Z')
            self.make_constraint(mch, 'COPY_LOCATION', curr_target)
        self.make_constraint(mch, 'COPY_SCALE', fk)  

    ####################################################
    # Tweak chain

    @stage.parent_bones
    def parent_tweak_chain(self):
        ctrl = self.bones.ctrl
        mch = self.bones.mch
        targets = threewise_nozip([*ctrl.fk, mch.tweak[-1]])
        for args in zip(count(0), ctrl.tweak, mch.tweak):
            self.parent_tweak_bone(*args)
        
        for args in zip(ctrl.tweak, *targets):
            self.align_tweak_bone(*args)

    def parent_tweak_bone(self, i, tweak, parent):
        # Parent tweak
        self.set_bone_parent(tweak, parent)

    def align_tweak_bone(self, tweak, prev_target, curr_target, next_target):
        # Realign tweak
        if prev_target and next_target:
            tweak_bone = self.get_bone(tweak)
            length = tweak_bone.length
            tweak_bone.tail = tweak_bone.head + self.get_bone(next_target).head - self.get_bone(prev_target).head
            tweak_bone.length = length

    def configure_tweak_bone(self, i, tweak):
        # Fully unlocked tweaks
        tweak_pb = self.get_bone(tweak)
        tweak_pb.rotation_mode = 'ZXY'

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
        # Added copy scale
        self.make_constraint(deform, 'COPY_TRANSFORMS', tweak)
        self.make_constraint(deform, 'COPY_SCALE', self.bones.ctrl.master)
        if next_tweak:
            self.make_constraint(deform, 'DAMPED_TRACK', next_tweak)
            self.make_constraint(deform, 'STRETCH_TO', next_tweak, bulge=self.volume_variation)
        self.rig_drivers_bendy(i, deform, tweak, next_tweak)

    def rig_drivers_bendy(self, i, deform, tweak, next_tweak):
        # New function to create bendy bone drivers
        pbone = self.get_bone(deform)
        space = 'LOCAL_SPACE'
        v_type = 'TRANSFORMS'

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

        params.volume_variation = bpy.props.FloatProperty(
            name        = 'Volume Variation',
            default     = 1.0,
            min         = 0.0,
            max         = 100.0,
            description = 'Volume Variation Factor for Stretch Deform'
        )

    @classmethod
    def parameters_ui(self, layout, params):
        # Added bbone segments
        r = layout.row()
        r.prop(params, "bbones_spine")

        r = layout.row(align=True)
        r.prop(params, "bbones_easein", text="Ease In", toggle=True)
        r.prop(params, "bbones_easeout", text="Ease Out", toggle=True)

        r = layout.row()
        r.prop(params, "volume_variation")

        ControlLayersOption.TWEAK.parameters_ui(layout, params)


class ConnectingBendyRig(BaseBendyRig):
    """
    Bendy rig that can attach to an end of the parent, extending bbone chains.
    """

    def initialize(self):
        super().initialize()

        self.use_connect_chain = self.params.connect_chain
        self.connected_org = None
        self.connected_tail = False
        self.connected_control = None
        self.connected_tweak = None

        if self.use_connect_chain:
            first_org = self.bones.org[0]
            parent = self.rigify_parent

            parent_orgs = parent.bones.org

            for org in parent_orgs:
                if 

            if not (ok_reverse if self.use_connect_reverse else ok_direct):
                self.raise_error("Cannot connect chain - bone position is disjoint.")


    def prepare_bones(self):
        # Exactly match bone position to parent
        if self.use_connect_chain:
            first_bone = self.get_bone(self.bones.org[0])
            parent_orgs = self.rigify_parent.bones.org

            if self.use_connect_reverse:
                first_bone.head = self.get_bone(parent_orgs[0]).head
            else:
                first_bone.head = self.get_bone(parent_orgs[-1]).tail

    def parent_bones(self):
        # Use the parent of the shared tweak as the rig parent
        root = self.connected_tweak or self.bones.org[0]

        self.rig_parent_bone = self.get_bone_parent(root)

    ##############################
    # Control chain

    @stage.parent_bones
    def parent_control_chain(self):
        super().parent_control_chain()

        self.set_bone_parent(self.bones.ctrl.fk[0], self.rig_parent_bone)

    ##############################
    # Tweak chain

    def check_connect_tweak(self, org):
        """ Check if it is possible to share the last parent tweak control. """

        assert self.connected_tweak is None

        if self.use_connect_chain and isinstance(self.rigify_parent, TweakChainRig):
            # Share the last tweak bone of the parent rig
            parent_tweaks = self.rigify_parent.bones.ctrl.tweak
            index = 0 if self.use_connect_reverse else -1
            name = parent_tweaks[index]

            if not is_same_position(self.obj, name, org):
                self.raise_error("Cannot connect tweaks - position mismatch.")

            if not self.use_connect_reverse:
                copy_bone_position(self.obj, org, name, scale=0.5)

                name = self.rename_bone(name, 'tweak_' + strip_org(org))

            self.connected_tweak = parent_tweaks[index] = name

            return name
        else:
            return None

    def make_tweak_bone(self, i, org):
        if i == 0 and self.check_connect_tweak(org):
            return self.connected_tweak
        else:
            return super().make_tweak_bone(i, org)

    @stage.parent_bones
    def parent_tweak_chain(self):
        ctrl = self.bones.ctrl
        for i, tweak, main in zip(count(0), ctrl.tweak, ctrl.fk + ctrl.fk[-1:]):
            if i > 0 or not (self.connected_tweak and self.use_connect_reverse):
                self.set_bone_parent(tweak, main)

    def configure_tweak_bone(self, i, tweak):
        super().configure_tweak_bone(i, tweak)

        if self.use_connect_chain and self.use_connect_reverse and i == len(self.bones.org):
            tweak_pb = self.get_bone(tweak)
            tweak_pb.lock_rotation_w = False
            tweak_pb.lock_rotation = (True, False, True)
            tweak_pb.lock_scale = (False, True, False)

    ##############################
    # ORG chain

    @stage.parent_bones
    def parent_org_chain(self):
        if self.use_connect_chain and self.use_connect_reverse:
            flip_bone_chain(self.obj, self.bones.org)

            for org, tweak in zip(self.bones.org, self.bones.ctrl.tweak[1:]):
                self.set_bone_parent(org, tweak)

        else:
            self.set_bone_parent(self.bones.org[0], self.rig_parent_bone)

    def rig_org_bone(self, i, org, tweak, next_tweak):
        if self.use_connect_chain and self.use_connect_reverse:
            self.make_constraint(org, 'DAMPED_TRACK', tweak)
            self.make_constraint(org, 'STRETCH_TO', tweak)
        else:
            super().rig_org_bone(i, org, tweak, next_tweak)

    ##############################
    # Deform chain

    def make_deform_bone(self, i, org):
        name = super().make_deform_bone(i, org)

        if self.use_connect_chain and self.use_connect_reverse:
            self.set_bone_parent(name, None)
            flip_bone(self.obj, name)

        return name

    @stage.parent_bones
    def parent_deform_chain(self):
        if self.use_connect_chain:
            deform = self.bones.deform
            parent_deform = self.rigify_parent.bones.deform

            if self.use_connect_reverse:
                self.set_bone_parent(deform[-1], self.bones.org[-1])
                self.parent_bone_chain(reversed(deform), use_connect=True)

                connect_bbone_chain_handles(self.obj, [ deform[0], parent_deform[0] ])
                return

            else:
                self.set_bone_parent(deform[0], parent_deform[-1], use_connect=True)

        super().parent_deform_chain()

    ##############################
    # Settings

    @classmethod
    def add_parameters(self, params):
        super().add_parameters(params)

        params.connect_chain = bpy.props.BoolProperty(
            name='Connect chain',
            default=False,
            description='Connect the B-Bone chain to the parent rig'
        )


        '''
        params.connect_direction = bpy.props.EnumProperty(
            name='Connect direction',
            default='FRONT',
            description='Parent side where chain will be attached',
            items=[
                ('FRONT', 'Front', 'Front'),
                ('REAR', 'Rear', 'Rear')
            ]
        )
        '''

    @classmethod
    def parameters_ui(self, layout, params):
        r = layout.row()
        r.prop(params, "connect_chain")
        '''
        r = layout.row()
        r.prop(params, "connect_direction", expand=True)
        if not params.connect_chain:
            r.enabled = False
        '''

        super().parameters_ui(layout, params)