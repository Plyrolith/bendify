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

from rigify.utils.widgets import create_widget


def create_sub_tweak_widget(rig, bone_name, size=1.0, bone_transform_name=None):
    """ Creates a empty-shaped sub tweak widget.
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
    """ Creates a square widget, mostly used by facial rigs.
    """
    obj = create_widget(rig, bone_name, bone_transform_name)
    if obj != None:
        verts = [
            (  0.5 * size, -2.9802322387695312e-08 * size,  0.5 * size ),
            ( -0.5 * size, -2.9802322387695312e-08 * size,  0.5 * size ),
            (  0.5 * size,  2.9802322387695312e-08 * size, -0.5 * size ),
            ( -0.5 * size,  2.9802322387695312e-08 * size, -0.5 * size ),
        ]

        edges = [(0, 1), (2, 3), (0, 2), (3, 1) ]
        faces = []

        mesh = obj.data
        mesh.from_pydata(verts, edges, faces)
        mesh.update()
        mesh.update()