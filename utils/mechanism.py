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

#=============================================
# Constraint creation utilities
#=============================================

def make_armature_constraint(
        obj,
        owner,
        subtargets,
        insert_index=None,
        **options
    ):
    """
    Creates armature constraint utilizing targeting given bones
    """

    # Create constraint
    arma = owner.constraints.new('ARMATURE')

    # Targets
    for i, subtarget in enumerate(subtargets):
        t = arma.targets.new()
        if "target" in subtarget:
            t.target = subtarget["target"]
        else:
            t.target = obj
        t.subtarget = subtarget
        if "weight" in subtarget:
            t.weight = subtarget["weight"]
        elif i == 0:
            t.weight = 1
        else:
            t.weight = 0

    # Move armature
    if insert_index:
        i = owner.constraints.find(arma.name)
        owner.constraints.move(i, insert_index)
    
    # Options
    for p, v in options.items():
        setattr(arma, p, v)
