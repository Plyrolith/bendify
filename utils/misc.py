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

from itertools import tee

#=============================================
# Iterators
#=============================================

def threewise_nozip(iterable):
    "s -> (None,s0,s1), (s0,s1,s2), (s1,s2,s3), ..."
    prv, c, nxt = tee(iterable, 3)
    p = [None]
    p.extend(prv)
    n = list(nxt)[1:]
    n.append(None)
    return p, c, n


def threewise(iterable):
    "s -> (None,s0,s1), (s0,s1,s2), (s1,s2,s3), ..."
    prv, c, nxt = tee(iterable, 3)
    p = [None]
    p.extend(prv)
    n = list(nxt)[1:]
    n.append(None)
    return zip(p, c, n)