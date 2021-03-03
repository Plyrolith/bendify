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

from math import pi

from rigify.utils.widgets import create_widget, obj_to_bone
from rigify.rigs.widgets import create_gear_widget

WGT_PREFIX = "WGT-"  # Prefix for widget objects

def create_properties_widget(rig, bone_name, size=1.0, bone_transform_name=None, text=""):
    """
    Creates a property (gear) widget with additional text.
    """
    obj = create_gear_widget(rig, bone_name, size * 8.887729560524728, bone_transform_name)

    if text and obj:
        D = bpy.data
        text_name = WGT_PREFIX + rig.name + '_' + bone_name + '_TEMP'
        text_crv = D.curves.new(text_name, 'FONT')
        text_crv.fill_mode = 'NONE'
        text_crv.align_x = 'CENTER'
        text_crv.align_y = 'CENTER'
        text_crv.overflow = 'SCALE'
        text_crv.text_boxes[0].width = 1
        text_crv.text_boxes[0].x = -0.5
        text = text.replace("\\n", "\n")
        text_crv.body = text

        text_crv_obj = D.objects.new(text_name, text_crv)
        text_mesh = D.meshes.new_from_object(text_crv_obj)
        D.objects.remove(text_crv_obj)
        D.curves.remove(text_crv)
        text = D.objects.new(text_name, text_mesh)
        obj_to_bone(text, rig, bone_name, bone_transform_name)
        text.rotation_euler[0] -= pi / 2

        bpy.context.scene.collection.objects.link(text)
        bpy.context.scene.collection.objects.link(obj)
        override = bpy.context.copy()
        override['selected_objects'] = [text, obj]
        override['active_object'] = obj
        override['view_layer']['objects'] = {}
        override['view_layer']['objects']['selected'] = [text, obj]
        override['view_layer']['objects']['active'] = obj
        bpy.ops.object.join(override)
        #bpy.context.scene.collection.objects.unlink(text)
        #bpy.context.scene.collection.objects.unlink(obj)


def create_sub_tweak_widget(rig, bone_name, size=1.0, bone_transform_name=None):
    """
    Creates a empty-shaped sub tweak widget.
    """
    obj = create_widget(rig, bone_name, bone_transform_name)
    if obj != None:
        verts = [
            (0.0000, 0.0000, size),
            (0.0000, 0.0000, -size),
            (0.0000, size, 0.0000),
            (-size, 0.0000, 0.0000),
            (size, 0.0000, 0.0000),
            (0.0000, 0.0000, 0.0000)
        ]
        edges = [
            (0, 5),
            (1, 5),
            (5, 2),
            (5, 3),
            (4, 5)
        ]
        mesh = obj.data
        mesh.from_pydata(verts, edges, [])
        mesh.update()
        mesh.update()


def create_square_widget(rig, bone_name, size=1.0, bone_transform_name=None):
    """
    Creates a square widget, mostly used by facial rigs.
    """
    obj = create_widget(rig, bone_name, bone_transform_name)
    if obj != None:
        verts = [
            (  0.5 * size, -2.9802322387695312e-08 * size,  0.5 * size ),
            ( -0.5 * size, -2.9802322387695312e-08 * size,  0.5 * size ),
            (  0.5 * size,  2.9802322387695312e-08 * size, -0.5 * size ),
            ( -0.5 * size,  2.9802322387695312e-08 * size, -0.5 * size ),
        ]
        
        edges = [(0, 1), (2, 3), (0, 2), (3, 1)]
        faces = []

        mesh = obj.data
        mesh.from_pydata(verts, edges, faces)
        mesh.update()
        mesh.update()


def create_simple_arrow_widget(rig, bone_name, size=1.0, bone_transform_name=None, invert=False):
    """
    Creates a simple arrow widget.
    """
    obj = create_widget(rig, bone_name, bone_transform_name)
    if obj != None:
        y = -1 if invert else 1
        verts = [
            (0 * size, 0 * size, 0 * size),
            (0 * size, 0.85 * size * y, 0 * size),
            (0.1 * size, 0.85 * size * y, 0 * size),
            (0 * size, 1 * size * y, 0 * size),
            (-0.1 * size, 0.85 * size * y, 0 * size)
        ]

        edges = [(0, 1), (1, 2), (2, 3), (3, 4), (1, 4)]
        faces = []

        mesh = obj.data
        mesh.from_pydata(verts, edges, faces)
        mesh.update()
        mesh.update()


def create_wide_arrow_widget(rig, bone_name, size=1.0, bone_transform_name=None, invert=False):
    """
    Creates a wide arrow widget.
    """
    obj = create_widget(rig, bone_name, bone_transform_name)
    if obj != None:
        y = -1 if invert else 1
        verts = [
            (0.1 * size, 0 * size, 0*size),
            (0.1 * size, 0.7 * size * y, 0 * size),
            (-0.1 * size, 0 * size, 0 * size),
            (-0.1 * size, 0.7 * size * y, 0 * size),
            (0.2 * size, 0.7 * size * y, 0 * size),
            (0 * size, 1 * size * y, 0 * size),
            (-0.2 * size, 0.7 * size * y, 0 * size),
        ]

        edges = [(0, 1), (2, 3), (1, 4), (4, 5), (3, 6), (5, 6), (0, 2)]
        faces = []

        mesh = obj.data
        mesh.from_pydata(verts, edges, faces)
        mesh.update()
        mesh.update()
