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
    """
    s -> (None,s0,s1), (s0,s1,s2), ... , (sY,sZ,None)
    """
    prv, c, nxt = tee(iterable, 3)
    p = [None] + list(prv)[:-1]
    n = list(nxt)[1:] + [None]
    return p, c, n


def threewise(iterable):
    """
    s -> (None,s0,s1), (s0,s1,s2), ... , (sY,sZ,None)
    """
    prv, c, nxt = tee(iterable, 3)
    p = [None] + list(prv)[:-1]
    n = list(nxt)[1:] + [None]
    return zip(p, c, n)

#=============================================
# Strings
#=============================================

def var_name(i):
    """
    Return the equivalent variable name for int
    """
    if i == 0:
        return "var"
    else:
        return "var_" + str(i).zfill(3)