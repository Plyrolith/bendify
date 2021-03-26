#=============================================
# Constraint creation utilities
#=============================================

def make_armature_constraint(
        obj,
        owner,
        subtargets,
        index=0,
        extend=True,
        **options
    ):
    """
    Creates armature constraint utilizing targeting given bones
    """

    # Find/create constraint
    if not self.extend or not any(c for c in owner.constraints if c.type == 'ARMATURE'):
        arma = owner.constraints.new('ARMATURE')
    else:
        arma = [c for c in owner.constraints if c.type == 'ARMATURE'][0]

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
    if index >= 0:
        i = owner.constraints.find(arma.name)
        owner.constraints.move(i, index)
    
    # Options
    for p, v in options.items():
        setattr(arma, p, v)
