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

from rigify.base_rig import BaseRig, stage
from rigify.utils.naming import strip_org, make_derived_name
from rigify.utils.misc import map_list
from rigify.utils.layers import ControlLayersOption
from rigify.utils.rig import connected_children_names
from rigify.utils.bones import put_bone, copy_bone_position, align_bone_roll, align_bone_x_axis, align_bone_y_axis
from rigify.utils.widgets_basic import create_sphere_widget

from .utils.bones import align_bone, align_bone_to_bone_axis, distance, real_bone
from .utils.misc import threewise_nozip
from .utils.widgets_bendy import create_sub_tweak_widget

class BendyRig(BaseRig):
    """
    Base bendy rig with driven B-Bones
    """

    def find_org_bones(self, bone):
        return [bone.name] + connected_children_names(self.obj, bone.name)

    min_chain_length = 1

    def initialize(self):
        if len(self.bones.org) < self.min_chain_length:
            self.raise_error("Input to rig type must be a chain of {} or more bones.", self.min_chain_length)
        
        self.bbone_segments = self.params.bbones_spine
        self.bbone_easein = self.params.bbones_easein
        self.bbone_easeout = self.params.bbones_easeout
        self.bbone_ease = self.params.bbone_ease
        self.bbone_scale = self.params.bbone_scale

        self.rotation_mode_tweak = self.params.rotation_mode_tweak
        self.org_transform = self.params.org_transform

        self.volume_deform_default = self.params.volume_deform_default
        self.volume_deform_panel = self.params.volume_deform_panel

        self.keep_axis = 'SWING_Y'
        self.root_bone = self.get_bone(self.base_bone).parent.name if self.get_bone(self.base_bone).parent else "root"
        self.default_prop_bone = None

    def parent_bones(self):
        self.rig_parent_bone = self.get_bone_parent(self.bones.org[0])

    ####################################################
    # Master control

    @stage.configure_bones
    def configure_volume_deform_properties(self):
        ctrls = self.bones.ctrl
        master = self.default_prop_bone
        if master:
            self.make_property(
                master,
                'volume_deform',
                default=self.volume_deform_default,
                max=100.0,
                soft_min=0.0,
                soft_max=max(self.volume_deform_default, 1.0),
                description='Volume variation for DEF bones'
            )

            if self.volume_deform_panel:
                panel = self.script.panel_with_selected_check(self, ctrls.flatten())
                panel.custom_prop(
                    master,
                    'volume_deform',
                    text=strip_org(self.base_bone) + ' Deform Volume Variation',
                    slider=True
                )

    ####################################################
    # B-Bone Utils

    def ease_bbone(self, bone, segments=8, ease_in=1.0, ease_out=1.0, handle_start=None, handle_end=None):
        pbone = self.get_bone(bone)
        pbone.bbone_segments = segments
        pbone.bbone_easein = ease_in
        pbone.bbone_easeout = ease_out
        pbone.bbone_handle_type_start = 'TANGENT' if handle_start else 'AUTO'
        pbone.bbone_handle_type_end = 'TANGENT' if handle_start else 'AUTO'
        pbone.bbone_custom_handle_start = self.get_bone(handle_start)
        pbone.bbone_custom_handle_end = self.get_bone(handle_end)

    def drivers_bbone_ease(self, bone, handle_start, handle_end):
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

    def drivers_bbone_scale(self, bone, handle_start, handle_end):
        pbone = self.get_bone(bone)
        space = 'LOCAL_SPACE'
        v_type = 'TRANSFORMS'

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
    # Tweak chain

    @stage.generate_bones
    def make_tweak_chain(self):
        orgs = self.bones.org
        self.bones.ctrl.tweak = map_list(self.make_tweak_bone, count(0), orgs + orgs[-1:])
        self.default_prop_bone = self.bones.ctrl.tweak[0]

    def make_tweak_bone(self, i, org):
        name = self.copy_bone(org, 'tweak_' + strip_org(org), parent=False, scale=0.5)

        if i == len(self.bones.org):
            put_bone(self.obj, name, self.get_bone(org).tail)

        return name

    @stage.parent_bones
    def parent_tweak_chain(self):
        for tweak in self.bones.ctrl.tweak:
            self.set_bone_parent(tweak, self.root_bone)

    @stage.configure_bones
    def configure_tweak_chain(self):
        for args in zip(count(0), self.bones.ctrl.tweak):
            self.configure_tweak_bone(*args)

    def configure_tweak_bone(self, i, tweak):
        tweak_pb = self.get_bone(tweak)
        tweak_pb.rotation_mode = self.rotation_mode_tweak

    @stage.generate_widgets
    def make_tweak_widgets(self):
        for tweak in self.bones.ctrl.tweak:
            self.make_tweak_widget(tweak)

    def make_tweak_widget(self, tweak):
        create_sphere_widget(self.obj, tweak)

    ##############################
    # ORG chain

    @stage.parent_bones
    def parent_org_chain(self):
        for org, deform in zip(self.bones.org, self.bones.deform):
            self.set_bone_parent(org, deform)

    @stage.rig_bones
    def rig_org_chain(self):
        ctrls = self.bones.ctrl
        for org, deform, tweak, next_tweak in zip(self.bones.org, self.bones.deform, ctrls.tweak, ctrls.tweak[1:]):
            self.rig_org_bone(org, deform, tweak, next_tweak)
            
    def rig_org_bone(self, org, deform, tweak, next_tweak):
        if self.org_transform == 'TWEAKS':
            #self.make_constraint(org, 'COPY_TRANSFORMS', deform)
            self.make_constraint(org, 'COPY_SCALE', tweak, use_y=False, power=0.5, use_offset=True, target_space='LOCAL', owner_space='LOCAL')
            self.make_constraint(org, 'COPY_SCALE', next_tweak, use_y=False, power=0.5, use_offset=True, target_space='LOCAL', owner_space='LOCAL')
        elif self.org_transform == 'TWEAK':
            #self.make_constraint(org, 'COPY_TRANSFORMS', deform)
            self.make_constraint(org, 'COPY_SCALE', tweak, use_y=False, use_offset=True, target_space='LOCAL', owner_space='LOCAL')
        elif self.org_transform == 'DEF':
            pass
            #self.make_constraint(org, 'COPY_TRANSFORMS', deform)
        #elif self.org_transform == 'FK':
        #    self.make_constraint(org, 'COPY_TRANSFORMS', fk)

    ####################################################
    # Deform bones

    @stage.generate_bones
    def make_deform_chain(self):
        self.bones.deform = map_list(self.make_deform_bone, count(0), self.bones.org)

    def make_deform_bone(self, i, org):
        name = self.copy_bone(org, make_derived_name(org, 'def'), parent=True, bbone=True)
        if self.bbone_segments:
            self.get_bone(name).bbone_segments = self.bbone_segments
        return name

    @stage.parent_bones
    def parent_deform_chain(self):
        deforms = self.bones.deform
        self.parent_bone_chain(deforms, use_connect=True)
        self.set_bone_parent(deforms[0], self.root_bone)

    @stage.parent_bones
    def ease_deform_chain(self):
        tweaks = self.bones.ctrl.tweak
        for i, deform, tweak, next_tweak in zip(count(0), self.bones.deform, tweaks, tweaks[1:]):
            ease_in = 0.0 if i == 0 and not self.bbone_easein else 1.0
            ease_out = 0.0 if i == len(self.bones.deform) - 1 and not self.bbone_easeout else 1.0
            self.ease_bbone(deform, self.bbone_segments, ease_in, ease_out, tweak, next_tweak)

    @stage.rig_bones
    def rig_deform_chain(self):
        ctrls = self.bones.ctrl
        for args in zip(self.bones.deform, ctrls.tweak, ctrls.tweak[1:]):
            self.rig_deform_bone(*args, self.root_bone)
    
    def rig_deform_bone(self, bone, handle_start, handle_end, scale):
        self.make_constraint(bone, 'COPY_LOCATION', handle_start)

        if not self.bbone_handles == 'NONE':
            self.make_constraint(bone, 'COPY_ROTATION', handle_start)
        
        self.make_constraint(bone, 'COPY_SCALE', scale, space='CUSTOM', space_object=self.obj, space_subtarget=self.root_bone)
        
        self.make_constraint(bone, 'DAMPED_TRACK', handle_end)
        stretch = self.make_constraint(bone, 'STRETCH_TO', handle_end)
        self.make_driver(stretch, 'bulge', variables=[(self.default_prop_bone, 'volume_deform')])

    @stage.rig_bones
    def drivers_deform_chain(self):
        ctrls = self.bones.ctrl
        for args in zip(self.bones.deform, ctrls.tweak, ctrls.tweak[1:]):
            self.drivers_deform_bone(*args)
    
    def drivers_deform_bone(self, bone, handle_start, handle_end):
        if self.bbone_ease:
            self.drivers_bbone_ease(bone, handle_start, handle_end)
        if self.bbone_scale:
            self.drivers_bbone_scale(bone, handle_start, handle_end)

    ####################################################
    # UI
    
    def org_transform_ui(self, layout, params):
        layout.row().prop(params, 'org_transform', text="ORGs")

    def bbones_ui(self, layout, params):
        layout.row().prop(params, 'bbones_spine')
        r = layout.row(align=True)
        r.prop(params, 'bbones_easein', text="Ease In", toggle=True)
        r.prop(params, 'bbones_easeout', text="Ease Out", toggle=True)
        r = layout.row(align=True)
        r.prop(params, 'bbone_ease', text="Ease Drivers", toggle=True)
        r.prop(params, 'bbone_scale', text="Scale Drivers", toggle=True)
    
    def volume_deform_ui(self, layout, params):
        r = layout.row(align=True)
        r.prop(params, 'volume_deform_default', slider=True)
        r.prop(params, 'volume_deform_panel', text="", icon='OPTIONS')

    ####################################################
    # SETTINGS
    
    @stage.finalize
    def finalize_armature_display(self):
        '''New function to set rig viewport display'''
        self.obj.data.display_type = 'BBONE'
    
    @classmethod
    def add_parameters(self, params):
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

        params.bbone_ease = bpy.props.BoolProperty(
            name="Ease Drivers",
            default=True,
            description="B-Bone easing driven by tweak"
        )

        params.bbone_scale = bpy.props.BoolProperty(
            name="Scale Drivers",
            default=True,
            description="B-Bone scaling driven by tweak"
        )

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

        params.org_transform = bpy.props.EnumProperty(
            name="ORG Transform base",
            items=[
                #('FK', "FK", "FK"),
                ('DEF', "Deforms", "Deforms"),
                ('TWEAK', "Single Tweak", "Single Tweak"),
                ('TWEAKS', "Between Tweaks", "BetweenTweaks"),
            ],
            default='DEF',
            description="Source of ORG transformation; useful to determine children's behaviour"
        )

        params.volume_deform_default = bpy.props.FloatProperty(
            name="Deform Volume Variation Default",
            default=1.0,
            soft_min=0.0,
            soft_max=1.0,
            description="Default value for deform bone chain stretch volume variation"
        )

        params.volume_deform_panel = bpy.props.BoolProperty(
            name="Deform Volume Variation Panel",
            default=False,
            description="Add panel to control volume variation to the UI"
        )

    @classmethod
    def parameters_ui(self, layout, params):
        self.org_transform_ui(self, layout, params)
        self.bbones_ui(self, layout, params)
        self.volume_deform_ui(self, layout, params)


# Advanced variations, mixable


class HandleBendyRig(BendyRig):
    """
    Bendy rig with prerequisites for autmatic handles
    """

    def initialize(self):
        super().initialize()
        self.bbone_handles = self.params.bbone_handles

    ####################################################
    # Tweak Targets

    def check_mch_parents(self):
        '''Return array of parents for tweak MCHs'''
        return [self.root_bone]

    def check_mch_targets(self):
        '''Return array of triple target lists (previous, current & next)'''
        return threewise_nozip(self.check_mch_parents())
    
    ####################################################
    # Tweak MCH chain

    @stage.generate_bones
    def make_tweak_mch_chain(self):
        if self.bbone_handles == 'TANGENT':
            orgs = self.bones.org
            self.bones.mch.tweak = map_list(self.make_tweak_mch_bone, count(0), orgs + orgs[-1:])

    def make_tweak_mch_bone(self, i, org):
        name = make_derived_name(org, 'mch', '_tweak')
        name = self.copy_bone(org, name, parent=False, scale=0.5)

        if i == len(self.bones.org):
            put_bone(self.obj, name, self.get_bone(org).tail)
        
        return name

    @stage.parent_bones
    def parent_tweak_mch_chain(self):
        if self.bbone_handles == 'TANGENT':
            mchs = self.bones.mch.tweak
            parents = self.check_mch_parents()

            for mch, parent in zip(mchs, parents):
                self.set_bone_parent(mch, parent, inherit_scale='FIX_SHEAR')

    @stage.parent_bones
    def align_tweak_mch_chain(self):
        if self.bbone_handles == 'TANGENT':
            mchs = self.bones.mch.tweak
            targets = self.check_mch_targets()
            
            for tweak, p, c, n in zip(mchs, *targets):
                align_bone(self.obj, tweak, p, c, n, next_tail=True if c == n else False)
    
    @stage.rig_bones
    def rig_tweak_mch_chain(self):
        if self.bbone_handles == 'TANGENT':
            mch = self.bones.mch
            parents = self.check_mch_parents()
            targets = self.check_mch_targets()

            for args in zip(count(0), mch.tweak, parents, *targets):
                self.rig_tweak_mch_bone(*args)

    def rig_tweak_mch_bone(self, i, mch, scale_bone, prev_target, curr_target, next_target):
        if prev_target and next_target:
            self.make_constraint(mch, 'COPY_LOCATION', prev_target)
            #self.make_constraint(mch, 'DAMPED_TRACK', next_target, head_tail=1 if curr_target == next_target else 0)
            self.make_constraint(mch, 'STRETCH_TO', next_target, head_tail=1 if curr_target == next_target else 0, bulge=0, volume='NO_VOLUME', keep_axis=self.keep_axis)
            self.make_constraint(mch, 'COPY_LOCATION', curr_target)
        self.make_constraint(mch, 'COPY_SCALE', scale_bone, space='CUSTOM', space_object=self.obj, space_subtarget=self.root_bone)#, use_make_uniform=True)

    ####################################################
    # Tweak chain

    @stage.parent_bones
    def parent_tweak_chain(self):
        tweaks = self.bones.ctrl.tweak
        parents = self.bones.mch.tweak if self.bbone_handles == 'TANGENT' else self.check_mch_parents()
        for tweak, parent in zip(tweaks, parents):
            self.set_bone_parent(tweak, parent)

    @stage.parent_bones
    def align_tweak_chain(self):
        if self.bbone_handles == 'TANGENT':
            tweaks = self.bones.ctrl.tweak
            targets = self.check_mch_targets()
            
            for tweak, p, c, n in zip(tweaks, *targets):
                align_bone(self.obj, tweak, p, c, n, next_tail=True if c == n else False)
    
    def configure_tweak_bone(self, i, tweak):
        super().configure_tweak_bone(i, tweak)
        tweak_pb = self.get_bone(tweak)
        tweak_pb.lock_rotation_w = self.bbone_handles == 'NONE'
        tweak_pb.lock_rotation[0] = not self.bbone_handles == 'TANGENT'
        tweak_pb.lock_rotation[1] = self.bbone_handles == 'NONE'
        tweak_pb.lock_rotation[2] = not self.bbone_handles == 'TANGENT'
        tweak_pb.lock_scale = (not self.bbone_scale, not self.bbone_ease, not self.bbone_scale)

    ####################################################
    # Deform chain

    @stage.parent_bones
    def ease_deform_chain(self):
        tweaks = self.bones.ctrl.tweak
        for i, deform, tweak, next_tweak in zip(count(0), self.bones.deform, tweaks, tweaks[1:]):
            ease_in = 0.0 if i == 0 and not self.bbone_easein else 1.0
            ease_out = 0.0 if i == len(self.bones.deform) - 1 and not self.bbone_easeout else 1.0
            handle_start = tweak if self.bbone_handles == 'TANGENT' else None
            handle_end = next_tweak if self.bbone_handles == 'TANGENT' else None
            self.ease_bbone(deform, self.bbone_segments, ease_in, ease_out, handle_start, handle_end)

    ####################################################
    # UI

    def rotation_mode_tweak_ui(self, layout, params):
        layout.row().prop(params, 'rotation_mode_tweak', text="Tweaks")

    def bbones_ui(self, layout, params):
        box = layout.box()
        super().bbones_ui(self, box, params)
        box.row().prop(params, 'bbone_handles', text="Handles", toggle=True)

    ####################################################
    # SETTINGS
    
    @classmethod
    def add_parameters(self, params):
        super().add_parameters(params)

        params.bbone_handles = bpy.props.EnumProperty(
            name="B-Bone Handles",
            items=[
                ('NONE', "None", "None"),
                ('Y', "Y Rotation Only", "Y Rotation Only"),
                ('TANGENT', "Full Tangent", "Full Tangent")
            ],
            default='TANGENT',
            description="B-Bone handles alignment"
        )

    @classmethod
    def parameters_ui(self, layout, params):
        self.rotation_mode_tweak_ui(self, layout, params)
        super().parameters_ui(layout, params)


class ComplexBendyRig(BendyRig):
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
            for mch in self.bones.mch.deform:
                self.set_bone_parent(mch, self.root_bone)

    @stage.apply_bones
    def apply_deform_mch_chain(self):
        if self.complex_stretch:
            for deform, mch in zip(self.bones.deform, self.bones.mch.deform):
                copy_bone_position(self.obj, deform, mch)

    @stage.rig_bones
    def rig_deform_mch_chain(self):
        if self.complex_stretch:
            ctrls = self.bones.ctrl
            for args in zip(count(0), self.bones.mch.deform, ctrls.tweak, ctrls.tweak[1:], ctrls.fk):
                self.rig_deform_mch_bone(*args)

    def rig_deform_mch_bone(self, i, bone, handle_start, handle_end, scale):
        self.make_constraint(bone, 'COPY_LOCATION', handle_start)
        self.make_constraint(bone, 'COPY_SCALE', scale)
        self.make_constraint(bone, 'DAMPED_TRACK', handle_end)
        stretch = self.make_constraint(bone, 'STRETCH_TO', handle_end)
        self.make_driver(stretch, 'bulge', variables=[(self.default_prop_bone, 'volume_deform')])

    ####################################################
    # Deform bones

    @stage.rig_bones
    def rig_deform_chain(self):
        if self.complex_stretch:
            ctrls = self.bones.ctrl
            for args in zip(self.bones.deform, ctrls.tweak, ctrls.tweak[1:], self.bones.mch.deform):
                self.rig_deform_bone(*args)
        else:
            super().rig_deform_chain()

    def rig_deform_bone(self, bone, handle_start, handle_end, scale):
        if self.complex_stretch:
            self.make_constraint(bone, 'COPY_LOCATION', handle_start)
            if not self.bbone_handles == 'NONE':
                self.make_constraint(bone, 'COPY_ROTATION', handle_start, space='CUSTOM', space_object=self.obj, space_subtarget=self.root_bone)
            self.make_constraint(bone, 'DAMPED_TRACK', handle_end)
            self.make_constraint(bone, 'COPY_SCALE', scale)  
        else:
            super().rig_deform_bone(bone, handle_start, handle_end, scale)

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
            description="Additional mechanical layer to separate stretch matrix and enable better non-uniform scaling at cost of additional complexity and non-standard hierarchy; worse export compatibiliy",
            default=False
            )

    @classmethod
    def parameters_ui(self, layout, params):
        self.complex_stretch_ui(self, layout, params)
        super().parameters_ui(layout, params)


class ConnectingBendyRig(BendyRig):
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
        base_bone = self.get_bone(self.base_bone)
        if base_bone.parent:
            self.incoming_parent = base_bone.parent.name

    ####################################################
    # Control chain

    @stage.parent_bones
    def set_incoming_connection(self):
        '''Check if connecting parents exist and move tweaks'''
        base_bone = self.get_bone(self.base_bone)

        first_tweak = self.bones.ctrl.tweak[0]
        if self.bbone_handles == 'TANGENT':
            first_tweak_mch = self.bones.mch.tweak[0]

        x_axis = base_bone.x_axis
        connect = None
        align = None

        # Incoming tweak
        parent = None
        if hasattr(self, 'rigify_parent') and self.rigify_parent:
            parent = self.rigify_parent

        if self.incoming == 'TWEAK' and parent and hasattr(parent.bones, 'ctrl') and hasattr(parent.bones.ctrl, 'tweak'):
            parent_tweaks = parent.bones.ctrl.tweak
            delta = distance(self.obj, self.base_bone, parent_tweaks[0])
            self.incoming_tweak = parent_tweaks[0]
            for tweak in parent_tweaks:
                dist = distance(self.obj, self.base_bone, tweak)
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
                d_head = (base_bone.head - parent_bone.head).length
                d_tail = (base_bone.head - parent_bone.tail).length
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
            copy_bone_position(self.obj, first_def, first_tweak, length=self.get_bone(first_tweak).length)
            if self.bbone_handles == 'TANGENT':
                copy_bone_position(self.obj, first_def, first_tweak_mch, length=self.get_bone(first_tweak_mch).length)
            if not self.org_transform == 'FK':
                copy_bone_position(self.obj, first_def, self.base_bone)

        # Align

        if align:
            align_bone_y_axis(self.obj, first_tweak, align)
            align_bone_roll(self.obj, first_tweak, roll)
            if self.bbone_handles == 'TANGENT':
                copy_bone_position(self.obj, first_tweak, first_tweak_mch)

        # Tip
        if real_bone(self.obj, self.params.tip_bone):
            self.tip_bone = self.params.tip_bone

    ####################################################
    # Tweak chain
    
    @stage.rig_bones
    def rig_tweak_chain(self):
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
        tweaks = self.bones.ctrl.tweak

        if self.incoming_tweak:
            create_sub_tweak_widget(self.obj, tweaks[0], size=0.25)
            tweaks = tweaks[1:]
        
        for tweak in tweaks:
            super().make_tweak_widget(tweak)

    ####################################################
    # Tweak MCH chain

    @stage.apply_bones
    def parent_incoming_apply(self):
        '''Re-parent first and tip tweak MCH'''
        first = self.bones.mch.tweak[0] if self.bbone_handles == 'TANGENT' else self.bones.ctrl.tweak[0]
        
        if self.incoming == 'TWEAK' and self.incoming_tweak:
            # Parent first to incoming tweak
            self.set_bone_parent(first, self.incoming_tweak)
        
        elif self.incoming == 'BONE' and self.incoming_bone:
            # Parent to specified bone
            self.set_bone_parent(first, self.incoming_bone)
        
        elif self.incoming == 'PARENT' and self.incoming_parent:
            # If not tweak, parent to actual parent
            self.set_bone_parent(first, self.incoming_parent)
        
        elif not self.incoming == 'NONE':
            # Without parent use root
            self.set_bone_parent(first, self.root_bone)
        
        # Re-parent tip
        if self.tip_bone:
            tip = self.bones.mch.tweak[-1] if self.bbone_handles == 'TANGENT' else self.bones.ctrl.tweak[-1]
            self.set_bone_parent(tip, self.tip_bone)

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


class AlignedBendyRig(BendyRig):
    """
    Bendy rig with start and end Y-alignment to other bones
    """

    def initialize(self):
        super().initialize()

        self.align_y_start = self.params.align_y_start
        self.align_y_end = self.params.align_y_end
        self.align_y_start_axis = self.params.align_y_start_axis
        self.align_y_end_axis = self.params.align_y_end_axis
        self.align_y_start_preserve = self.params.align_y_start_preserve
        self.align_y_end_preserve = self.params.align_y_end_preserve

    ####################################################
    # Align

    @stage.apply_bones
    def align_tweak_mch_ends(self):
        if hasattr(self.bones.mch, 'tweak'):
            mchs = self.bones.mch.tweak
            if real_bone(self.obj, self.align_y_start):
                align_bone_to_bone_axis(self.obj, mchs[0], self.align_y_start, self.align_y_start_axis, self.align_y_start_preserve)
            if real_bone(self.obj, self.align_y_end):
                align_bone_to_bone_axis(self.obj, mchs[-1], self.align_y_end, self.align_y_end_axis, self.align_y_end_preserve)

    @stage.apply_bones
    def align_tweak_ends(self):
        if hasattr(self.bones.ctrl, 'tweak'):
            ctrls = self.bones.ctrl.tweak
            if real_bone(self.obj, self.align_y_start):
                align_bone_to_bone_axis(self.obj, ctrls[0], self.align_y_start, self.align_y_start_axis, self.align_y_start_preserve)
            if real_bone(self.obj, self.align_y_end):
                align_bone_to_bone_axis(self.obj, ctrls[-1], self.align_y_end, self.align_y_end_axis, self.align_y_end_preserve)
        
    ####################################################
    # UI

    def align_ui(self, layout, params):
        box = layout.box()
        box.row().prop(params, 'align_y_start')
        if params.align_y_start:
            r = box.row(align=True)
            r.prop(params, 'align_y_start_axis')
            r.prop(params, 'align_y_start_preserve', text="")
        
        box.row().prop(params, 'align_y_end')
        if params.align_y_end:
            r = box.row(align=True)
            r.prop(params, 'align_y_end_axis')
            r.prop(params, 'align_y_end_preserve', text="")

    ####################################################
    # SETTINGS

    @classmethod
    def add_parameters(self, params):
        super().add_parameters(params)

        axes = [
            ('X', "X", "X"),
            ('-X', "-X", "-X"),
            ('Y', "Y", "Y"),
            ('-Y', "-Y", "-Y"),
            ('Z', "Z", "Z"),
            ('-Z', "-Z", "-Z"),
        ]

        preserves = [
            ('X', "X Preserve", "X Preserve"),
            ('Z', "Z Preserve", "Z Preserve"),
        ]

        params.align_y_start_axis = bpy.props.EnumProperty(
            items=axes,
            name="Axis",
            default='Y',
            description="Orientation guide bone axis to use for start"
        )

        params.align_y_end_axis = bpy.props.EnumProperty(
            items=axes,
            name="Axis",
            default='Y',
            description="Orientation guide bone axis to use for end"
        )

        params.align_y_start_preserve = bpy.props.EnumProperty(
            items=preserves,
            name="Preserve",
            default='X',
            description="Preserve this axis while re-orienting start"
        )

        params.align_y_end_preserve = bpy.props.EnumProperty(
            items=preserves,
            name="Preserve",
            default='Z',
            description="Preserve this axis while re-orienting end"
        )

        params.align_y_start = bpy.props.StringProperty(
            name="Start Orientation",
            default="",
            description="Orientation guide bone for start"
        )


        params.align_y_end = bpy.props.StringProperty(
            name="End Orientation",
            default="",
            description="Orientation guide bone for end"
        )


    @classmethod
    def parameters_ui(self, layout, params):
        self.align_ui(self, layout, params)
        super().parameters_ui(layout, params)