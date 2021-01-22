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
from rigify.utils.bones import align_bone_orientation, align_bone_x_axis, copy_bone_position, put_bone
from rigify.utils.layers import ControlLayersOption
from rigify.utils.misc import map_list
from rigify.utils.naming import make_derived_name
from rigify.utils.widgets_basic import create_bone_widget

from .bendy_chain_rigs import BaseBendyRig, ComplexStretchBendyRig

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
    # Control chain

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
        return threewise_nozip(self.bones.mch.arma)

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

# Combine between the following

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
            bend.bbone_easein = 1.0 if self.bend_easein else 0.0
            bend.bbone_easeout = 1.0 if self.bend_easeout else 0.0
    
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
        layout.row().prop(params, 'bend', toggle=True)
        r = layout.row(align=True)
        r.prop(params, 'bend_easein', text="CTRL Ease In", toggle=True)
        r.prop(params, 'bend_easeout', text="CTRL Ease Out", toggle=True)
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

        params.bend_easein = bpy.props.BoolProperty(
            name="Control Ease In",
            default=True,
            description="Easing in for the control curve"
        )

        params.bend_easeout = bpy.props.BoolProperty(
            name="Control Ease Out",
            default=True,
            description="Easing out for the control curve"
        )

    @classmethod
    def parameters_ui(self, layout, params):
        self.bend_ui(self, layout, params)
        self.rotation_mode_tweak_ui(self, layout, params)
        self.org_transform_ui(self, layout, params)
        self.bbones_ui(self, layout, params)
        ControlLayersOption.TWEAK.parameters_ui(layout, params)


class CurvyStretchyRig(BaseStretchyRig):
    """
    Bendy stretchy rig
    """

class ParentedStretchyRig(BaseStretchyRig):
    """
    Bendy stretchy rig
    """

class ScalingStretchyRig(BaseStretchyRig):
    """
    Bendy stretchy rig
    """