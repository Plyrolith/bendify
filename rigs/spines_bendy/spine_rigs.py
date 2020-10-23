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

from rigify.utils.layers import ControlLayersOption
from rigify.base_rig import stage
from rigify.rigs.spines.spine_rigs import BaseSpineRig, BaseHeadTailRig


class BaseSpineBendyRig(BaseSpineRig):
    """
    Spine rig with bendy tweaks.
    """

    ####################################################
    # BONES
    #
    # ctrl:
    #   master
    #     Main control.
    #   master_pivot
    #     Custom pivot under the master control.
    # mch:
    #   master_pivot
    #     Final output of the custom pivot.
    #
    ####################################################

    ####################################################
    # ORG bones

    @stage.parent_bones
    def parent_org_chain(self):
        # Set org parents to FK instead of tweak
        for org, fk in zip(self.bones.org, self.bones.ctrl.fk):
            self.set_bone_parent(org, fk)

    ####################################################
    # Tweak bones

    def configure_tweak_bone(self, i, tweak):
        # Fully unlocked tweaks
        tweak_pb = self.get_bone(tweak)
        tweak_pb.rotation_mode = 'ZXY'
    
    ####################################################
    # Deform bones
    @stage.parent_bones
    def parent_deform_chain(self):
        # New loop for parenting
        for args in zip(count(0), self.bones.deform, self.bones.org):
            self.parent_deform_bone(*args)

    def parent_deform_bone(self, i, deform, org):
        # New, set deform parent to org
        if i == 0:
            self.set_bone_parent(deform, self.rig_parent_bone)
        else:
            self.set_bone_parent(deform, org)

    @stage.parent_bones
    def rig_deform_chain_easing(self):
        # New function to set bbone easing in edit mode
        tweaks = self.bones.ctrl.tweak
        for args in zip(count(0), self.bones.deform, tweaks, tweaks[1:]):
            self.rig_deform_easing(*args)
        
    def rig_deform_easing(self, i, deform, tweak, next_tweak):
        # Easing per bone
        pbone = self.get_bone(deform)
        pbone.bbone_handle_type_start = 'TANGENT'
        pbone.bbone_handle_type_end = 'ABSOLUTE'
        pbone.bbone_custom_handle_start = self.get_bone(tweak)
        pbone.bbone_custom_handle_end = self.get_bone(next_tweak)    

    def rig_deform_bone(self, i, deform, tweak, next_tweak):
        # Added copy scale
        self.make_constraint(deform, 'COPY_TRANSFORMS', tweak)
        self.make_constraint(deform, 'COPY_SCALE', self.bones.ctrl.master)
        if next_tweak:
            self.make_constraint(deform, 'DAMPED_TRACK', next_tweak)
            self.make_constraint(deform, 'STRETCH_TO', next_tweak)

    ####################################################
    # SETTINGS
    
    @stage.configure_bones
    def configure_armature_display(self):
        # New function to set rig viewport display
        self.obj.data.display_type = 'BBONE'

class BaseHeadTailBendyRig(BaseHeadTailRig):
    """ Base for bendy head and tail rigs. """

    ####################################################
    # Tweak chain
 
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
        pbone.bbone_handle_type_start = 'TANGENT'
        pbone.bbone_handle_type_end = 'ABSOLUTE'
        pbone.bbone_custom_handle_start = self.get_bone(tweak)
        pbone.bbone_custom_handle_end = self.get_bone(next_tweak)

    ####################################################
    # SETTINGS
    
    @stage.configure_bones
    def configure_armature_display(self):
        # New function to set rig viewport display
        self.obj.data.display_type = 'BBONE'