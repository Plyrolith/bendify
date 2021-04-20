from rigify.utils.errors import MetarigError

#=============================================
# Constraint creation utilities
#=============================================

def make_armature_constraint(
        obj,
        owner,
        subtargets,
        weights_reset=True,
        weights_equalize=False,
        extend=True,
        index=None,
        **options
    ):
    """
    Creates armature constraint utilizing targeting given bones
    """

    # Find/create constraint
    if not extend or not any(c for c in owner.constraints if c.type == 'ARMATURE'):
        arma = owner.constraints.new('ARMATURE')
    else:
        arma = [c for c in owner.constraints if c.type == 'ARMATURE'][0]

    # Reset weights of existing targets
    if weights_reset:
        for t in arma.targets:
            t.weight = 0

    # Targets
    if isinstance(subtargets, str):
        subtargets = [subtargets]
    for i, subtarget in enumerate(subtargets):
        target = obj
        if weights_reset and i == 0:
            weight = 1
        else:
            weight = 0
        if isinstance(subtarget, dict):
            if "subtarget" in subtarget:
                bone_name = subtarget["subtarget"]
            elif "name" in subtarget:
                bone_name = subtarget["name"]
            if "target" in subtarget:
                target = subtarget["target"]
            if "weight" in subtarget:
                weight = subtarget["weight"]
        else:
            bone_name = subtarget

        if not bone_name in target.data.bones:
            raise MetarigError("Armature target {} not found".format(bone_name))

        if any(t.subtarget == bone_name and t.target == target for t in arma.targets):
            t = [t for t in arma.targets if t.subtarget == bone_name and t.target == target][0]
        else:
            t = arma.targets.new()
        
        t.target = target
        t.subtarget = bone_name
        t.weight = weight

    # Move armature
    if index and index >= 0:
        i = owner.constraints.find(arma.name)
        owner.constraints.move(i, index)
    
    # Options
    for p, v in options.items():
        setattr(arma, p, v)

    return arma