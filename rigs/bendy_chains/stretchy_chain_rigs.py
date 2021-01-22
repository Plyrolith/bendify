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
from rigify.utils.bones import align_bone_orientation, align_bone_x_axis, copy_bone_position, put_bone, set_bone_widget_transform
from rigify.utils.layers import ControlLayersOption
from rigify.utils.misc import map_list
from rigify.utils.naming import make_derived_name
from rigify.utils.widgets_basic import create_bone_widget
from rigify.utils.widgets_special import create_neck_bend_widget

from .bendy_chain_rigs import BaseBendyRig, ComplexStretchBendyRig

from ...utils.bones import real_bone
from ...utils.misc import threewise_nozip
from ...utils.mechanism import make_armature_constraint


class BaseStretchyRig(BaseBendyRig):
    """
    Base stretchy rig
    """

    ####################################################
    # Master control

    @stage.configure_bones
    def configure_master_properties(self):
        super().configure_master_properties()
        ctrls = self.bones.ctrl
        master = self.default_prop_bone
        panel = self.script.panel_with_selected_check(self, ctrls.flatten())
        self.make_property(master, 'volume_stretch', default=1.0, max=100.0, soft_max=1.0, description='Volume variation for CTRL stretch')
        panel.custom_prop(master, 'volume_stretch', text='Stretch Volume Variation', slider=True)

    ##############################
    # Stretch control

    @stage.generate_bones
    def make_control_chain(self):
        orgs = self.bones.org

        start = make_derived_name(orgs[0], 'ctrl', "_in")
        start = self.bones.ctrl.start = self.copy_bone(orgs[0], start, parent=False, scale=0.75)
        self.default_prop_bone = self.bones.ctrl.start

        end = make_derived_name(orgs[-1], 'ctrl', "_out")
        end = self.bones.ctrl.end = self.copy_bone(orgs[-1], end, parent=False, scale=0.75)
        put_bone(self.obj, end, self.get_bone(orgs[-1]).tail)

    @stage.parent_bones
    def parent_control_chain(self):
        ctrls = self.bones.ctrl
        for ctrl in (ctrls.start, ctrls.end):
            self.set_bone_parent(ctrl, self.root_bone)

    @stage.configure_bones
    def configure_control_chain(self):
        orgs = self.bones.org
        ctrls = self.bones.ctrl
        self.copy_bone_properties(orgs[0], ctrls.start)
        self.copy_bone_properties(orgs[-1], ctrls.end)

    @stage.generate_widgets
    def make_control_widgets(self):
        ctrls = self.bones.ctrl
        for ctrl in (ctrls.start, ctrls.end):
            create_bone_widget(self.obj, ctrl, r1=1.0, l1=-0.5, r2=1.0, l2=0.5)

    ####################################################
    # Tweak Targets

    def check_mch_parents(self):
        return self.bones.mch.arma

    def check_mch_targets(self):
        return threewise_nozip(self.check_mch_parents())

    ####################################################
    # Tweak MCH chain

    @stage.rig_bones
    def rig_tweak_mch_chain(self):
        '''Scale from root'''
        mch = self.bones.mch
        #parents = self.check_mch_parents()
        targets = self.check_mch_targets()

        for i, mch, p, c, n  in zip(count(0), mch.tweak, *targets):
            self.rig_tweak_mch_bone(i, mch, self.root_bone, p, c, n)

    ####################################################
    # Stretch MCHs

    @stage.generate_bones
    def make_stretch_mch(self):
        orgs = self.bones.org
        stretch = make_derived_name(orgs[0], 'mch', "_stretch")
        self.bones.mch.stretch = self.copy_bone(orgs[0], stretch, parent=False)
        self.get_bone(stretch).tail = self.get_bone(orgs[-1]).tail
        align_bone_x_axis(self.obj, stretch, self.get_bone(orgs[0]).x_axis)
    
    @stage.parent_bones
    def parent_stretch_mch(self):
        self.set_bone_parent(self.bones.mch.stretch, self.root_bone)

    @stage.rig_bones
    def rig_stretch_mch(self):
        ctrls = self.bones.ctrl
        mch = self.bones.mch.stretch
        start = ctrls.start
        end = ctrls.end
        #scale = self.root_bone
        self.make_constraint(mch, 'COPY_LOCATION', start)
        #self.make_constraint(mch, 'COPY_SCALE', scale)
        self.make_constraint(mch, 'DAMPED_TRACK', end)

        # Stretch
        stretch = self.make_constraint(mch, 'STRETCH_TO', end)
        self.make_driver(stretch, 'bulge', variables=[(self.default_prop_bone, 'volume_stretch')])
    
    ####################################################
    # Armature MCHs

    @stage.generate_bones
    def make_arma_mch_chain(self):
        orgs = self.bones.org
        self.bones.mch.arma = map_list(self.make_arma_mch_bone, count(0), orgs + orgs[-1:])

    def make_arma_mch_bone(self, i, org):
        name = make_derived_name(org, 'mch', '_arma')
        name = self.copy_bone(org, name, parent=False)

        if i == len(self.bones.org):
            put_bone(self.obj, name, self.get_bone(org).tail)
        
        return name
    
    @stage.parent_bones
    def parent_arma_mch_chain(self):
        for arma in self.bones.mch.arma:
            self.set_bone_parent(arma, self.bones.mch.stretch)

    ##############################
    # ORG chain

    @stage.rig_bones
    def rig_org_chain(self):
        '''Set ORG transformation according to rig setting'''
        ctrls = self.bones.ctrl
        for org, deform, tweak, next_tweak, arma in zip(self.bones.org, self.bones.deform, ctrls.tweak, ctrls.tweak[1:], self.bones.mch.arma):
            self.rig_org_bone(org, deform, tweak, next_tweak, arma)

    ##############################
    # Deform chain

    @stage.rig_bones
    def rig_deform_chain(self):
        '''No copy scale'''
        ctrls = self.bones.ctrl
        for args in zip(count(0), self.bones.deform, ctrls.tweak, ctrls.tweak[1:]):
            self.rig_deform_bone(*args)
    
    ####################################################
    # SETTINGS

    @classmethod
    def parameters_ui(self, layout, params):
        self.rotation_mode_tweak_ui(self, layout, params)
        self.org_transform_ui(self, layout, params)
        self.bbones_ui(self, layout, params)
        ControlLayersOption.TWEAK.parameters_ui(layout, params)

# Combine between the following

class StraightStretchyRig(BaseStretchyRig):
    """
    Stretchy rig with aligned controls
    """

    def initialize(self):
        super().initialize()

        self.straight = self.params.straight
        self.straight_orientation = self.params.straight_orientation

    ##############################
    # Stretch control

    @stage.generate_bones
    def make_control_chain(self):
        super().make_control_chain()
        if self.straight:
            ctrls = self.bones.ctrl
            orgs = self.bones.org
            first_org = self.get_bone(orgs[0])
            last_org = self.get_bone(orgs[-1])
            for ctrl in (ctrls.start, ctrls.end):
                bone = self.get_bone(ctrl)
                length = bone.length
                bone.head = first_org.head
                bone.tail = last_org.tail
                bone.length = length
            put_bone(self.obj, ctrls.end, last_org.tail)
            align_bone_x_axis(self.obj, ctrls.start, last_org.x_axis if self.straight_orientation == 'LAST' else first_org.x_axis)
            align_bone_x_axis(self.obj, ctrls.end, first_org.x_axis if self.straight_orientation == 'FIRST' else last_org.x_axis)

    ####################################################
    # UI

    def straight_ui(self, layout, params):
        box = layout.box()
        box.row().prop(params, 'straight', toggle=True)
        r = box.row()
        r.prop(params, 'straight_orientation', expand=True)
        if not params.straight:
            r.enabled = False

    ####################################################
    # SETTINGS

    @classmethod
    def add_parameters(self, params):
        super().add_parameters(params)

        params.straight = bpy.props.BoolProperty(
            name="Straighten CTRLs",
            default=True,
            description="Align stretch controls to form a straight line by default"
        )

        params.straight_orientation = bpy.props.EnumProperty(
            items=[
                ('FIRST', "First", "First"),
                ('LAST', "Last", "Last"),
                ('BOTH', "Both", "Both")
            ],
            name="Orientation",
            default='FIRST',
            description="New orientation for stretch controllers"
        )


    @classmethod
    def parameters_ui(self, layout, params):
        self.straight_ui(self, layout, params)
        super().parameters_ui(layout, params)


class ComplexStretchStretchyRig(BaseStretchyRig, ComplexStretchBendyRig):
    """
    Stretchy rig with copied stretch constraints for better non-uniform scalability
    """

    ##############################
    # Deform MCH

    @stage.rig_bones
    def rig_deform_mch_chain(self):
        '''No copy scale'''
        if self.complex_stretch:
            ctrls = self.bones.ctrl
            for args in zip(count(0), self.bones.mch.deform, ctrls.tweak, ctrls.tweak[1:]):
                self.rig_deform_mch_bone(*args)


class BendyStretchyRig(BaseStretchyRig):
    """
    Bendy stretchy rig
    """
    def initialize(self):
        super().initialize()

        self.bend = self.params.bend
        self.bend_easein = self.params.bend_easein
        self.bend_easeout = self.params.bend_easeout

    ####################################################
    # Stretch MCHs

    @stage.generate_bones
    def make_bend_mch(self):
        orgs = self.bones.org
        bend = make_derived_name(orgs[0], 'mch', "_bend")
        self.bones.mch.bend = self.copy_bone(orgs[0], bend, parent=False)
        self.get_bone(bend).tail = self.get_bone(orgs[-1]).tail
        align_bone_x_axis(self.obj, bend, self.get_bone(orgs[0]).x_axis)

    @stage.parent_bones
    def parent_bend_mch(self):
        self.set_bone_parent(self.bones.mch.bend, self.root_bone)

    @stage.parent_bones
    def ease_bend_mch(self):
        if self.bend:
            bend = self.get_bone(self.bones.mch.bend)
            bend.bbone_segments = min(len(self.bones.org) * 3, 32)
            bend.bbone_handle_type_start = 'TANGENT'
            bend.bbone_handle_type_end = 'TANGENT'
            bend.bbone_custom_handle_start = self.get_bone(self.bones.ctrl.start)
            bend.bbone_custom_handle_end = self.get_bone(self.bones.ctrl.end)
            bend.bbone_easein = self.bend_easein
            bend.bbone_easeout = self.bend_easeout
    
    @stage.rig_bones
    def rig_bend_mch(self):
        if self.bend:
            ctrls = self.bones.ctrl
            mchs = self.bones.mch
            start = ctrls.start
            end = ctrls.end
            self.make_constraint(mchs.bend, 'COPY_LOCATION', start)
            self.make_constraint(mchs.bend, 'DAMPED_TRACK', end)
            self.make_constraint(mchs.bend, 'COPY_SCALE', mchs.stretch)
            self.bendy_drivers(mchs.bend, start, end)

    ####################################################
    # Armature MCHs
    
    @stage.apply_bones
    def apply_arma_mch_chain(self):
        if self.bend:
            for arma in self.bones.mch.arma:
                self.get_bone(arma).parent = None

    @stage.rig_bones
    def rig_arma_mch_chain(self):
        if self.bend:
            for arma in self.bones.mch.arma:
                owner = self.get_bone(arma)
                make_armature_constraint(self.obj, owner, [self.bones.mch.bend])

    ####################################################
    # UI

    def bend_ui(self, layout, params):
        box = layout.box()
        box.row().prop(params, 'bend', toggle=True)
        r = box.row(align=True)
        r.prop(params, 'bend_easein')
        r.prop(params, 'bend_easeout')
        if not params.bend:
            r.enabled = False

    ####################################################
    # SETTINGS

    @classmethod
    def add_parameters(self, params):
        super().add_parameters(params)

        params.bend = bpy.props.BoolProperty(
            name="Bend Between CTRLs",
            default=True,
            description="Use a bendy control curve between start and end handles"
        )

        params.bend_easein = bpy.props.FloatProperty(
            name="Ease In",
            default=1.0,
            description="Easing in for the control curve"
        )

        params.bend_easeout = bpy.props.FloatProperty(
            name="Ease Out",
            default=1.0,
            description="Easing out for the control curve"
        )

    @classmethod
    def parameters_ui(self, layout, params):
        self.bend_ui(self, layout, params)
        super().parameters_ui(layout, params)


class CurvyStretchyRig(BaseStretchyRig):
    """
    Stretchy rig with curve control
    """

    def initialize(self):
        super().initialize()

        self.curve_control = self.params.curve_control if len(self.bones.org) > 1 else False

    ####################################################
    # Utilities

    def bone_to_center(self, bone, bone_center, scale=0.25):
        # Match target
        copy_bone_position(self.obj, bone_center, bone, scale=scale)

        # Move to center of target
        b = self.get_bone(bone_center)
        position = b.head + (b.tail - b.head) / 2
        put_bone(self.obj, bone, pos=position)

    ####################################################
    # Tweak Targets

    def check_mch_parents(self):
        if self.curve_control:
            armas = self.bones.mch.arma
            curves = self.bones.mch.curve
            return (armas[0], *curves, armas[-1])
        else:
            return super().check_mch_parents()

    ####################################################
    # Curve control

    @stage.generate_bones
    def make_curve_ctrl(self):
        if self.curve_control:
            orgs = self.bones.org
            curve = make_derived_name(orgs[0], 'ctrl', "_curve")
            self.bones.ctrl.curve = self.copy_bone(orgs[0], curve, parent=False)
            self.bone_to_center(curve, self.bones.mch.stretch)

    @stage.parent_bones
    def parent_curve_ctrl(self):
        if self.curve_control:
            self.set_bone_parent(self.bones.ctrl.curve, self.bones.mch.curve_parent)

    @stage.configure_bones
    def configure_curve_ctrl(self):
        if self.curve_control:
            curve = self.bones.ctrl.curve
            bone = self.get_bone(curve)
            bone.lock_rotation = (True, True, True)
            bone.lock_rotation_w = True
            bone.lock_scale[1] = True

    @stage.generate_widgets
    def make_curve_widget(self):
        if self.curve_control:
            curve = self.bones.ctrl.curve
            create_neck_bend_widget(
                self.obj, curve,
                radius=1,
                head_tail=0.0,
            )

    ####################################################
    # Curve parent

    @stage.generate_bones
    def make_curve_parent_mch(self):
        if self.curve_control:
            orgs = self.bones.org
            parent = make_derived_name(orgs[0], 'mch', "_curve_parent")
            self.bones.mch.curve_parent = self.copy_bone(orgs[0], parent, parent=False)
            self.bone_to_center(parent, self.bones.mch.stretch)
    
    @stage.parent_bones
    def parent_curve_parent_mch(self):
        if self.curve_control:
            self.set_bone_parent(self.bones.mch.curve_parent, self.root_bone)

    @stage.rig_bones
    def rig_curve_parent_mch(self):
        if self.curve_control:
            ctrls = self.bones.ctrl
            self.make_constraint(self.bones.mch.curve_parent, 'COPY_TRANSFORMS', ctrls.start)
            self.make_constraint(self.bones.mch.curve_parent, 'COPY_TRANSFORMS', ctrls.end, influence=0.5)
            self.make_constraint(self.bones.mch.curve_parent, 'DAMPED_TRACK', ctrls.end)

    ####################################################
    # Curve MCHs

    @stage.generate_bones
    def make_curve_mch_chain(self):
        if self.curve_control:
            orgs = self.bones.org
            self.bones.mch.curve = map_list(self.make_curve_mch_bone, count(0), orgs[1:])

    def make_curve_mch_bone(self, i, org):
        name = make_derived_name(org, 'mch', '_curve')
        name = self.copy_bone(org, name, parent=False)
        return name
    
    @stage.parent_bones
    def parent_curve_mch_chain(self):
        if self.curve_control:
            curves = self.bones.mch.curve
            armas = self.bones.mch.arma[1:-1]
            for curve, arma in zip(curves, armas):
                self.set_bone_parent(curve, arma)
                align_bone_orientation(self.obj, curve, self.bones.mch.stretch)

    @stage.finalize
    def rig_curve_mch_chain(self):
        if self.curve_control:
            curves = self.bones.mch.curve
            curves_len = len(curves)
            for i, curve in zip(count(0), curves):
                # Parabolic influence
                step = 2 / (curves_len + 1)
                xval = (i + 1) * step
                influence = 2 * xval - xval ** 2

                self.make_constraint(
                    curve, 'COPY_LOCATION', self.bones.ctrl.curve,
                    influence=influence, space='LOCAL'
                )
    
    ####################################################
    # Curve MCHs

    @stage.rig_bones
    def rig_stretch_mch(self):
        super().rig_stretch_mch()
        self.make_constraint(self.bones.mch.stretch, 'COPY_SCALE', self.bones.ctrl.curve,
            space='LOCAL', use_offset=True)

    ####################################################
    # UI

    def curve_ui(self, layout, params):
        layout.row().prop(params, 'curve_control', toggle=True)

    ####################################################
    # SETTINGS

    @classmethod
    def add_parameters(self, params):
        super().add_parameters(params)

        params.curve_control = bpy.props.BoolProperty(
            name="Add Curve Control",
            default=False,
            description="Add a controller to alter the curvature from the center"
        )

    @classmethod
    def parameters_ui(self, layout, params):
        self.curve_ui(self, layout, params)
        super().parameters_ui(layout, params)


class ParentedStretchyRig(BaseStretchyRig):
    """
    Stretchy rig with armature constrained start and end handles
    """

    def initialize(self):
        super().initialize()

        self.parent_start = self.params.parent_start
        self.parent_end = self.params.parent_end

    ##############################
    # Control MCH

    @stage.generate_bones
    def make_control_start_mch(self):
        if self.parent_start:
            orgs = self.bones.org
            start = make_derived_name(orgs[0], 'mch', "_in")
            start = self.bones.mch.start = self.copy_bone(orgs[0], start, parent=False)

    @stage.apply_bones
    def parent_control_start_mch(self):
        if self.parent_start:
            self.set_bone_parent(self.bones.mch.start, self.root_bone)

    @stage.apply_bones
    def apply_control_start_mch(self):
        if real_bone(self.obj, self.parent_start):
            self.get_bone(self.bones.mch.start).parent = None

    @stage.rig_bones
    def rig_control_start_mch(self):
        if real_bone(self.obj, self.parent_start):
            owner = self.get_bone(self.bones.mch.start)
            make_armature_constraint(self.obj, owner, [self.parent_start])

    @stage.generate_bones
    def make_control_end_mch(self):
        if self.parent_end:
            orgs = self.bones.org
            end = make_derived_name(orgs[-1], 'mch', "_out")
            end = self.bones.mch.end = self.copy_bone(orgs[-1], end, parent=False)
            put_bone(self.obj, end, self.get_bone(orgs[-1]).tail)

    @stage.apply_bones
    def parent_control_end_mch(self):
        if self.parent_end:
            self.set_bone_parent(self.bones.mch.end, self.root_bone)

    @stage.apply_bones
    def apply_control_end_mch(self):
        if real_bone(self.obj, self.parent_start):
            self.get_bone(self.bones.mch.end).parent = None

    @stage.rig_bones
    def rig_control_end_mch(self):
        if real_bone(self.obj, self.parent_start):
            owner = self.get_bone(self.bones.mch.end)
            make_armature_constraint(self.obj, owner, [self.parent_end])

    ##############################
    # Stretch control

    @stage.parent_bones
    def parent_control_chain(self):
        super().parent_control_chain()
        ctrls = self.bones.ctrl
        mchs = self.bones.mch
        if self.parent_start:
            self.set_bone_parent(ctrls.start, mchs.start)
        if self.parent_end:
            self.set_bone_parent(ctrls.end, mchs.end)
            
    ####################################################
    # UI

    def parent_ui(self, layout, params):
        box = layout.box()
        box.row().prop(params, 'parent_start')
        box.row().prop(params, 'parent_end')

    ####################################################
    # SETTINGS

    @classmethod
    def add_parameters(self, params):
        super().add_parameters(params)

        params.parent_start = bpy.props.StringProperty(
            name="Start Parent",
            default="",
            description="Set the parent for the start handle of the stretchy control curve"
        )

        params.parent_end = bpy.props.StringProperty(
            name="End Parent",
            default="",
            description="Set the parent for the end handle of the stretchy control curve"
        )

    @classmethod
    def parameters_ui(self, layout, params):
        self.parent_ui(self, layout, params)
        super().parameters_ui(layout, params)


class ScalingStretchyRig(BaseStretchyRig):
    """
    Stretchy rig with volume scaling control
    """

    def initialize(self):
        super().initialize()

        self.scale_control = self.params.scale_control
        self.scale_space = self.params.scale_space

    ####################################################
    # Tweak MCH chain

    @stage.rig_bones
    def rig_tweak_mch_chain(self):
        if real_bone(self.obj, self.scale_control):
            mch = self.bones.mch
            #parents = self.check_mch_parents()
            targets = self.check_mch_targets()

            for i, mch, p, c, n  in zip(count(0), mch.tweak, *targets):
                self.rig_tweak_mch_bone(i, mch, self.scale_control, p, c, n)

    ##############################
    # Deform MCH

    @stage.configure_bones
    def configure_deform_mch_chain(self):
        if real_bone(self.obj, self.scale_control) and hasattr(self, 'complex_stretch') and self.complex_stretch:
            for mch in self.bones.mch.deform:
                self.make_constraint(mch, 'COPY_SCALE', self.scale_control,
                    target_space=self.scale_space, owner_space=self.scale_space)
    
    ##############################
    # Deform

    @stage.configure_bones
    def configure_deform_chain(self):
        if real_bone(self.obj, self.scale_control) and (not hasattr(self, 'complex_stretch') or not self.complex_stretch):
            for deform in self.bones.deform:
                self.make_constraint(deform, 'COPY_SCALE', self.scale_control,
                    target_space=self.scale_space, owner_space=self.scale_space)

    ####################################################
    # UI

    def scale_ui(self, layout, params):
        box = layout.box()
        box.row().prop(params, 'scale_control')
        if params.scale_control:
            box.row().prop(params, 'scale_space', expand=True)

    ####################################################
    # SETTINGS

    @classmethod
    def add_parameters(self, params):
        super().add_parameters(params)

        params.scale_control = bpy.props.StringProperty(
            name="Volume Copy",
            default="",
            description="Copy X/Y scale from this bone"
        )

        params.scale_space = bpy.props.EnumProperty(
            items=[
                ('LOCAL', "Local", "Local"),
                ('WORLD', "World", "World")
            ],
            name="Copy Scale Space",
            default='LOCAL',
            description="Target and owner space for scale control"
        )

    @classmethod
    def parameters_ui(self, layout, params):
        self.scale_ui(self, layout, params)
        super().parameters_ui(layout, params)