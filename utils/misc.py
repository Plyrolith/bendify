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
# Attributes
#=============================================

def attribute_return(base, attributes, iterable=False):
    """
    Returns value of attribute down the list hierarchy.
    'None' if any invalid attribute is encountered;
    '[]' if an iterable is expected.
    """
    def attr_iter(base, attribute):
        try:
            return getattr(base, attribute)
        except AttributeError:
            return None
    attribute = base
    for a in attributes:
        attribute = attr_iter(attribute, a)
    if not attribute and iterable:
        attribute = []
    return attribute

#=============================================
# Iterators
#=============================================

def threewise_nozip(iterable):
    "s -> (None,s0,s1), (s0,s1,s2), ... , (sY,sZ,None)"
    prv, c, nxt = tee(iterable, 3)
    p = [None] + list(prv)[:-1]
    n = list(nxt)[1:] + [None]
    return p, c, n


def threewise(iterable):
    "s -> (None,s0,s1), (s0,s1,s2), ... , (sY,sZ,None)"
    prv, c, nxt = tee(iterable, 3)
    p = [None] + list(prv)[:-1]
    n = list(nxt)[1:] + [None]
    return zip(p, c, n)

#=============================================
# Strings
#=============================================

def var_name(i):
    if i == 0:
        return "var"
    else:
        return "var_" + str(i).zfill(3)