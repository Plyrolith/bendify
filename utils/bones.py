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

from rigify.utils.bones import align_bone_roll, align_bone_x_axis, \
align_bone_y_axis, align_bone_z_axis, get_bone


#=============================================
# Utilities
#=============================================

def real_bone(obj, bone_name):
    bones = obj.data.edit_bones if obj.mode == 'EDIT' else obj.pose.bones
    return bone_name and bone_name in bones

#=============================================
# Math
#=============================================

def distance(obj, bone_name1, bone_name2, tail=False):
    '''
    Return the distance between two bone heads (or tails)
    '''
    bone1 = get_bone(obj, bone_name1)
    bone2 = get_bone(obj, bone_name2)
    pos1 = bone1.tail if tail else bone1.head
    pos2 = bone2.tail if tail else bone2.head

    return (pos1 - pos2).length

#=============================================
# Aligning
#=============================================

def align_bone_to_bone_axis(obj, bone_name1, bone_name2, axis='Y', preserve='X'):
    '''
    Matches the bone y-axis to specified axis of another bone
    '''
    bone1 = obj.data.edit_bones[bone_name1]
    bone2 = obj.data.edit_bones[bone_name2]
    length = bone1.length

    # Get preservation vector
    if preserve == 'X':
        vec_preserve = bone1.x_axis
    elif preserve == 'Z':
        vec_preserve = bone1.z_axis
    
    # Get vector for Y alignment
    if axis.endswith('X'):
        vec_axis = bone2.x_axis
    elif axis.endswith('Y'):
        vec_axis = bone2.y_axis
    elif axis.endswith('Z'):
        vec_axis = bone2.z_axis
    
    if axis.startswith('-'):
        vec_axis.negate()
    
    # Align Y
    align_bone_y_axis(obj, bone_name1, vec_axis)

    # Roll to preserved axis
    if preserve == 'X':
        align_bone_x_axis(obj, bone_name1, vec_preserve)
    elif preserve == 'Z':
        align_bone_z_axis(obj, bone_name1, vec_preserve)
    
    # Restore length
    bone1.length = length

def align_bone(obj, bone_name, prev_target, roll_target, next_target, prev_tail=False, next_tail=False):
    '''
    Realign bone between two target bones and copy bone roll
    '''
    if prev_target and next_target:
        n = get_bone(obj, next_target)
        p = get_bone(obj, prev_target)
        p_vec = p.tail if prev_tail else p.head
        n_vec = n.tail if next_tail else n.head
        vec = n_vec - p_vec
        align_bone_y_axis(obj, bone_name, vec)
        if roll_target:
            align_bone_roll(obj, bone_name, roll_target)