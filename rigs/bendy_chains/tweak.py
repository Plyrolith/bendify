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

from rigify.utils.layers import ControlLayersOption

from ...bendy_rigs import HandleBendyRig, ComplexBendyRig, AlignedBendyRig, ConnectingBendyRig

class Rig(ConnectingBendyRig, AlignedBendyRig, ComplexBendyRig):
    """
    Simple bendy tweak chain
    """

    @classmethod
    def parameters_ui(self, layout, params):
        layout.row().prop(params, 'show_advanced')
        if params.show_advanced:
            box = layout.box()
            self.parent_ui(self, box, params)
            self.tip_ui(self, box, params)
            self.align_ui(self, box, params)
            self.complex_stretch_ui(self, box, params)
            self.rotation_mode_tweak_ui(self, box, params)
            self.org_transform_ui(self, box, params)
            self.volume_ui(self, box, params)
        box = layout.box()
        self.bbones_ui(self, box, params)
        #ControlLayersOption.TWEAK.parameters_ui(layout, params)
