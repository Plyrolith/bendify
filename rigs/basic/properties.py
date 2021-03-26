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

from rigify.base_rig import BaseRig, stage
from rigify.base_generate import SubstitutionRig
from rigify.utils.naming import strip_org

from ...utils.widgets_bendy import create_properties_widget

class Rig(SubstitutionRig):
    """
    A raw copy rig, preserving the metarig bone as is, without the ORG prefix.
    """

    def substitute(self):
        # Strip the ORG prefix during the rig instantiation phase
        new_name = strip_org(self.base_bone)
        new_name = self.generator.rename_org_bone(self.base_bone, new_name)

        return [ self.instantiate_rig(PropertyRig, new_name) ]

class PropertyRig(BaseRig):
    """
    Rig that adds custom properties to UI
    """

    def initialize(self):
        self.panel_selected_only = self.params.panel_selected_only
        self.properties_widget_text = self.params.properties_widget_text

        #self.rigify_parent

    ####################################################
    # Properties

    @stage.configure_bones
    def configure_properties(self):
        if self.panel_selected_only:
            panel = self.script.panel_with_selected_check(self, [self.base_bone])
        else:
            panel = self.script.panel_with_selected_check(self, [self.base_bone])

        base = self.get_bone(self.base_bone)
        if hasattr(base, '["_RNA_UI"]'):
            prop_rna = base['_RNA_UI']

            if prop_rna:
                for prop in prop_rna:
                    p = prop_rna[prop]
                    text = p['description'] if hasattr(p, '["description"]') and p['description'] else prop
                    panel.custom_prop(
                        self.base_bone,
                        prop,
                        text=text,
                        slider=True if prop_rna[prop]['soft_min'] >= 0 and prop_rna[prop]['soft_max'] <= 12 else False
                    )
    
    @stage.generate_widgets
    def make_properties_widget(self):
        create_properties_widget(self.obj, self.base_bone, text=self.properties_widget_text)

    ####################################################
    # UI

    def properties_panel_ui(self, layout, params):
        layout.row().prop(params, 'properties_widget_text')
        #layout.row().prop(params, 'panel_selected_only', toggle=True)

    ####################################################
    # SETTINGS

    @classmethod
    def add_parameters(self, params):
        params.panel_selected_only = bpy.props.BoolProperty(
            name="Selected Only UI",
            default=False,
            description="Display UI panel only if this bone is selected"
        )

        params.properties_widget_text = bpy.props.StringProperty(
            name="Widget Text",
            default="",
            description="Text displayed in bone widget. Use \n for new lines"
        )

    @classmethod
    def parameters_ui(self, layout, params):
        self.properties_panel_ui(self, layout, params)

add_parameters = PropertyRig.add_parameters
parameters_ui = PropertyRig.parameters_ui