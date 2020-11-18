import bpy, re
from mathutils import Vector
from rigify.utils import copy_bone, flip_bone
from rigify.utils import org, strip_org, make_deformer_name, connected_children_names, make_mechanism_name
from rigify.utils import create_widget
from rigify.utils.mechanism import make_property
from rigify.rigs.widgets import create_face_widget, create_eye_widget, create_eyes_widget, create_ear_widget, create_jaw_widget, create_teeth_widget

from ...utils.widgets_bendy import create_square_widget

script = """
all_controls   = [%s]
eyes_ctrl_name = '%s'

if is_selected(all_controls):
    layout.prop(pose_bones[eyes_ctrl_name], '["%s"]', slider=True)
"""


class Rig:

    def __init__(self, obj, bone_name, params):
        self.obj = obj

        b = self.obj.data.bones

        children = ["lid.T.L", "lid.T.R", "eye.L", "eye.R"]

        #create_pose_lib( self.obj )

        children     = [ org(b) for b in children ]
        grand_children = []

        for child in children:
            grand_children += connected_children_names( self.obj, child )

        self.org_bones   = [bone_name] + children + grand_children
        self.face_length = obj.data.bones[ self.org_bones[0] ].length
        self.params      = params

        if params.primary_layers_extra:
            self.primary_layers = list(params.primary_layers)
        else:
            self.primary_layers = None

        if params.secondary_layers_extra:
            self.secondary_layers = list(params.secondary_layers)
        else:
            self.secondary_layers = None

    def orient_org_bones(self):

        bpy.ops.object.mode_set(mode='EDIT')
        eb = self.obj.data.edit_bones

        # Adjust eye bones roll
        eb['ORG-eye.L'].roll = 0.0
        eb['ORG-eye.R'].roll = 0.0

    def symmetrical_split(self, bones):

        # RE pattern match right or left parts
        # match the letter "L" (or "R"), followed by an optional dot (".")
        # and 0 or more digits at the end of the the string
        left_pattern  = 'L\.?\d*$'
        right_pattern = 'R\.?\d*$'

        left  = sorted( [ name for name in bones if re.search( left_pattern,  name ) ] )
        right = sorted( [ name for name in bones if re.search( right_pattern, name ) ] )

        return left, right

    def create_deformation(self):
        org_bones = self.org_bones

        bpy.ops.object.mode_set(mode='EDIT')
        eb = self.obj.data.edit_bones

        def_bones = []
        for org in org_bones:
            if 'optic' in org or 'eye' in org:
                continue

            def_name = make_deformer_name( strip_org( org ) )
            def_name = copy_bone( self.obj, org, def_name )
            def_bones.append( def_name )

            eb[def_name].use_connect = False
            eb[def_name].parent      = None

        return { 'all' : def_bones }

    def create_ctrl(self, bones):
        org_bones = self.org_bones

        ## create control bones
        bpy.ops.object.mode_set(mode='EDIT')
        eb = self.obj.data.edit_bones

        eyeL_ctrl_name = strip_org(bones['eyes'][0])
        eyeR_ctrl_name = strip_org(bones['eyes'][1])

        eyeL_ctrl_name = copy_bone(self.obj, bones['eyes'][0], eyeL_ctrl_name)
        eyeR_ctrl_name = copy_bone(self.obj, bones['eyes'][1], eyeR_ctrl_name)
        eyes_ctrl_name = copy_bone(self.obj, bones['eyes'][0], 'eyes')

        eyeL_ctrl_e = eb[eyeL_ctrl_name]
        eyeR_ctrl_e = eb[eyeR_ctrl_name]
        eyes_ctrl_e = eb['eyes']

        # eyes ctrls
        eyeL_e = eb[bones['eyes'][0]]
        eyeR_e = eb[bones['eyes'][1]]

        interpupillary_distance = eyeL_e.head - eyeR_e.head
        distance = (eyeL_e.head - eyeR_e.head) * 3
        distance = distance.cross((0, 0, 1))

        eyeL_ctrl_e.head    += distance
        eyeR_ctrl_e.head    += distance
        eyes_ctrl_e.head[:] =  ( eyeL_ctrl_e.head + eyeR_ctrl_e.head ) / 2

        for bone in [ eyeL_ctrl_e, eyeR_ctrl_e, eyes_ctrl_e ]:
            # bone.tail[:] = bone.head + Vector( [ 0, 0, eyeL_e.length * 1.35 ] )
            bone.tail[:] = bone.head + Vector([0, 0, interpupillary_distance.length * 0.3144])

        ## Widget for transforming the both eyes
        eye_master_names = []
        for bone in bones['eyes']:
            eye_master = copy_bone(
                self.obj,
                bone,
                'master_' + strip_org(bone)
            )

            eye_master_names.append( eye_master )

        ## Assign widgets
        bpy.ops.object.mode_set(mode ='OBJECT')

        # Assign each eye widgets
        create_eye_widget( self.obj, eyeL_ctrl_name )
        create_eye_widget( self.obj, eyeR_ctrl_name )

        # Assign eyes widgets
        create_eyes_widget( self.obj, eyes_ctrl_name )

        # Assign each eye_master widgets
        for master in eye_master_names:
            create_square_widget(self.obj, master)

        return {
            'eyes'   : [
                eyeL_ctrl_name,
                eyeR_ctrl_name,
                eyes_ctrl_name,
            ] + eye_master_names
            }

    def create_tweak(self, bones):
        org_bones = self.org_bones

        ## create tweak bones
        bpy.ops.object.mode_set(mode ='EDIT')
        eb = self.obj.data.edit_bones

        tweaks = []

        for bone in bones:

            tweak_name = strip_org( bone )

            tweak_name = copy_bone( self.obj, bone, tweak_name )
            eb[ tweak_name ].use_connect = False
            eb[ tweak_name ].parent      = None

            tweaks.append( tweak_name )

            eb[ tweak_name ].tail[:] = \
                eb[ tweak_name ].head + Vector(( 0, 0, self.face_length / 7 ))

        bpy.ops.object.mode_set(mode ='OBJECT')
        pb = self.obj.pose.bones

        primary_tweaks = [
            "lid.B.L.002", "lid.T.L.002", "lid.B.R.002", "lid.T.R.002"
        ]

        for bone in tweaks:
            if bone in primary_tweaks:
                if self.primary_layers:
                    pb[bone].bone.layers = self.primary_layers
                create_face_widget( self.obj, bone, size = 1.5 )
            else:
                if self.secondary_layers:
                    pb[bone].bone.layers = self.secondary_layers
                create_face_widget( self.obj, bone )

        return { 'all' : tweaks }

    def all_controls(self):
        org_bones = self.org_bones

        org_to_ctrls = {
            'eyes'   : ['eye.L', 'eye.R']
        }

        tweak_exceptions = [] # bones not used to create tweaks

        org_to_ctrls = { key : [ org( bone ) for bone in org_to_ctrls[key] ] for key in org_to_ctrls.keys() }

        tweak_exceptions += [ 'optic' ]
        tweak_exceptions += org_to_ctrls.keys()

        tweak_exceptions = [ org( bone ) for bone in tweak_exceptions ]

        org_to_tweak = sorted( [ bone for bone in org_bones if bone not in tweak_exceptions ] )

        ctrls  = self.create_ctrl( org_to_ctrls )
        tweaks = self.create_tweak( org_to_tweak )

        return { 'ctrls' : ctrls, 'tweaks' : tweaks }

    def create_mch(self):
        org_bones = self.org_bones
        bpy.ops.object.mode_set(mode ='EDIT')
        eb = self.obj.data.edit_bones

        # Create eyes mch bones
        eyes = [ bone for bone in org_bones if 'eye' in bone ]

        mch_bones = { strip_org( eye ) : [] for eye in eyes }

        for eye in eyes:
            mch_name = make_mechanism_name( strip_org( eye ) )
            mch_name = copy_bone( self.obj, eye, mch_name )
            eb[ mch_name ].use_connect = False
            eb[ mch_name ].parent      = None

            mch_bones[ strip_org( eye ) ].append( mch_name )

            mch_name = copy_bone( self.obj, eye, mch_name )
            eb[ mch_name ].use_connect = False
            eb[ mch_name ].parent      = None

            mch_bones[ strip_org( eye ) ].append( mch_name )

            eb[ mch_name ].head[:] = eb[ mch_name ].tail
            eb[ mch_name ].tail[:] = eb[ mch_name ].head + Vector( ( 0, 0, 0.005 ) )

        # Create the eyes' parent mch
        optic = [ bone for bone in org_bones if 'optic' in bone ].pop()

        mch_name = 'eyes_parent'
        mch_name = make_mechanism_name( mch_name )
        mch_name = copy_bone( self.obj, optic, mch_name )
        eb[ mch_name ].use_connect = False
        eb[ mch_name ].parent      = None

        eb[ mch_name ].length /= 4

        mch_bones['eyes_parent'] = [ mch_name ]

        # Create the lids' mch bones
        all_lids       = [ bone for bone in org_bones if 'lid' in bone ]
        lids_L, lids_R = self.symmetrical_split( all_lids )

        all_lids = [ lids_L, lids_R ]

        mch_bones['lids'] = []

        for i in range( 2 ):
            for bone in all_lids[i]:
                mch_name = make_mechanism_name( strip_org( bone ) )
                mch_name = copy_bone( self.obj, eyes[i], mch_name  )

                eb[ mch_name ].use_connect = False
                eb[ mch_name ].parent      = None

                eb[ mch_name ].tail[:] = eb[ bone ].head

                mch_bones['lids'].append( mch_name )

        return mch_bones

    def parent_bones(self, all_bones):
        org_bones = self.org_bones
        bpy.ops.object.mode_set(mode ='EDIT')
        eb = self.obj.data.edit_bones

        optic_name = [ bone for bone in org_bones if 'optic' in bone ].pop()

        # Initially parenting all bones to the optic org bone.
        for category in list( all_bones.keys() ):
            for area in list( all_bones[category] ):
                for bone in all_bones[category][area]:
                    eb[ bone ].parent = eb[ optic_name ]

        ## Parenting all deformation bones and org bones

        # Parent all the deformation bones that have respective tweaks
        def_tweaks = [ bone for bone in all_bones['deform']['all'] if bone[4:] in all_bones['tweaks']['all'] ]

        # Parent all org bones to the ORG-face
        for bone in [ bone for bone in org_bones if 'optic' not in bone ]:
            eb[ bone ].parent = eb[ org('optic') ]

        for bone in def_tweaks:
            # the def and the matching org bone are parented to their corresponding tweak,
            # whose name is the same as that of the def bone, without the "DEF-" (first 4 chars)
            eb[ bone ].parent            = eb[ bone[4:] ]
            eb[ org( bone[4:] ) ].parent = eb[ bone[4:] ]

        # Parent ORG eyes to corresponding mch bones
        for bone in [ bone for bone in org_bones if 'eye' in bone ]:
            eb[ bone ].parent = eb[ make_mechanism_name( strip_org( bone ) ) ]

        # Parent eyelid deform bones (each lid def bone is parented to its respective MCH bone)
        def_lids = [ bone for bone in all_bones['deform']['all'] if 'lid' in bone ]

        for bone in def_lids:
            mch = make_mechanism_name( bone[4:] )
            eb[ bone ].parent = eb[ mch ]

        ## Parenting all mch bones

        eb[ 'MCH-eyes_parent' ].parent = None  # eyes_parent will be parented to root

        ## Parenting the control bones

        # eyes
        eb[ 'eyes' ].parent = eb[ 'MCH-eyes_parent' ]

        eyes = [
            bone for bone in all_bones['ctrls']['eyes'] if 'eyes' not in bone
        ][0:2]

        for eye in eyes:
            eb[ eye ].parent = eb[ 'eyes' ]

        ## turbo: parent eye master bones to face
        for eye_master in eyes[2:]:
            eb[ eye_master ].parent = eb[ 'ORG-optic' ]

        # Parent eyes mch and lid tweaks and mch bones to masters
        tweaks = [
            b for b in all_bones['tweaks']['all'] if 'lid' in b
        ]
        mch = all_bones['mch']['lids']  + \
              all_bones['mch']['eye.R'] + \
              all_bones['mch']['eye.L']

        everyone = tweaks + mch

        left, right = self.symmetrical_split( everyone )

        for l in left:
            eb[ l ].parent = eb[ 'master_eye.L' ]

        for r in right:
            eb[ r ].parent = eb[ 'master_eye.R' ]

    def make_constraits(self, constraint_type, bone, subtarget, influence = 1):
        org_bones = self.org_bones
        bpy.ops.object.mode_set(mode ='OBJECT')
        pb = self.obj.pose.bones

        owner_pb = pb[bone]

        if   constraint_type == 'def_tweak':

            const = owner_pb.constraints.new( 'DAMPED_TRACK' )
            const.target    = self.obj
            const.subtarget = subtarget

            const = owner_pb.constraints.new( 'STRETCH_TO' )
            const.target    = self.obj
            const.subtarget = subtarget

        elif constraint_type == 'def_lids':

            const = owner_pb.constraints.new( 'DAMPED_TRACK' )
            const.target    = self.obj
            const.subtarget = subtarget
            const.head_tail = 1.0

            const = owner_pb.constraints.new( 'STRETCH_TO' )
            const.target    = self.obj
            const.subtarget = subtarget
            const.head_tail = 1.0

        elif constraint_type == 'mch_eyes':

            const = owner_pb.constraints.new( 'DAMPED_TRACK' )
            const.target    = self.obj
            const.subtarget = subtarget

        elif constraint_type == 'mch_eyes_lids_follow':

            const = owner_pb.constraints.new( 'COPY_LOCATION' )
            const.target    = self.obj
            const.subtarget = subtarget
            const.head_tail = 1.0

        elif constraint_type == 'mch_eyes_parent':

            const = owner_pb.constraints.new( 'COPY_TRANSFORMS' )
            const.target    = self.obj
            const.subtarget = subtarget

        elif constraint_type == 'mch_jaw_master':

            const = owner_pb.constraints.new( 'COPY_TRANSFORMS' )
            const.target    = self.obj
            const.subtarget = subtarget
            const.influence = influence

        elif constraint_type == 'teeth':

            const = owner_pb.constraints.new( 'COPY_TRANSFORMS' )
            const.target    = self.obj
            const.subtarget = subtarget
            const.influence = influence

        elif constraint_type == 'tweak_copyloc':

            const = owner_pb.constraints.new( 'COPY_LOCATION' )
            const.target       = self.obj
            const.subtarget    = subtarget
            const.influence    = influence
            const.use_offset   = True
            const.target_space = 'LOCAL'
            const.owner_space  = 'LOCAL'

        elif constraint_type == 'tweak_copy_rot_scl':

            const = owner_pb.constraints.new( 'COPY_ROTATION' )
            const.target       = self.obj
            const.subtarget    = subtarget
            const.mix_mode     = 'OFFSET'
            const.target_space = 'LOCAL'
            const.owner_space  = 'LOCAL'

            const = owner_pb.constraints.new( 'COPY_SCALE' )
            const.target       = self.obj
            const.subtarget    = subtarget
            const.use_offset   = True
            const.target_space = 'LOCAL'
            const.owner_space  = 'LOCAL'

        elif constraint_type == 'tweak_copyloc_inv':

            const = owner_pb.constraints.new( 'COPY_LOCATION' )
            const.target       = self.obj
            const.subtarget    = subtarget
            const.influence    = influence
            const.target_space = 'LOCAL'
            const.owner_space  = 'LOCAL'
            const.use_offset   = True
            const.invert_x     = True
            const.invert_y     = True
            const.invert_z     = True

        elif constraint_type == 'mch_tongue_copy_trans':

            const = owner_pb.constraints.new( 'COPY_TRANSFORMS' )
            const.target    = self.obj
            const.subtarget = subtarget
            const.influence = influence

    def constraints( self, all_bones ):
        ## Def bone constraints

        pattern = r'^DEF-(\w+\.?\w?\.?\w?)(\.?)(\d*?)(\d?)$'

        for bone in [ bone for bone in all_bones['deform']['all'] if 'lid' not in bone ]:
            print("do not delete constraints")
            matches = re.match( pattern, bone ).groups()
            if len( matches ) > 1 and matches[-1]:
                num = int( matches[-1] ) + 1
                str_list = list( matches )[:-1] + [ str( num ) ]
                tweak = "".join( str_list )
            else:
                tweak = "".join( matches ) + ".001"
            self.make_constraits('def_tweak', bone, tweak )

        def_lids = sorted( [ bone for bone in all_bones['deform']['all'] if 'lid' in bone ] )
        mch_lids = sorted( [ bone for bone in all_bones['mch']['lids'] ] )

        def_lidsL, def_lidsR = self.symmetrical_split( def_lids )
        mch_lidsL, mch_lidsR = self.symmetrical_split( mch_lids )

        # Take the last mch_lid bone and place it at the end
        mch_lidsL = mch_lidsL[1:] + [ mch_lidsL[0] ]
        mch_lidsR = mch_lidsR[1:] + [ mch_lidsR[0] ]

        for boneL, boneR, mchL, mchR in zip( def_lidsL, def_lidsR, mch_lidsL, mch_lidsR ):
            self.make_constraits('def_lids', boneL, mchL )
            self.make_constraits('def_lids', boneR, mchR )

        ## MCH constraints

        # mch lids constraints
        for bone in all_bones['mch']['lids']:
            tweak = bone[4:]  # remove "MCH-" from bone name
            self.make_constraits('mch_eyes', bone, tweak )

        # mch eyes constraints
        for bone in [ 'MCH-eye.L', 'MCH-eye.R' ]:
            ctrl = bone[4:]  # remove "MCH-" from bone name
            self.make_constraits('mch_eyes', bone, ctrl )

        for bone in [ 'MCH-eye.L.001', 'MCH-eye.R.001' ]:
            target = bone[:-4] # remove number from the end of the name
            self.make_constraits('mch_eyes_lids_follow', bone, target )

        # mch eyes parent constraints
        self.make_constraits('mch_eyes_parent', 'MCH-eyes_parent', 'ORG-optic' )

        ## Tweak bones constraints

        # copy location constraints for tweak bones of both sides
        tweak_copyloc_L = {
            'lid.T.L.001'   : [ [ 'lid.T.L.002'                    ], [ 0.6       ] ],
            'lid.T.L.003'   : [ [ 'lid.T.L.002',                   ], [ 0.6       ] ],
            'lid.T.L.002'   : [ [ 'MCH-eye.L.001',                 ], [ 0.5       ] ],
            'lid.B.L.001'   : [ [ 'lid.B.L.002',                   ], [ 0.6       ] ],
            'lid.B.L.003'   : [ [ 'lid.B.L.002',                   ], [ 0.6       ] ],
            'lid.B.L.002'   : [ [ 'MCH-eye.L.001',                 ], [ 0.5, 0.1  ] ],
            }

        for owner in list( tweak_copyloc_L.keys() ):

            targets, influences = tweak_copyloc_L[owner]
            for target, influence in zip( targets, influences ):

                # Left side constraints
                self.make_constraits( 'tweak_copyloc', owner, target, influence )

                # create constraints for the right side too
                ownerR  = owner.replace(  '.L', '.R' )
                targetR = target.replace( '.L', '.R' )
                self.make_constraits( 'tweak_copyloc', ownerR, targetR, influence )

    def drivers_and_props( self, all_bones ):

        bpy.ops.object.mode_set(mode ='OBJECT')
        pb = self.obj.pose.bones

        eyes_ctrl = all_bones['ctrls']['eyes'][2]
        eyes_prop = 'eyes_follow'
        defval = 1.0

        make_property(pb[ eyes_ctrl ], eyes_prop, defval)

        # Eyes driver
        mch_eyes_parent = all_bones['mch']['eyes_parent'][0]

        drv = pb[ mch_eyes_parent ].constraints[0].driver_add("influence").driver
        drv.type='SUM'

        var = drv.variables.new()
        var.name = eyes_prop
        var.type = "SINGLE_PROP"
        var.targets[0].id = self.obj
        var.targets[0].data_path = pb[ eyes_ctrl ].path_from_id() + '['+ '"' + eyes_prop + '"' + ']'

        return eyes_prop

    def create_bones(self):
        org_bones = self.org_bones
        bpy.ops.object.mode_set(mode ='EDIT')
        eb = self.obj.data.edit_bones

        # Clear parents for org bones
        for bone in [ bone for bone in org_bones if 'optic' not in bone ]:
            eb[bone].use_connect = False
            eb[bone].parent      = None

        all_bones = {}

        def_names           = self.create_deformation()
        ctrls = self.all_controls()
        mchs                = self.create_mch()

        return {
            'deform' : def_names,
            'ctrls'  : ctrls['ctrls'],
            'tweaks' : ctrls['tweaks'],
            'mch'    : mchs
            }

    def generate(self):

        self.orient_org_bones()
        all_bones = self.create_bones()
        self.parent_bones(all_bones)
        self.constraints(all_bones)
        eyes_prop = self.drivers_and_props(all_bones)


        # Create UI
        all_controls = []
        all_controls += [ bone for bone in [ bgroup for bgroup in [ all_bones['ctrls'][group] for group in list( all_bones['ctrls'].keys() ) ] ] ]
        all_controls += [ bone for bone in [ bgroup for bgroup in [ all_bones['tweaks'][group] for group in list( all_bones['tweaks'].keys() ) ] ] ]

        all_ctrls = []
        for group in all_controls:
            for bone in group:
                all_ctrls.append( bone )

        controls_string = ", ".join(["'" + x + "'" for x in all_ctrls])
        return [ script % (
            controls_string,
            all_bones['ctrls']['eyes'][2],
            eyes_prop )
            ]


def add_parameters(params):
    """ Add the parameters of this rig type to the
        RigifyParameters PropertyGroup
    """

    # Setting up extra layers for the tweak bones
    params.primary_layers_extra = bpy.props.BoolProperty(
        name="primary_layers_extra",
        default=True,
        description=""
        )
    params.primary_layers = bpy.props.BoolVectorProperty(
        size=32,
        description="Layers for the primary controls to be on",
        default=tuple([i == 1 for i in range(0, 32)])
        )
    params.secondary_layers_extra = bpy.props.BoolProperty(
        name="secondary_layers_extra",
        default=True,
        description=""
        )
    params.secondary_layers = bpy.props.BoolVectorProperty(
        size=32,
        description="Layers for the secondary controls to be on",
        default=tuple([i == 1 for i in range(0, 32)])
        )


def parameters_ui(layout, params):
    """ Create the ui for the rig parameters."""
    layers = ["primary_layers", "secondary_layers"]

    bone_layers = bpy.context.active_pose_bone.bone.layers[:]

    for layer in layers:
        r = layout.row()
        r.prop( params, layer + "_extra" )
        r.active = getattr( params, layer + "_extra" )

        col = r.column(align=True)
        row = col.row(align=True)
        for i in range(8):
            icon = "NONE"
            if bone_layers[i]:
                icon = "LAYER_ACTIVE"
            row.prop(params, layer, index=i, toggle=True, text="", icon=icon)

        row = col.row(align=True)
        for i in range(16, 24):
            icon = "NONE"
            if bone_layers[i]:
                icon = "LAYER_ACTIVE"
            row.prop(params, layer, index=i, toggle=True, text="", icon=icon)

        col = r.column(align=True)
        row = col.row(align=True)

        for i in range(8, 16):
            icon = "NONE"
            if bone_layers[i]:
                icon = "LAYER_ACTIVE"
            row.prop(params, layer, index=i, toggle=True, text="", icon=icon)

        row = col.row(align=True)
        for i in range(24, 32):
            icon = "NONE"
            if bone_layers[i]:
                icon = "LAYER_ACTIVE"
            row.prop(params, layer, index=i, toggle=True, text="", icon=icon)


def create_sample(obj):
    # generated by rigify.utils.write_metarig
    bpy.ops.object.mode_set(mode='EDIT')
    arm = obj.data

    bones = {}

    bone = arm.edit_bones.new('optic')
    bone.head = 0.0000, -0.1209, 1.8941
    bone.tail = 0.0000, -0.1209, 1.9139
    bone.roll = 0.0000
    bone.use_connect = False
    bones['optic'] = bone.name
    bone = arm.edit_bones.new('lid.T.L')
    bone.head = 0.0768, -0.1218, 1.8947
    bone.tail = 0.0678, -0.1356, 1.8995
    bone.roll = -0.2079
    bone.use_connect = False
    bone.parent = arm.edit_bones[bones['optic']]
    bones['lid.T.L'] = bone.name
    bone = arm.edit_bones.new('lid.T.R')
    bone.head = -0.0768, -0.1218, 1.8947
    bone.tail = -0.0678, -0.1356, 1.8995
    bone.roll = 0.2079
    bone.use_connect = False
    bone.parent = arm.edit_bones[bones['optic']]
    bones['lid.T.R'] = bone.name
    bone = arm.edit_bones.new('eye.L')
    bone.head = 0.0516, -0.1209, 1.8941
    bone.tail = 0.0516, -0.1451, 1.8941
    bone.roll = 0.0000
    bone.use_connect = False
    bone.parent = arm.edit_bones[bones['optic']]
    bones['eye.L'] = bone.name
    bone = arm.edit_bones.new('eye.R')
    bone.head = -0.0516, -0.1209, 1.8941
    bone.tail = -0.0516, -0.1451, 1.8941
    bone.roll = 0.0000
    bone.use_connect = False
    bone.parent = arm.edit_bones[bones['optic']]
    bones['eye.R'] = bone.name
    bone = arm.edit_bones.new('lid.T.L.001')
    bone.head = 0.0678, -0.1356, 1.8995
    bone.tail = 0.0550, -0.1436, 1.9022
    bone.roll = 0.1837
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['lid.T.L']]
    bones['lid.T.L.001'] = bone.name
    bone = arm.edit_bones.new('lid.T.R.001')
    bone.head = -0.0678, -0.1356, 1.8995
    bone.tail = -0.0550, -0.1436, 1.9022
    bone.roll = -0.1837
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['lid.T.R']]
    bones['lid.T.R.001'] = bone.name
    bone = arm.edit_bones.new('lid.T.L.002')
    bone.head = 0.0550, -0.1436, 1.9022
    bone.tail = 0.0425, -0.1427, 1.8987
    bone.roll = -0.0940
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['lid.T.L.001']]
    bones['lid.T.L.002'] = bone.name
    bone = arm.edit_bones.new('lid.T.R.002')
    bone.head = -0.0550, -0.1436, 1.9022
    bone.tail = -0.0425, -0.1427, 1.8987
    bone.roll = 0.0940
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['lid.T.R.001']]
    bones['lid.T.R.002'] = bone.name
    bone = arm.edit_bones.new('lid.T.L.003')
    bone.head = 0.0425, -0.1427, 1.8987
    bone.tail = 0.0262, -0.1418, 1.8891
    bone.roll = 0.2194
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['lid.T.L.002']]
    bones['lid.T.L.003'] = bone.name
    bone = arm.edit_bones.new('lid.T.R.003')
    bone.head = -0.0425, -0.1427, 1.8987
    bone.tail = -0.0262, -0.1418, 1.8891
    bone.roll = -0.2194
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['lid.T.R.002']]
    bones['lid.T.R.003'] = bone.name
    bone = arm.edit_bones.new('lid.B.L')
    bone.head = 0.0262, -0.1418, 1.8891
    bone.tail = 0.0393, -0.1425, 1.8854
    bone.roll = 0.0756
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['lid.T.L.003']]
    bones['lid.B.L'] = bone.name
    bone = arm.edit_bones.new('lid.B.R')
    bone.head = -0.0262, -0.1418, 1.8891
    bone.tail = -0.0393, -0.1425, 1.8854
    bone.roll = -0.0756
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['lid.T.R.003']]
    bones['lid.B.R'] = bone.name
    bone = arm.edit_bones.new('lid.B.L.001')
    bone.head = 0.0393, -0.1425, 1.8854
    bone.tail = 0.0553, -0.1418, 1.8833
    bone.roll = 0.1015
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['lid.B.L']]
    bones['lid.B.L.001'] = bone.name
    bone = arm.edit_bones.new('lid.B.R.001')
    bone.head = -0.0393, -0.1425, 1.8854
    bone.tail = -0.0553, -0.1418, 1.8833
    bone.roll = -0.1015
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['lid.B.R']]
    bones['lid.B.R.001'] = bone.name
    bone = arm.edit_bones.new('lid.B.L.002')
    bone.head = 0.0553, -0.1418, 1.8833
    bone.tail = 0.0694, -0.1351, 1.8889
    bone.roll = -0.0748
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['lid.B.L.001']]
    bones['lid.B.L.002'] = bone.name
    bone = arm.edit_bones.new('lid.B.R.002')
    bone.head = -0.0553, -0.1418, 1.8833
    bone.tail = -0.0694, -0.1351, 1.8889
    bone.roll = 0.0748
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['lid.B.R.001']]
    bones['lid.B.R.002'] = bone.name
    bone = arm.edit_bones.new('lid.B.L.003')
    bone.head = 0.0694, -0.1351, 1.8889
    bone.tail = 0.0768, -0.1218, 1.8947
    bone.roll = -0.0085
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['lid.B.L.002']]
    bones['lid.B.L.003'] = bone.name
    bone = arm.edit_bones.new('lid.B.R.003')
    bone.head = -0.0694, -0.1351, 1.8889
    bone.tail = -0.0768, -0.1218, 1.8947
    bone.roll = 0.0085
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['lid.B.R.002']]
    bones['lid.B.R.003'] = bone.name

    bpy.ops.object.mode_set(mode='OBJECT')
    pbone = obj.pose.bones[bones['optic']]
    pbone.rigify_type = 'faces.eyes'
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    try:
        pbone.rigify_parameters.primary_layers = [False, True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False]
    except AttributeError:
        pass
    try:
        pbone.rigify_parameters.secondary_layers = [False, False, True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False]
    except AttributeError:
        pass
    pbone = obj.pose.bones[bones['lid.T.L']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['lid.T.R']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['eye.L']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['eye.R']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['lid.T.L.001']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['lid.T.R.001']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['lid.T.L.002']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['lid.T.R.002']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['lid.T.L.003']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['lid.T.R.003']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['lid.B.L']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['lid.B.R']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['lid.B.L.001']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['lid.B.R.001']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['lid.B.L.002']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['lid.B.R.002']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['lid.B.L.003']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['lid.B.R.003']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'

    bpy.ops.object.mode_set(mode='EDIT')
    for bone in arm.edit_bones:
        bone.select = False
        bone.select_head = False
        bone.select_tail = False
    for b in bones:
        bone = arm.edit_bones[bones[b]]
        bone.select = True
        bone.select_head = True
        bone.select_tail = True
        bone.bbone_x = bone.bbone_z = bone.length * 0.05
        arm.edit_bones.active = bone

    return bones
