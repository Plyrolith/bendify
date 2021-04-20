from rigify.utils.bones import align_bone_roll, align_bone_x_axis, \
align_bone_y_axis, align_bone_z_axis, get_bone, put_bone

#=============================================
# Math
#=============================================

def distance(obj, bone_name1, bone_name2, tail=False):
    """
    Return the distance between two bone heads (or tails)
    """
    bone1 = get_bone(obj, bone_name1)
    bone2 = get_bone(obj, bone_name2)
    pos1 = bone1.tail if tail else bone1.head
    pos2 = bone2.tail if tail else bone2.head

    return (pos1 - pos2).length

#=============================================
# Position
#=============================================

def connect_bone_to_bone(obj, bone_name, bone_name_target, tail=False, tail_target=False, keep_length=False):
    """
    Matches the bone head or tail to another bone's head or tail, preserving the x-axis
    """
    bone = obj.data.edit_bones[bone_name]
    target = obj.data.edit_bones[bone_name_target]
    x_axis = bone.x_axis
    length = bone.length
    target = target.tail if tail_target else target.head
    if tail:
        bone.tail = target
    else:
        bone.head = target
    align_bone_x_axis(obj, bone_name, x_axis)
    if keep_length:
        bone.length = length


def put_bone_to_bone(obj, bone_name, bone_name_target, tail_target=False, length=None, scale=None):
    """
    Places the a bone at another bone's head or tail
    """
    target = obj.data.edit_bones[bone_name_target]
    pos = target.tail if tail_target else target.head
    put_bone(obj, bone_name, pos, length=length, scale=scale)

#=============================================
# Aligning
#=============================================

def align_bone_to_bone_axis(obj, bone_name, bone_name_target, axis='Y', preserve='X'):
    """
    Matches the bone y-axis to specified axis of another bone
    """
    bone = obj.data.edit_bones[bone_name]
    target = obj.data.edit_bones[bone_name_target]
    length = bone.length

    # Get preservation vector
    if preserve == 'X':
        vec_preserve = bone.x_axis
    elif preserve == 'Z':
        vec_preserve = bone.z_axis
    
    # Get vector for Y alignment
    if axis.endswith('X'):
        vec_axis = target.x_axis
    elif axis.endswith('Y'):
        vec_axis = target.y_axis
    elif axis.endswith('Z'):
        vec_axis = target.z_axis
    
    if axis.startswith('-'):
        vec_axis.negate()
    
    # Align Y
    align_bone_y_axis(obj, bone_name, vec_axis)

    # Roll to preserved axis
    if preserve == 'X':
        align_bone_x_axis(obj, bone_name, vec_preserve)
    elif preserve == 'Z':
        align_bone_z_axis(obj, bone_name, vec_preserve)
    
    # Restore length
    bone.length = length

def align_bone_between_bones(obj, bone_name, prev_target, roll_target, next_target, prev_tail=False, next_tail=False):
    """
    Realign bone between two target bones and align X axis
    """
    if prev_target and next_target:
        n = get_bone(obj, next_target)
        p = get_bone(obj, prev_target)
        p_vec = p.tail if prev_tail else p.head
        n_vec = n.tail if next_tail else n.head
        vec = n_vec - p_vec
        if roll_target:
            r = get_bone(obj, roll_target)
            r_vec = r.x_axis
        align_bone_y_axis(obj, bone_name, vec)
        if roll_target:
            align_bone_x_axis(obj, bone_name, r_vec)