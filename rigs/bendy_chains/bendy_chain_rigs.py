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
from rigify.utils.bones import align_bone_orientation, align_bone_roll, align_bone_x_axis, align_bone_y_axis, copy_bone_position, put_bone, set_bone_widget_transform
from rigify.utils.widgets_basic import create_circle_widget
from rigify.rigs.widgets import create_ballsocket_widget, create_gear_widget

from rigify.rigs.chain_rigs import TweakChainRig

from ...utils.bones import align_bone, distance, real_bone
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
        self.make_property(master, 'volume_deform', default=1.0, max=100.0, soft_max=1.0, description='Volume variation for DEF bones')
        panel.custom_prop(master, 'volume_deform', text='Deform Volume Variation', slider=True)

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
        self.set_bone_parent(mch, parent, inherit_scale='FIX_SHEAR')

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
            #self.make_constraint(mch, 'DAMPED_TRACK', next_target)
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
        for org in self.bones.org:
            self.set_bone_parent(org, self.root_bone)

    @stage.rig_bones
    def rig_org_chain(self):
        '''Set ORG transformation according to rig setting'''
        ctrls = self.bones.ctrl
        for org, deform, tweak, next_tweak, fk in zip(self.bones.org, self.bones.deform, ctrls.tweak, ctrls.tweak[1:], ctrls.fk):
            self.rig_org_bone(org, deform, tweak, next_tweak, fk)
            
    def rig_org_bone(self, org, deform, tweak, next_tweak, fk):
        '''ORG bone constraint loop'''
        if self.org_transform == 'TWEAKS':
            self.make_constraint(org, 'COPY_TRANSFORMS', deform)
            self.make_constraint(org, 'COPY_SCALE', tweak, use_y=False, power=0.5, use_offset=True, target_space='LOCAL', owner_space='LOCAL')
            self.make_constraint(org, 'COPY_SCALE', next_tweak, use_y=False, power=0.5, use_offset=True, target_space='LOCAL', owner_space='LOCAL')
        elif self.org_transform == 'TWEAK':
            self.make_constraint(org, 'COPY_TRANSFORMS', deform)
            self.make_constraint(org, 'COPY_SCALE', tweak, use_y=False, use_offset=True, target_space='LOCAL', owner_space='LOCAL')
        elif self.org_transform == 'DEF':
            self.make_constraint(org, 'COPY_TRANSFORMS', deform)
        elif self.org_transform == 'FK':
            self.make_constraint(org, 'COPY_TRANSFORMS', fk)

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
        for deform in self.bones.deform:
            self.set_bone_parent(deform, self.root_bone)

    @stage.parent_bones
    def ease_deform_chain(self):
        '''Set bbone easing in edit mode'''
        tweaks = self.bones.ctrl.tweak

        for args in zip(count(0), self.bones.deform, tweaks, tweaks[1:]):
            self.ease_deform_bone(*args)
        
    def ease_deform_bone(self, i, bone, handle_start, handle_end):
        '''Easing per bone'''
        pbone = self.get_bone(bone)
        pbone.bbone_segments = self.bbone_segments
        pbone.bbone_handle_type_start = 'TANGENT'
        pbone.bbone_handle_type_end = 'TANGENT'
        pbone.bbone_custom_handle_start = self.get_bone(handle_start)
        pbone.bbone_custom_handle_end = self.get_bone(handle_end)
        pbone.bbone_easein = 0.0 if i == 0 and not self.bbone_easein else 1.0
        pbone.bbone_easeout = 0.0 if i == self.bbone_chain_length and not self.bbone_easeout else 1.0

    @stage.rig_bones
    def rig_deform_chain(self):
        '''DEF constraint chain'''
        ctrls = self.bones.ctrl
        for args in zip(count(0), self.bones.deform, ctrls.tweak, ctrls.tweak[1:], ctrls.fk):
            self.rig_deform_bone(*args)
    
    def rig_deform_bone(self, i, bone, handle_start, handle_end, scale=None):
        '''DEF constraints'''
        self.transform_deform_bone(bone, handle_start)
        if scale:
            self.scale_deform_bone(bone, scale)
        self.track_deform_bone(bone, handle_end)
        self.stretch_bone(bone, handle_end, 'volume_deform')

        self.bendy_drivers(bone, handle_start, handle_end)

    def transform_deform_bone(self, bone, target):
        self.make_constraint(bone, 'COPY_LOCATION', target)
        #self.make_constraint(bone, 'COPY_ROTATION', target)
    
    def scale_deform_bone(self, bone, target):
        self.make_constraint(bone, 'COPY_SCALE', target)

    def track_deform_bone(self, bone, target):
        self.make_constraint(bone, 'DAMPED_TRACK', target)

    def stretch_bone(self, bone, target, volume_property):
        stretch = self.make_constraint(bone, 'STRETCH_TO', target)
        self.make_driver(stretch, 'bulge', variables=[(self.default_prop_bone, volume_property)])

    def bendy_drivers(self, bone, handle_start, handle_end):
        '''New function to create bendy bone drivers'''
        pbone = self.get_bone(bone)
        space = 'LOCAL_SPACE'
        v_type = 'TRANSFORMS'

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
                            'bone_target': handle_start,
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
                            'bone_target': handle_end,
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
                            'bone_target': handle_start,
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
                            'bone_target': handle_end,
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
                            'bone_target': handle_start,
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
                            'bone_target': handle_end,
                            'transform_type': 'SCALE_Z',
                            'transform_space': space,
                        }
                    ]
                }
            }
        )

    ####################################################
    # UI

    def rotation_mode_tweak_ui(self, layout, params):
        layout.row().prop(params, 'rotation_mode_tweak', text="Tweaks")
    
    def org_transform_ui(self, layout, params):
        layout.row().prop(params, 'org_transform', text="ORGs")

    def bbones_ui(self, layout, params):
        box = layout.box()
        box.row().prop(params, 'bbones_spine')
        r = box.row(align=True)
        r.prop(params, 'bbones_easein', text="Ease In", toggle=True)
        r.prop(params, 'bbones_easeout', text="Ease Out", toggle=True)

    ####################################################
    # SETTINGS
    
    @stage.finalize
    def finalize_armature_display(self):
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
            description="Deform easing in for first bone of chain"
        )

        params.bbones_easeout = bpy.props.BoolProperty(
            name="B-Bone Ease Out",
            default=True,
            description="Deform easing out for last bone of chain"
        )

        params.org_transform = bpy.props.EnumProperty(
            name="ORG Transform base",
            items=[
                ('FK', "FK", "FK"),
                ('DEF', "Deforms", "Deforms"),
                ('TWEAK', "Single Tweak", "Single Tweak"),
                ('TWEAKS', "Between Tweaks", "BetweenTweaks"),
            ],
            default='DEF',
            description="Source of ORG transformation; useful to determine children's behaviour"
        )

    @classmethod
    def parameters_ui(self, layout, params):
        self.rotation_mode_tweak_ui(self, layout, params)
        self.org_transform_ui(self, layout, params)
        self.bbones_ui(self, layout, params)
        ControlLayersOption.TWEAK.parameters_ui(layout, params)


# Combine from the following

class ComplexStretchBendyRig(BaseBendyRig):
    """
    Bendy rig with copied stretch constraints for better non-uniform scalability
    """

    def initialize(self):
        super().initialize()

        self.complex_stretch = self.params.complex_stretch
    
    ####################################################
    # Deform MCH

    @stage.generate_bones
    def make_deform_mch_chain(self):
        if self.complex_stretch:
            self.bones.mch.deform = map_list(self.make_deform_mch_bone, count(0), self.bones.org)

    def make_deform_mch_bone(self, i, org):
        name = self.copy_bone(org, make_derived_name(org, 'mch', "_deform"), parent=True)
        return name

    @stage.parent_bones
    def parent_deform_mch_chain(self):
        if self.complex_stretch:
            self.parent_bone_chain(self.bones.mch.deform, use_connect=True)
            self.set_bone_parent(self.bones.mch.deform[0], self.root_bone)

    @stage.apply_bones
    def apply_deform_mch_chain(self):
        if self.complex_stretch:
            for deform, mch in zip(self.bones.deform, self.bones.mch.deform):
                copy_bone_position(self.obj, deform, mch)
                self.set_bone_parent(mch, self.get_bone_parent(deform))

    @stage.rig_bones
    def rig_deform_mch_chain(self):
        if self.complex_stretch:
            ctrls = self.bones.ctrl
            for args in zip(count(0), self.bones.mch.deform, ctrls.tweak, ctrls.tweak[1:], ctrls.fk):
                self.rig_deform_mch_bone(*args)

    def rig_deform_mch_bone(self, i, bone, handle_start, handle_end, scale=None):
        if self.complex_stretch:
            self.transform_deform_bone(bone, handle_start)
            if scale:
                self.scale_deform_bone(bone, scale)
            #self.track_deform_bone(bone, handle_end)
            self.stretch_bone(bone, handle_end, 'volume_deform')

    ####################################################
    # Deform bones

    def rig_deform_bone(self, i, bone, handle_start, handle_end, scale=None):
        if self.complex_stretch:
            self.transform_deform_bone(bone, handle_start)
            #if scale:
            #    self.scale_deform_bone(bone, scale)
            self.track_deform_bone(bone, handle_end)
            
            mch = self.bones.mch.deform[i]
            self.make_constraint(bone, 'COPY_SCALE', mch)

            self.bendy_drivers(bone, handle_start, handle_end)
        else:
            super().rig_deform_bone(i, bone, handle_start, handle_end, scale)

    ####################################################
    # UI

    def complex_stretch_ui(self, layout, params):
        layout.row().prop(params, "complex_stretch", toggle=True)

    ####################################################
    # SETTINGS

    @classmethod
    def add_parameters(self, params):
        super().add_parameters(params)

        params.complex_stretch = bpy.props.BoolProperty(
            name="Complex Stretch Mechanics",
            description="Additional mechanical layer to separate stretch matrix and enable better non-uniform scaling",
            default=False
            )

    @classmethod
    def parameters_ui(self, layout, params):
        self.complex_stretch_ui(self, layout, params)
        super().parameters_ui(layout, params)


class SegmentedBendyRig(BaseBendyRig):
    """
    Bendy chain with indivdually scaling fk segments
    """

    def initialize(self):
        super().initialize()

        self.segmented_fk = self.params.segmented_fk
        self.segmented_align = self.params.segmented_align

    ##############################
    # Utilities

    def copy_scale_bone(self):
        #if hasattr(self.bones.ctrl, 'master'):
        #    return self.bones.ctrl.master
        if hasattr(self.bones.mch, 'rot'):
            return self.bones.mch.rot
        elif hasattr(self.bones.mch, 'parent'):
            return self.bones.mch.parent
        else:
            return self.root_bone

    ####################################################
    # Control chain

    @stage.parent_bones
    def parent_control_chain(self):
        if self.segmented_fk:
            for fk, parent in zip(self.bones.ctrl.fk, self.bones.mch.fk):
                self.set_bone_parent(fk, parent)
        else:
            super().parent_control_chain()

    ####################################################
    # FK MCH chain

    @stage.generate_bones
    def make_fk_mch_chain(self):
        # Create (new) mch bones for controllers
        if self.segmented_fk:
            self.bones.mch.fk = map_list(self.make_fk_mch_bone, count(0), self.bones.org)

    def make_fk_mch_bone(self, i, org):
        # FK mch creation loop
        name = make_derived_name(org, 'mch')
        name = self.copy_bone(org, name, parent=False)
        
        return name

    @stage.parent_bones
    def parent_fk_mch_chain(self):
        if self.segmented_fk:
            for mch, parent in zip(self.bones.mch.fk, [self.root_bone] + self.bones.ctrl.fk):
                self.set_bone_parent(mch, parent, inherit_scale='ALIGNED' if self.segmented_align else 'FULL')

    @stage.rig_bones
    def rig_fk_mch_chain(self):
        if self.segmented_fk:
            ctrls = self.bones.ctrl
            mchs = self.bones.mch
            for mch, fk in zip(mchs.fk, [None] + ctrls.fk):
                if fk:
                    self.make_constraint(mch, 'COPY_SCALE', fk, power=-1, space='LOCAL')

                # Add master control constraint if necessary
                if hasattr(self, 'master_control') and self.master_control and len(ctrls.fk) > 1:
                    self.make_constraint(mch, 'COPY_ROTATION', ctrls.master, space='LOCAL')

    ####################################################
    # Tweak MCH chain

    @stage.rig_bones
    def rig_tweak_mch_chain(self):
        # Create tweak mch constraints
        if self.segmented_fk:
            mch = self.bones.mch
            targets = self.check_mch_targets()

            for i, mch, p, c, n in zip(count(0), mch.tweak, *targets):
                self.rig_tweak_mch_bone(i, mch, self.copy_scale_bone() or self.root_bone, p, c, n)
        else:
            super().rig_tweak_mch_chain()

    ####################################################
    # Deform bones

    def scale_deform_bone(self, deform, target):
        if self.segmented_fk:
            self.make_constraint(deform, 'COPY_SCALE', self.root_bone)
            counter_volume = self.make_constraint(
                deform, 'COPY_SCALE', target, use_offset=True,
                use_y=False, target_space='LOCAL', owner_space='LOCAL'
            )
            self.make_driver(
                counter_volume, 'power', expression='1 - var * 0.5',
                variables=[(self.default_prop_bone, 'volume_deform')]
            )
        else:
            super().scale_deform_bone(deform, target)
    
    """
    @stage.apply_bones
    def fix_deform_shear(self):
        if self.segmented_fk:
            for deform in self.bones.deform:
                self.get_bone(deform).inherit_scale = 'NONE'
            if hasattr(self.bones.mch, 'deform'):
                for mch in self.bones.mch.deform:
                    self.get_bone(mch).inherit_scale = 'NONE'
    """
    
    ####################################################
    # UI

    def segmented_fk_ui(self, layout, params):
        split = layout.split(align=True)
        split.row(align=True).prop(params, "segmented_fk", toggle=True)
        r = split.row(align=True)
        r.row(align=True).prop(params, "segmented_align", toggle=True)
        if not params.segmented_fk:
            r.enabled = False

    ####################################################
    # SETTINGS

    @classmethod
    def add_parameters(self, params):
        super().add_parameters(params)

        params.segmented_fk = bpy.props.BoolProperty(
            name="Segmented FK",
            description="Isolate FK controller scaling",
            default=False
            )
        
        params.segmented_align = bpy.props.BoolProperty(
            name="Align Segments",
            description="Align segment scaling by default for better control; may result in unexprected master scaling behavior",
            default=True
            )


    @classmethod
    def parameters_ui(self, layout, params):
        self.segmented_fk_ui(self, layout, params)
        super().parameters_ui(layout, params)


class ConnectingBendyRig(BaseBendyRig):
    """
    Bendy rig that can connect to a (tweak of its) parent, as well as attach its tip to another bone.
    """

    def initialize(self):
        super().initialize()

        self.incoming = self.params.incoming
        self.incoming_connect = self.params.incoming_connect
        self.incoming_align = self.params.incoming_align
        self.incoming_scale = self.params.incoming_scale
        self.incoming_scale_uniform = self.params.incoming_scale_uniform
        self.incoming_tweak = None
        self.incoming_bone = None
        self.incoming_parent = None

        self.tip_bone = None
        self.tip_scale = self.params.tip_scale
        self.tip_scale_uniform = self.params.tip_scale_uniform

    def prepare_bones(self):
        '''Get parent bone'''
        first_org_b = self.get_bone(self.bones.org[0])
        if first_org_b.parent:
            self.incoming_parent = first_org_b.parent.name

    ####################################################
    # Control chain

    @stage.parent_bones
    def set_incoming_connection(self):
        '''Check if connecting parents exist and move tweaks'''
        first_org = self.bones.org[0]
        first_org_b = self.get_bone(first_org)

        first_tweak = self.bones.ctrl.tweak[0]
        first_tweak_mch = self.bones.mch.tweak[0]

        x_axis = first_org_b.x_axis
        connect = None
        align = None

        # Incoming tweak
        parent = None
        if hasattr(self, 'rigify_parent') and self.rigify_parent:
            parent = self.rigify_parent

        if self.incoming == 'TWEAK' and parent and hasattr(parent.bones, 'ctrl') and hasattr(parent.bones.ctrl, 'tweak'):
            parent_tweaks = parent.bones.ctrl.tweak
            delta = distance(self.obj, first_org, parent_tweaks[0])
            self.incoming_tweak = parent_tweaks[0]
            for tweak in parent_tweaks:
                dist = distance(self.obj, first_org, tweak)
                if dist < delta:
                    delta = dist
                    self.incoming_tweak = tweak
            
            bone_in = self.get_bone(self.incoming_tweak)

            if self.incoming_connect:
                connect = bone_in.head
            
            if self.incoming_align:
                roll = self.incoming_tweak
                if self.incoming_tweak == parent_tweaks[0]:
                    align = bone_in.head - bone_in.tail

                elif self.incoming_tweak == parent_tweaks[-1]:
                    align = bone_in.tail - bone_in.head

        # Incoming bone
        elif self.incoming == 'BONE' and self.params.incoming_bone and self.params.incoming_bone in self.obj.data.edit_bones:
            self.incoming_bone = self.params.incoming_bone
            bone_in = self.get_bone(self.incoming_bone)

            if self.incoming_connect:
                connect = bone_in.head
            
            if self.incoming_align:
                roll = self.incoming_bone
                align = bone_in.tail - bone_in.head
        
        # Incoming parent
        elif self.incoming == 'PARENT' and self.incoming_parent:
            if self.incoming_connect or self.incoming_align:
                parent_bone = self.get_bone(self.incoming_parent)
                d_head = (first_org_b.head - parent_bone.head).length
                d_tail = (first_org_b.head - parent_bone.tail).length
                head = True if d_head < d_tail else False

            if self.incoming_connect:
                connect = parent_bone.head if head else parent_bone.tail
            
            if self.incoming_align:
                align = parent_bone.head - parent_bone.tail if head else parent_bone.tail - parent_bone.head
                roll = self.incoming_parent

        # Connect
        if connect:
            first_def = self.bones.deform[0]
            first_def_b = self.get_bone(first_def)
            first_def_b.head = connect
            align_bone_x_axis(self.obj, first_def, x_axis)
            copy_bone_position(self.obj, first_def, first_tweak_mch, length=self.get_bone(first_tweak_mch).length)
            copy_bone_position(self.obj, first_def, first_tweak, length=self.get_bone(first_tweak).length)
            if not self.org_transform == 'FK':
                copy_bone_position(self.obj, first_def, self.bones.org[0])

        # Align
        if align:
            align_bone_y_axis(self.obj, first_tweak_mch, align)
            align_bone_roll(self.obj, first_tweak_mch, roll)
            copy_bone_position(self.obj, first_tweak_mch, first_tweak)

        # Tip
        if real_bone(self.obj, self.params.tip_bone):
            self.tip_bone = self.params.tip_bone

    ####################################################
    # Tweak chain
    
    @stage.rig_bones
    def rig_tweak_chain(self):
        '''Copy scale offset for connected tweak'''
        if self.incoming_tweak or self.incoming_bone:
            make_incoming_scale = self.incoming_scale
        else:
            make_incoming_scale = False

        if make_incoming_scale:
            use_make_uniform = True if self.incoming == 'TWEAK' else self.incoming_scale_uniform

            self.make_constraint(
                self.bones.ctrl.tweak[0],
                'COPY_SCALE',
                self.incoming_tweak or self.incoming_bone,
                use_make_uniform=use_make_uniform,
                use_offset=True,
                target_space='LOCAL',
                owner_space='LOCAL'
            )

        # Tip scale offset
        if self.tip_bone:
            self.make_constraint(
                self.bones.ctrl.tweak[-1],
                'COPY_SCALE',
                self.tip_bone,
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

        if self.incoming == 'TWEAK' and self.incoming_tweak:
            # Parent first tweak MCH to incoming tweak
            self.set_bone_parent(mch, self.incoming_tweak)
        
        elif self.incoming == 'BONE' and self.incoming_bone:
            # Parent to specified bone
            self.set_bone_parent(mch, self.incoming_bone)
        
        elif self.incoming == 'PARENT' and self.incoming_parent:
            # If not tweak, parent to actual parent
            self.set_bone_parent(mch, self.incoming_parent)
        
        elif not self.incoming == 'NONE':
            # Without parent use root
            self.set_bone_parent(mch, self.root_bone)
        
        # Re-parent tip tweak mch
        if self.tip_bone:
            self.set_bone_parent(self.bones.mch.tweak[-1], self.tip_bone)

    ####################################################
    # UI

    def incoming_ui(self, layout, params):
        if not params.incoming == 'NONE':
            layout = layout.box()
        layout.row().prop(params, 'incoming')

        if params.incoming == 'BONE':
            layout.row().prop(params, 'incoming_bone')

        if not params.incoming == 'NONE':
            r = layout.row(align=True)
            r.prop(params, 'incoming_connect', toggle=True)
            r.prop(params, 'incoming_align', toggle=True)
            if params.incoming == 'BONE' and not params.incoming_bone:
                r.enabled = False
        
        if params.incoming == 'BONE' or params.incoming == 'TWEAK':
            split = layout.split(align=True)
            r = split.row(align=True)
            r.prop(params, 'incoming_scale', toggle=True)
            if params.incoming == 'BONE' and not params.incoming_bone:
                r.enabled = False
            r = split.row(align=True)
            r.prop(params, 'incoming_scale_uniform', toggle=True)
            if params.incoming == 'BONE' and not params.incoming_bone or not params.incoming_scale:
                r.enabled = False

    def tip_ui(self, layout, params):
        if params.tip_bone:
            layout = layout.box()
        
        layout.row().prop(params, 'tip_bone')

        if params.tip_bone:
            split = layout.split(align=True)
            r = split.row(align=True)
            r.prop(params, 'tip_scale', toggle=True)
            if not params.tip_bone:
                r.enabled = False
            r = split.row(align=True)
            r.prop(params, 'tip_scale_uniform', toggle=True)
            if not params.tip_bone or not params.tip_scale:
                r.enabled = False

    ##############################
    # Settings

    @classmethod
    def add_parameters(self, params):
        super().add_parameters(params)

        params.incoming = bpy.props.EnumProperty(
            items=[
                ('NONE', "Default", "Default"),
                ('PARENT', "To Parent", "Connect first tweak to parent"),
                ('TWEAK', "Merge Tweaks", "Merge with closest parent tweak"),
                ('BONE', "Define Bone", "Specify parent for first tweak by name"),
            ],
            name="First Tweak",
            default='NONE',
            description="Connection point for the first tweak of the B-Bone chain"
        )

        params.incoming_connect = bpy.props.BoolProperty(
            name="Connect First",
            default=True,
            description="Move first tweak to its parent"
        )

        params.incoming_align = bpy.props.BoolProperty(
            name="Align First",
            default=True,
            description="Align first tweak to its parent for a smooth curve"
        )

        params.incoming_bone = bpy.props.StringProperty(
            name="First Parent",
            default="",
            description="Parent for the first tweak"
        )

        params.incoming_scale = bpy.props.BoolProperty(
            name="First Scale Offset",
            default=True,
            description="Add copy scale constraint to first tweak, offsetting it by its parent's scale"
        )

        params.incoming_scale_uniform = bpy.props.BoolProperty(
            name="Make Uniform",
            default=False,
            description="Make first tweak scale offset uniform"
        )

        params.tip_bone = bpy.props.StringProperty(
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
        self.incoming_ui(self, layout, params)
        self.tip_ui(self, layout, params)
        super().parameters_ui(layout, params)


class MasterControlBendyRig(BaseBendyRig):
    """
    Connecting Bendy with a master controller.
    """

    def initialize(self):
        super().initialize()

        self.master_control = self.params.master_control
        self.master_rotation_mode = self.params.master_rotation_mode

    ####################################################
    # Master control

    @stage.generate_bones
    def make_master_control(self):
        if self.master_control:
            org = self.bones.org[0]
            self.bones.ctrl.master = self.copy_bone(org, make_derived_name(org, 'ctrl', '_master'))
    
    @stage.parent_bones
    def parent_master_control(self):
        if self.master_control:
            self.set_bone_parent(self.bones.ctrl.master, self.root_bone)

    @stage.configure_bones
    def configure_master_control(self):
        if self.master_control:
            master = self.bones.ctrl.master
            bone = self.get_bone(master)
            bone.lock_location = (True, True, True)
            bone.lock_scale = (True, True, True)
            bone.rotation_mode = self.master_rotation_mode

    @stage.generate_widgets
    def make_master_control_widget(self):
        if self.master_control:
            ctrls = self.bones.ctrl
            bone = ctrls.master
            create_ballsocket_widget(self.obj, bone, size=0.7)
            transform = ctrls.fk[-1] if self.tip_bone else ctrls.tweak[-1]
            set_bone_widget_transform(self.obj, bone, transform)

    
    ####################################################
    # Control chain

    @stage.rig_bones
    def rig_control_chain(self):
        '''Add master control constraints if no MCH found'''
        if self.master_control and not hasattr(self.bones.mch, 'fk'):
            for ctrl in self.bones.ctrl.fk:
                self.make_constraint(ctrl, 'COPY_ROTATION', self.bones.ctrl.master, mix_mode='BEFORE', target_space='LOCAL', owner_space='LOCAL')

    ####################################################
    # UI

    def master_control_ui(self, layout, params):
        split = layout.row(align=True).split(align=True)
        split.row(align=True).prop(params, "master_control", toggle=True)
        r = split.row(align=True)
        r.prop(params, "master_rotation_mode", text="")
        if not params.master_control:
            r.enabled=False

    ####################################################
    # SETTINGS

    @classmethod
    def add_parameters(self, params):
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

        params.master_rotation_mode = bpy.props.EnumProperty(
            name="Default Master Control Rotation Mode",
            items=rotation_modes,
            default='XYZ',
            description="Default rotation mode for master control"
        )

        params.master_control = bpy.props.BoolProperty(
            name="Master Control",
            description="Add master controller for the whole chain",
            default=False
            )

    @classmethod
    def parameters_ui(self, layout, params):
        self.master_control_ui(self, layout, params)
        super().parameters_ui(layout, params)


class ParentSwitchBendyRig(BaseBendyRig):
    """
    WIP

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
        self.set_bone_parent(self.bones.mch.parent, self.rig_parent_bone)


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