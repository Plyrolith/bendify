from bpy.props import *

from itertools import count

from rigify.base_rig import stage
from rigify.utils.bones import align_bone_orientation, align_bone_x_axis, copy_bone_position, put_bone, set_bone_widget_transform
from rigify.utils.errors import MetarigError
from rigify.utils.layers import ControlLayersOption
from rigify.utils.misc import map_list
from rigify.utils.naming import make_derived_name, strip_org
from rigify.utils.widgets_basic import create_bone_widget
from rigify.utils.widgets_special import create_neck_bend_widget

from ...bendy_rigs import HandleBendyRig, ParentedBendyRig, VolumeBendyRig, AlignedBendyRig, AttachedBendyRig, ConnectingBendyRig, ScaleOffsetMixin
from ...props import ArmaConstraintTargets

from ...utils.bones import align_bone_to_bone_axis, connect_bone_to_bone, put_bone_to_bone
from ...utils.misc import threewise_nozip
from ...utils.widgets_bendy import create_simple_arrow_widget


class StretchBendyRig(HandleBendyRig):
    """
    Base stretchy rig
    """

    def initialize(self):
        super().initialize()
        self.volume_stretch_default = self.params.volume_stretch_default
        self.volume_stretch_panel = self.params.volume_stretch_panel

    ####################################################
    # Master control

    @stage.configure_bones
    def configure_volume_stretch_properties(self):
        if self.default_prop_bone:
            self.configure_volume_prop(
                self.default_prop_bone,
                self.volume_stretch_default,
                "volume_stretch",
                self.volume_stretch_panel,
                strip_org(self.base_bone) + " Stretch Volume Variation"
            )

    ##############################
    # Stretch control

    @stage.generate_bones
    def make_control_chain(self):
        orgs = self.bones.org
        start = self.make_control_bone(orgs[0], "_in")
        self.bones.ctrl.stretch_in = start
        self.default_prop_bone = start
        end = self.make_control_bone(orgs[-1], "_out", True)
        self.bones.ctrl.stretch_out = end
        self.bones.ctrl.stretch = [start, end]
        
    def make_control_bone(self, org, suffix="_in", tail=False):
        orgs = self.bones.org
        name = make_derived_name(orgs[0], 'ctrl', suffix)
        name = self.copy_bone(org, name, parent=False)
        if tail:
            put_bone(self.obj, name, self.get_bone(org).tail)
        return name
        
    @stage.parent_bones
    def parent_control_chain(self):
        for ctrl in self.bones.ctrl.stretch:
            self.set_bone_parent(ctrl, self.root_bone, inherit_scale='FIX_SHEAR')

    @stage.configure_bones
    def configure_control_chain(self):
        ctrls = self.bones.ctrl
        for ctrl in [ctrls.stretch_in, ctrls.stretch_out]:
            self.configure_control_bone(ctrl)

    def configure_control_bone(self, bone):
        cb = self.get_bone(bone)
        cb.lock_rotation = (True, False, True)
        cb.lock_scale = [True] * 3

    @stage.generate_widgets
    def make_control_widgets(self):
        for ctrl in self.bones.ctrl.stretch:
            self.make_control_widget(ctrl)
    
    def make_control_widget(self, ctrl):
        create_bone_widget(self.obj, ctrl, r1=0.5, l1=-0.25, r2=0.5, l2=0.25)

    ####################################################
    # Tweak MCH

    @stage.rig_bones
    def rig_tweak_mch_chain(self):
        orgs = self.bones.org
        if self.tweak_mch:
            for mch, org in zip(self.bones.mch.tweak, orgs + [orgs[-1]]):
                self.make_armature_constraint(mch, org)
                self.make_constraint(mch, 'COPY_SCALE', self.root_bone)

    ####################################################
    # Tweak chain

    @stage.generate_bones
    def make_tweak_chain(self):
        '''Removed first tweak as default prop bone'''
        orgs = self.bones.org
        self.bones.ctrl.tweak = map_list(self.make_tweak_bone, count(0), orgs + orgs[-1:])


    @stage.parent_bones
    def parent_tweak_chain(self):
        tweaks = self.bones.ctrl.tweak
        parents = self.bones.mch.tweak if self.tweak_mch else len(tweaks) * [self.bones.mch.stretch[0]]
        for args in zip(tweaks, parents):
            self.parent_tweak_bone(*args)

    @stage.configure_bones
    def configure_tweak_chain(self):
        super().configure_tweak_chain()
        ControlLayersOption.TWEAK.assign(self.params, self.obj, self.bones.ctrl.tweak)

    ####################################################
    # Stretch MCH

    @stage.generate_bones
    def make_stretch_mch_chain(self):
        orgs = self.bones.org
        stretch = make_derived_name(orgs[0], 'mch', "_stretch")
        self.bones.mch.stretch = [self.copy_bone(orgs[0], stretch, parent=False)]
        self.get_bone(stretch).tail = self.get_bone(orgs[-1]).tail
        align_bone_x_axis(self.obj, stretch, self.get_bone(orgs[0]).x_axis)
    
    @stage.parent_bones
    def parent_stretch_mch_chain(self):
        for stretch in self.bones.mch.stretch:
            self.set_bone_parent(stretch, self.root_bone)

    @stage.rig_bones
    def rig_stretch_mch_chain(self):
        ctrls = self.bones.ctrl.stretch
        for args in zip(self.bones.mch.stretch, ctrls, ctrls[1:]):
            self.rig_stretch_mch_bone(*args)

    def rig_stretch_mch_bone(self, bone, start, end):
        self.make_constraint(bone, 'COPY_LOCATION', start)
        self.make_constraint(bone, 'COPY_ROTATION', start, use_x=False, use_z=False, space='LOCAL', mix_mode = 'BEFORE')
        self.make_constraint(bone, 'COPY_ROTATION', end, use_x=False, use_z=False, space='LOCAL', mix_mode='BEFORE')
        stretch = self.make_constraint(bone, 'STRETCH_TO', end, keep_axis=self.keep_axis)
        self.make_driver(stretch, 'bulge', variables=[(self.default_prop_bone, 'volume_stretch')])

    ####################################################
    # ORG MCH chain

    @stage.generate_bones
    def make_org_mch_chain(self):
        orgs = self.bones.org
        self.bones.mch.org = map_list(self.make_org_mch_bone, count(0), orgs + orgs[-1:])

    def make_org_mch_bone(self, i, org):
        name = make_derived_name(org, 'mch', '_org')
        name = self.copy_bone(org, name, parent=False)

        if i == len(self.bones.org):
            put_bone(self.obj, name, self.get_bone(org).tail)
        
        return name

    @stage.parent_bones
    def parent_org_mch_chain(self):
        for mch in self.bones.mch.org:
            self.set_bone_parent(mch, self.root_bone_mch)

    @stage.rig_bones
    def rig_org_mch_chain(self):
        for mch in self.bones.mch.org:
            self.rig_org_mch_bone(mch, self.bones.mch.stretch[0])
    
    def rig_org_mch_bone(self, mch, target):
        self.make_armature_constraint(mch, target)
        #self.make_constraint(mch, 'COPY_SCALE', self.parent_org)

    ##############################
    # ORG chain

    @stage.apply_bones
    def bbone_org_chain(self):
        orgs = self.bones.org
        mchs = self.bones.mch.org
        self.ease_org_chain(orgs)
        self.bbone_chain(
            orgs,
            mchs[0] if self.bbone_handles == 'TANGENT' else None,
            mchs[-1] if self.bbone_handles == 'TANGENT' else None
        )

    @stage.rig_bones
    def rig_org_chain(self):
        mchs = self.bones.mch.org
        for org, mch, next_mch in zip(self.bones.org, mchs, mchs[1:]):
            self.rig_org_bone(org, mch, next_mch, self.root_bone)

    ####################################################
    # UI

    @classmethod
    def volume_ui(self, layout, params):
        r = layout.row(align=True)
        r.prop(params, 'volume_stretch_default', slider=True)
        r.prop(params, 'volume_stretch_panel', text="", icon='OPTIONS')

    ####################################################
    # SETTINGS

    @classmethod
    def add_parameters(self, params):
        '''Added more parameters'''

        super().add_parameters(params)

        params.volume_stretch_default = FloatProperty(
            name="Stretch Volume Variation Default",
            default=1.0,
            soft_min=0.0,
            soft_max=1.0,
            description="Default value for stretch volume variation",
        )

        params.volume_stretch_panel = BoolProperty(
            name="Stretch Volume Variation Panel",
            default=False,
            description="Add panel to control volume variation to the UI",
        )

    @classmethod
    def parameters_ui(self, layout, params):
        self.volume_ui(layout, params)
        ControlLayersOption.TWEAK.parameters_ui(layout, params)


### Single Segment simplifications

class SingleSegmentStretchBendyTweakMixin():
    """
    << DEPRECATED >>
    Mix-in for reduced complexity using tweaks
    """

    ##############################
    # Stretch control

    @stage.generate_bones
    def make_control_chain(self):
        if not self.single_segment:
            super().make_control_chain()

    @stage.configure_bones
    def configure_control_chain(self):
        if not self.single_segment:
            super().configure_control_chain()

    @stage.generate_widgets
    def make_control_widgets(self):
        if not self.single_segment:
            super().make_control_widgets()

    ####################################################
    # Tweak chain

    @stage.generate_bones
    def make_tweak_chain(self):
        super().make_tweak_chain()
        if self.single_segment:
            tweaks = self.bones.ctrl.tweak
            self.default_prop_bone = tweaks[0]
            self.bones.ctrl.stretch = [tweaks[0], tweaks[-1]]

    @stage.parent_bones
    def parent_tweak_chain(self):
        if not self.single_segment:
            super().parent_tweak_chain()

    @stage.parent_bones
    def align_tweak_chain(self):
        if not self.single_segment:
            super().align_tweak_chain()


class SingleSegmentStretchBendyControlMixin():
    """
    Mix-in for reduced complexity using in and out controls
    """

    ##############################
    # Stretch control

    @stage.generate_bones
    def make_control_chain(self):
        super().make_control_chain()
        if self.single_segment:
            self.bones.ctrl.tweak = self.bones.ctrl.stretch

    ##############################
    # Stretch control

    @stage.rig_bones
    def configure_control_bone(self, bone):
        if self.single_segment:
            cb = self.get_bone(bone)
            if not self.bbone_scale:
                cb.lock_scale[0] = True
                cb.lock_scale[2] = True
            if not self.bbone_ease:
                cb.lock_scale[1] = True
            if not self.bbone_handles == 'TANGENT':
                cb.lock_rotation[0] = True
                cb.lock_rotation[2] = True
            if self.bbone_handles == 'NONE':
                cb.lock_rotation_w = True
                cb.lock_rotation[1] = True
        else:
            super().configure_control_bone(bone)

    ####################################################
    # Tweak chain

    @stage.generate_bones
    def make_tweak_chain(self):
        if not self.single_segment:
            super().make_tweak_chain()

    @stage.parent_bones
    def parent_tweak_chain(self):
        if not self.single_segment:
            super().parent_tweak_chain()

    @stage.parent_bones
    def align_tweak_chain(self):
        if not self.single_segment:
            super().align_tweak_chain()

    @stage.configure_bones
    def configure_tweak_chain(self):
        if not self.single_segment:
            super().configure_tweak_chain()

    @stage.generate_widgets
    def make_tweak_widgets(self):
        if not self.single_segment:
            super().make_tweak_widgets()


class SingleSegmentStretchBendyRig(SingleSegmentStretchBendyControlMixin, StretchBendyRig):
    """
    Stretchy rig with reduced complexity for single segment; Control OR Tweak Mixin
    """

    def initialize(self):
        super().initialize()

        self.single_segment = True if len(self.bones.org) == 1 else False

    ####################################################
    # Master control

    @stage.configure_bones
    def configure_volume_stretch_properties(self):
        if not self.single_segment:
            super().configure_volume_stretch_properties()

    ####################################################
    # Stretch MCH chain

    def rig_stretch_mch_bone(self, bone, start, end):
        if self.single_segment:
            self.make_constraint(bone, 'COPY_LOCATION', start)
            stretch = self.make_constraint(bone, 'STRETCH_TO', end, keep_axis=self.keep_axis)
            self.make_driver(stretch, 'bulge', variables=[(self.default_prop_bone, 'volume_stretch')])
        else:
            super().rig_stretch_mch_bone(bone, start, end)

    ####################################################
    # Tweak MCH chain

    @stage.generate_bones
    def make_tweak_mch_chain(self):
        if not self.single_segment:
            super().make_tweak_mch_chain()

    @stage.parent_bones
    def parent_tweak_mch_chain(self):
        if not self.single_segment:
            super().parent_tweak_mch_chain()

    @stage.parent_bones
    def align_tweak_mch_chain(self):
        if not self.single_segment:
            super().align_tweak_mch_chain()
    
    @stage.rig_bones
    def rig_tweak_mch_chain(self):
        if not self.single_segment:
            super().rig_tweak_mch_chain()


### Combine from the following

# NEEDS UPDATE
class HarmonicScaleStretchRig(SingleSegmentStretchBendyRig):
    """
    Stretchy rig with scale falloff from main controllers
    """

    def initialize(self):
        super().initialize()
        self.tweak_scale_offset = False if self.single_segment else self.params.tweak_scale_offset

    ##############################
    # Stretch control

    @stage.rig_bones
    def unlock_control_chain_scale_xyz(self):
        if self.tweak_scale_offset:
            ctrls = self.bones.ctrl
            for ctrl in ctrls.stretch:
                ctrl_pb = self.get_bone(ctrl)
                ctrl_pb.lock_scale[0] = False
                ctrl_pb.lock_scale[2] = False
                if len(ctrls.stretch) == len(ctrls.tweak):
                    ctrl_pb.lock_scale[1] = False
    
    ##############################
    # Tweaks

    @stage.rig_bones
    def rig_tweak_chain_scale_offset(self):
        if self.tweak_scale_offset:
            ctrls = self.bones.ctrl
            if len(ctrls.stretch) == len(ctrls.tweak):
                for tweak, stretch in zip(ctrls.tweak, ctrls.stretch):
                    self.make_constraint(tweak, 'COPY_SCALE', stretch, use_offset=True, space='LOCAL')
            else:
                total = len(ctrls.tweak) - 1
                for i, tweak in zip(count(0), ctrls.tweak):
                    if self.attribute_return(['curve_control']):
                        cp = self.curve_position
                        # Zero divide protection
                        div = total - cp - 1
                        third = (i - cp - 1) / div if self.curve_center and div else (i - cp) / (total - cp)
                        first = 1 - (i / cp)
                        second = 1 - first if i <= cp else 1 - third
                    else:
                        second = (i / total)
                        first = 1 - second
                        third = 0
                    for stretch, power in zip(ctrls.stretch, [first, second, third]):
                        if power > 0:
                            self.make_constraint(tweak, 'COPY_SCALE', stretch, use_offset=True, use_y=False, space='LOCAL', power=power)

    ####################################################
    # UI

    @classmethod
    def harmonic_scale_ui(self, layout, params):
        layout.row().prop(params, 'tweak_scale_offset', toggle=True)

    ####################################################
    # SETTINGS

    @classmethod
    def add_parameters(self, params):
        super().add_parameters(params)

        params.tweak_scale_offset = BoolProperty(
            name="Main Controls Scale Tweaks",
            default=True,
            description="Offset tweak X and Z scale by stretch main controls scale",
        )


    @classmethod
    def parameters_ui(self, layout, params):
        self.harmonic_scale_ui(layout, params)
        super().parameters_ui(layout, params)


class StraightStretchBendyRig(SingleSegmentStretchBendyRig):
    """
    Stretchy rig with aligned controls
    """

    def initialize(self):
        super().initialize()

        self.straight = False if self.single_segment else self.params.straight
        self.straight_orientation = self.params.straight_orientation

    ##############################
    # Stretch control

    @stage.parent_bones
    def transform_control_chain(self):
        if self.straight:
            ctrls = self.bones.ctrl
            orgs = self.bones.org
            first_org = self.get_bone(orgs[0])
            last_org = self.get_bone(orgs[-1])
            for ctrl in (ctrls.stretch_in, ctrls.stretch_out):
                bone = self.get_bone(ctrl)
                length = bone.length
                bone.head = first_org.head
                bone.tail = last_org.tail
                bone.length = length
            put_bone(self.obj, ctrls.stretch_out, last_org.tail)
            align_bone_x_axis(self.obj, ctrls.stretch_in, last_org.x_axis if self.straight_orientation == 'LAST' else first_org.x_axis)
            align_bone_x_axis(self.obj, ctrls.stretch_out, first_org.x_axis if self.straight_orientation == 'FIRST' else last_org.x_axis)

    ####################################################
    # UI

    @classmethod
    def straight_ui(self, layout, params):
        col = layout.column()
        if params.straight:
            col = col.box()
        col.row().prop(params, 'straight', toggle=True)
        if params.straight:
            col.row().prop(params, 'straight_orientation', expand=True)
            layout.separator(factor=0.2)

    ####################################################
    # SETTINGS

    @classmethod
    def add_parameters(self, params):
        super().add_parameters(params)

        params.straight = BoolProperty(
            name="Straighten CTRLs",
            default=True,
            description="Align stretch controls to form a straight line by default",
        )

        params.straight_orientation = EnumProperty(
            items=[
                ('FIRST', "Use First", "Use First"),
                ('BOTH', "Individual", "Individual"),
                ('LAST', "Use Last", "Use Last")
            ],
            name="Orientation",
            default='FIRST',
            description="New orientation for stretch controllers",
        )


    @classmethod
    def parameters_ui(self, layout, params):
        self.straight_ui(layout, params)
        super().parameters_ui(layout, params)


class VolumeStretchBendyRig(SingleSegmentStretchBendyRig, VolumeBendyRig):
    """
    Stretchy rig with volume scaling control
    """

    def initialize(self):
        super().initialize()
        VolumeBendyRig.initialize(self)

    @stage.finalize
    def offset_scale_chain(self):
        if self.deform_scale:
            for bone in self.bones.org:
                self.offset_scale_bone(bone)


# NEEDS MERGE
class AlignedStretchBendyRig(SingleSegmentStretchBendyRig, AlignedBendyRig):
    """
    Stretchy rig with start and end Y-alignment
    """

    ####################################################
    # Align

    @stage.apply_bones
    def align_control_ends(self):
        stretchs = self.attribute_return(['bones', 'ctrl', 'stretch'])
        if stretchs:
            if self.align_y_start:
                align_bone_to_bone_axis(
                    self.obj, stretchs[0],
                    self.align_y_start, self.align_y_start_axis, self.align_y_start_preserve
                )
            if self.align_y_end:
                align_bone_to_bone_axis(
                    self.obj, stretchs[-1],
                    self.align_y_end, self.align_y_end_axis, self.align_y_end_preserve
                )


class ConnectingStretchBendyRig(SingleSegmentStretchBendyRig, ConnectingBendyRig):
    """
    Stretchy rig that can connect to a (tweak of its) parent, as well as attach its tip to another bone.
    """
    def initialize(self):
        super().initialize()
        if self.single_segment:
            self.attach_base = None
            self.attach_tip = None
            self.base_type = 'BONE'

    """
    @stage.apply_bones
    def attach_org_mch_bones(self):
        if not self.single_segment:
            mchs = self.bones.mch.org
            
            if self.attach_base:
                if self.attach_base_connect:
                    connect_bone_to_bone(self.obj, mchs[0], self.attach_base)
                
                if self.attach_base_align:
                    align_bone_orientation(self.obj, mchs[0], self.attach_base)

            if self.attach_tip:
                if self.attach_tip_connect:
                    connect_bone_to_bone(self.obj, mchs[-1], self.attach_tip, tail1=True)
                    put_bone_to_bone(self.obj, mchs[-1], self.attach_tip)

                if self.attach_tip_align:
                    align_bone_orientation(self.obj, mchs[-1], self.attach_tip)
    """


### Base for CurvyStretchBendyRig

# MAKE PANEL
class ParentedStretchBendyRig(ParentedBendyRig, SingleSegmentStretchBendyRig):
    """
    Bendy rig with complex parenting
    """

    def initialize(self):
        super().initialize()

        self.use_parents_out = self.params.use_parents_out
        self.parents_out = self.attributes_to_dicts(self.params.parents_out)
        self.parents_out_type_single = self.params.parents_out_type_single

        self.parents_out_copy_rotation = self.params.parents_out_copy_rotation
        self.parents_out_copy_rotation_default = self.params.parents_in_copy_rotation_default
        self.parents_out_copy_rotation_panel = self.params.parents_in_copy_rotation_panel

        self.parents_out_copy_scale = self.params.parents_out_copy_scale
        self.parents_out_copy_scale_default = self.params.parents_in_copy_scale_default
        self.parents_out_copy_scale_panel = self.params.parents_in_copy_scale_panel

    ##############################
    # Stretch control
        
    @stage.parent_bones
    def parent_control_chain(self):
        ctrls = self.bones.ctrl
        mchs = self.bones.mch
        for ctrl, mch in zip(
            [ctrls.stretch_in, ctrls.stretch_out],
            [mchs.inherit_in, mchs.inherit_out]
        ):
            self.set_bone_parent(ctrl, mch, inherit_scale='FIX_SHEAR')

    ####################################################
    # Parent MCH chain

    @stage.generate_bones
    def make_parent_mch_chain(self):
        super().make_parent_mch_chain()
        orgs = self.bones.org
        self.bones.mch.inherit_out = self.make_parent_mch_bone(orgs[-1], "_inherit_out", True)
        if self.use_parents_out:
            self.bones.mch.parent_out = self.make_parent_mch_bone(orgs[-1], "_parent_out", True)
    
    @stage.parent_bones
    def parent_parent_mch_chain(self):
        super().parent_parent_mch_chain()
        mchs = self.bones.mch
        if self.use_parents_out:
            self.set_bone_parent(mchs.inherit_out, mchs.parent_out, inherit_scale='FIX_SHEAR')
            self.set_bone_parent(mchs.parent_out, self.root_bone_mch)
        else:
            self.set_bone_parent(mchs.inherit_out, mchs.inherit_in, inherit_scale='FIX_SHEAR')
        if self.parents_out_copy_rotation:
            align_bone_orientation(self.obj, mchs.inherit_out, self.parents_out_copy_rotation)
            
    @stage.rig_bones
    def rig_parent_mch_chain(self):
        super().rig_parent_mch_chain()
        mchs = self.bones.mch
        if self.use_parents_out:
            self.rig_parent_mch_bone(
                mchs.parent_out,
                self.parents_out,
                self.parents_out_type_single
            )
        self.rig_inherit_mch_bone(
            mchs.inherit_out,
            self.bones.ctrl.stretch_out,
            self.parents_out_copy_rotation,
            self.parents_out_copy_rotation_default,
            self.parents_out_copy_rotation_panel,
            self.parents_out_copy_scale,
            self.parents_out_copy_scale_default,
            self.parents_out_copy_scale_panel
        )
    
    ####################################################
    # UI

    @classmethod
    def parents_ui(self, layout, params):
        box = layout.box()
        self.parents_component_ui(box, params, 'parents_in', "Base", icon='CURSOR')
        layout.separator()
        box = layout.box()
        self.parents_component_ui(box, params, 'parents_out', "Tip", icon='TRACKING', use=True)

    ####################################################
    # SETTINGS

    @classmethod
    def add_parameters(self, params):
        super().add_parameters(params)
        params.parents_curve = CollectionProperty(type=ArmaConstraintTargets, name="Curve Parents")
        params.parents_out = CollectionProperty(type=ArmaConstraintTargets, name="Tip Parents")

        params.use_parents_out = BoolProperty(
            name="Complex Tip Parenting",
            default=False,
            description="Use complex parenting for the stretch tip control",
        )

        params.parents_out_type_single = EnumProperty(
            name="Parenting Type",
            items=[
                ('CHILD_OF', "Chilf Of", "Chilf Of"),
                ('ARMATURE', "Armature", "Armature")
            ],
            default='CHILD_OF',
            description="Constraint type for single parenting. Use Armature to follow B-Bones.",
        )

        params.parents_out_panel = EnumProperty(
            name="Parenting Panel",
            items=[
                ('NONE', "No UI", "No UI"),
                ('SWITCH', "Switch", "Switch"),
                ('SLIDER', "Slider", "Slider"),
                ('INDIVIDUAL', "Individual", "Individual")
            ],
            default='NONE',
            description="Property and panel variation to be used for dynamic parenting",
        )

        params.parents_out_copy_rotation = StringProperty(
            name="World Rotation",
            default="",
            description="Copy world rotation from this bone",
        )

        params.parents_out_copy_rotation_default = FloatProperty(
            name="Default",
            default=1.0,
            min=0.0,
            max=1.0,
            description="Default value for world rotation",
        )

        params.parents_out_copy_rotation_panel = BoolProperty(
            name="World Rotation Panel",
            default=False,
            description="Add a panel for world rotation to the UI",
        )

        params.parents_out_copy_scale = StringProperty(
            name="World Scale",
            default="",
            description="Copy world scale from this bone",
        )

        params.parents_out_copy_scale_default = FloatProperty(
            name="Default",
            default=1.0,
            min=0.0,
            max=1.0,
            description="Default value for world scale",
        )

        params.parents_out_copy_scale_panel = BoolProperty(
            name="Copy Scale Panel",
            default=False,
            description="Add a panel for world scale to the UI",
        )


class EasingStretchBendyRig(SingleSegmentStretchBendyRig):
    """
    Bendy stretchy rig
    """
    def initialize(self):
        super().initialize()

        self.bend = False if self.single_segment else self.params.bend
        self.bend_easein = self.params.bend_easein
        self.bend_easeout = self.params.bend_easeout

        if not self.tweak_mch:
            self.tweak_mch = self.bend

    ##############################
    # Stretch control

    def configure_control_bone(self, bone):
        if self.bend:
            cb = self.get_bone(bone)
            cb.lock_rotation_w = False
            cb.lock_rotation = [False] * 3
            if len(self.bones.org) >= len(self.bones.ctrl.stretch):
                cb.lock_scale[1] = False
        else:
            super().configure_control_bone(bone)
    
    ####################################################
    # Stretch MCH chain

    @stage.parent_bones
    def ease_stretch_mch_chain(self):
        if self.bend:
            ctrls = self.bones.ctrl.stretch
            segments = min(len(self.bones.org) * 3, 32)
            for mch, handle_start, handle_end in zip(self.bones.mch.stretch, ctrls, ctrls[1:]):
                self.bbone_setup(mch, segments, self.bend_easein, self.bend_easeout, handle_start, handle_end)

    @stage.rig_bones
    def drivers_stretch_mch_chain(self):
        if self.bend and len(self.bones.org) >= len(self.bones.ctrl.stretch):
            ctrls = self.bones.ctrl.stretch
            for mch, handle_in, handle_out in zip(self.bones.mch.stretch, ctrls, ctrls[1:]):
                self.driver_bbone_ease(mch, [handle_in], [handle_out])

    def rig_stretch_mch_bone(self, bone, start, end):
        if self.bend:
            self.make_constraint(bone, 'COPY_LOCATION', start)
            stretch = self.make_constraint(bone, 'STRETCH_TO', end, keep_axis=self.keep_axis)
            self.make_driver(stretch, 'bulge', variables=[(self.default_prop_bone, 'volume_stretch')])
        else:
            super().rig_stretch_mch_bone(bone, start, end)

    ####################################################
    # UI

    @classmethod
    def bend_ui(self, layout, params):
        col = layout.column()
        if params.bend:
            col = col.box()
        col.row().prop(params, 'bend', toggle=True)
        if params.bend:
            r = col.row(align=True)
            r.prop(params, 'bend_easein', slider=True)
            r.prop(params, 'bend_easeout', slider=True)
            layout.separator(factor=0.2)

    ####################################################
    # SETTINGS

    @classmethod
    def add_parameters(self, params):
        super().add_parameters(params)

        params.bend = BoolProperty(
            name="Bend Between CTRLs",
            default=True,
            description="Use a bendy control curve between start and end handles",
        )

        params.bend_easein = FloatProperty(
            name="Ease In",
            default=1.0,
            soft_min=0.0,
            soft_max=2.0,
            description="Easing in for the control curve",
        )

        params.bend_easeout = FloatProperty(
            name="Ease Out",
            default=1.0,
            soft_min=0.0,
            soft_max=2.0,
            description="Easing out for the control curve",
        )

    @classmethod
    def parameters_ui(self, layout, params):
        self.bend_ui(layout, params)
        super().parameters_ui(layout, params)


### Don't use the two above if using this

class CurvyStretchBendyRig(EasingStretchBendyRig, ParentedStretchBendyRig, ScaleOffsetMixin):
    """
    Stretchy rig with curve control
    """

    def initialize(self):
        super().initialize()

        self.curve_control = self.params.curve_control if self.bend else False
        self.curve_position = self.params.curve_position
        self.curve_center = self.params.curve_center
        self.curve_align = self.params.curve_align
        self.curve_control_easein = self.params.curve_control_easein
        self.curve_control_easeout = self.params.curve_control_easeout

        self.curve_location = self.params.curve_location
        if not self.single_segment and self.curve_control and not (self.curve_position < len(self.bones.org)):
            raise MetarigError("Bone {}: Please specify a valid curve control position.".format(self.bones.org[0]))

        self.use_parents_curve = self.params.use_parents_curve
        self.parents_curve = self.attributes_to_dicts(self.params.parents_curve)
        self.parents_curve_type_single = self.params.parents_curve_type_single

        self.parents_curve_copy_rotation = self.params.parents_curve_copy_rotation
        self.parents_curve_copy_rotation_default = self.params.parents_in_copy_rotation_default
        self.parents_curve_copy_rotation_panel = self.params.parents_in_copy_rotation_panel

        self.parents_curve_copy_scale = self.params.parents_curve_copy_scale
        self.parents_curve_copy_scale_default = self.params.parents_in_copy_scale_default
        self.parents_curve_copy_scale_panel = self.params.parents_in_copy_scale_panel

    ####################################################
    # Utilities

    def place_chain(self, bone, handle_in, handle_out):
        bone_e = self.get_bone(bone)
        in_e = self.get_bone(handle_in)
        out_e = self.get_bone(handle_out)
        
        bone_e.head = in_e.head
        bone_e.tail = out_e.head
        align_bone_x_axis(self.obj, bone, in_e.x_axis)

    def position_curve(self, curve):
        if self.curve_center:
            pos = self.bones.org[self.curve_position]
            pos_b = self.get_bone(pos)
            pos_v = pos_b.head + (pos_b.tail - pos_b.head) / 2
            put_bone(self.obj, curve, pos=pos_v)
        if self.curve_location and self.curve_location:
            copy_bone_position(self.obj, self.curve_location, curve)
        if self.curve_align:
            ctrls = self.bones.ctrl
            roll = curve
            if self.attribute_return(['straight']):
                if self.straight_orientation == 'FIRST':
                    roll = ctrls.stretch_in
                elif self.straight_orientation == 'LAST':
                    roll = ctrls.stretch_out
            self.align_bone_between_bones(curve, ctrls.stretch_in, roll, ctrls.stretch_out)

    ####################################################
    # Curve control

    @stage.generate_bones
    def make_control_chain(self):
        super().make_control_chain()
        if self.curve_control:
            orgs = self.bones.org
            ctrls = self.bones.ctrl
            curve = self.make_control_bone(orgs[self.curve_position], "_curve")
            ctrls.stretch_curve = curve
            ctrls.stretch = [ctrls.stretch_in, curve, ctrls.stretch_out]

    @stage.parent_bones
    def parent_control_chain(self):
        super().parent_control_chain()
        if self.curve_control:
            curve = self.bones.ctrl.stretch_curve
            self.set_bone_parent(curve, self.bones.mch.inherit_curve, inherit_scale='FIX_SHEAR')
            self.position_curve(curve)

    """
    @stage.rig_bones
    def offset_scale_control_curve(self):
        if self.curve_control and self.parents_curve and self.curve_parent_scale_offset:
            self.bone_scale_offset(
                self.bones.ctrl.stretch_curve,
                self.curve_parent,
                self.curve_parent_scale_x,
                self.curve_parent_scale_y,
                self.curve_parent_scale_z
            )
    """

    ####################################################
    # Curve MCH

    @stage.generate_bones
    def make_parent_mch_chain(self):
        super().make_parent_mch_chain()
        if self.curve_control:
            orgs = self.bones.org
            pos = orgs[self.curve_position]
            self.bones.mch.inherit_curve = self.make_parent_mch_bone(pos, "_inherit_curve")
            self.bones.mch.parent_curve = self.make_parent_mch_bone(pos, "_parent_curve")

    @stage.parent_bones
    def parent_parent_mch_chain(self):
        super().parent_parent_mch_chain()
        if self.curve_control:
            mchs = self.bones.mch
            parent = mchs.parent_curve
            inherit = mchs.inherit_curve
            self.set_bone_parent(inherit, parent, inherit_scale='FIX_SHEAR')
            self.set_bone_parent(parent, self.root_bone_mch)
            for curve in [parent, inherit]:
                self.position_curve(curve)
            if self.parents_curve_copy_rotation:
                align_bone_orientation(self.obj, mchs.inherit_curve, self.parents_curve_copy_rotation)
            
    @stage.rig_bones
    def rig_parent_mch_chain(self):
        super().rig_parent_mch_chain()

        if self.curve_control:
            mchs = self.bones.mch
            if self.use_parents_curve:
                targets = self.parents_curve
                curve_type = self.parents_curve_type_single
            else:
                targets = [{"name": mchs.stretch_curve}]
                curve_type = 'ARMATURE'
            self.rig_parent_mch_bone(
                mchs.parent_curve,
                targets,
                curve_type
            )
            self.rig_inherit_mch_bone(
                mchs.inherit_curve,
                self.bones.ctrl.stretch_curve,
                self.parents_curve_copy_rotation,
                self.parents_curve_copy_rotation_default,
                self.parents_curve_copy_rotation_panel,
                self.parents_curve_copy_scale,
                self.parents_curve_copy_scale_default,
                self.parents_curve_copy_scale_panel
            )

            if not self.parents_curve_copy_rotation:
                self.make_constraint(mchs.inherit_curve, 'COPY_SCALE', self.root_bone)
            
    ####################################################
    # Curve stretch MCH

    @stage.generate_bones
    def make_stretch_curve_mch(self):
        if self.curve_control and not self.use_parents_curve:
            orgs = self.bones.org
            stretch_curve = make_derived_name(orgs[0], 'mch', "_stretch_curve")
            self.bones.mch.stretch_curve = self.copy_bone(orgs[0], stretch_curve, parent=False)
            self.get_bone(stretch_curve).tail = self.get_bone(orgs[-1]).tail
            align_bone_x_axis(self.obj, stretch_curve, self.get_bone(orgs[0]).x_axis)
    
    @stage.parent_bones
    def parent_stretch_curve_mch(self):
        if self.curve_control and not self.use_parents_curve:
            self.set_bone_parent(self.bones.mch.stretch_curve, self.root_bone)

    @stage.rig_bones
    def rig_stretch_curve_mch(self):
        if self.curve_control and not self.use_parents_curve:
            mch = self.bones.mch.stretch_curve
            ctrls = self.bones.ctrl.stretch
            self.make_constraint(mch, 'COPY_LOCATION', ctrls[0])
            stretch = self.make_constraint(mch, 'STRETCH_TO', ctrls[-1], keep_axis=self.keep_axis)
            self.make_driver(stretch, 'bulge', variables=[(self.default_prop_bone, 'volume_stretch')])
    
    ####################################################
    # Stretch MCH

    @stage.generate_bones
    def make_stretch_mch_chain(self):
        if self.curve_control:
            orgs = self.bones.org
            stretch_in = make_derived_name(orgs[0], 'mch', "_stretch_in")
            stretch_out = make_derived_name(orgs[0], 'mch', "_stretch_out")
            self.bones.mch.stretch = [
                self.copy_bone(orgs[0], stretch_in, parent=False),
                self.copy_bone(orgs[0], stretch_out, parent=False),
            ]
        else:
            super().make_stretch_mch_chain()

    @stage.apply_bones
    def transform_stretch_mch_chain(self):
        if self.curve_control:
            ctrls = self.bones.ctrl.stretch
            for args in zip(self.bones.mch.stretch, ctrls, ctrls[1:]):
                self.place_chain(*args)
    
    ####################################################
    # ORG MCH chain

    @stage.rig_bones
    def rig_org_mch_chain(self):
        if self.curve_control:
            stretch = self.bones.mch.stretch
            for i, mch in zip(count(0), self.bones.mch.org):
                target = stretch[0] if i <= self.curve_position else stretch[1]
                self.rig_org_mch_bone(mch, target)
        else:
            super().rig_org_mch_chain()

    ####################################################
    # UI

    @classmethod
    def parents_ui(self, layout, params):
        box = layout.box()
        self.parents_component_ui(box, params, 'parents_in', "Base", icon='CURSOR')
        if params.curve_control:
            layout.separator()
            box = layout.box()
            self.parents_component_ui(box, params, 'parents_curve', "Curve", icon='HANDLE_AUTO', use=True)
        layout.separator()
        box = layout.box()
        self.parents_component_ui(box, params, 'parents_out', "Tip", icon='TRACKING', use=True)

    @classmethod
    def bend_ui(self, layout, params):
        super().bend_ui(layout, params)
        col = layout.column()
        if params.bend and params.curve_control:
            col = col.box()
        r = col.row()
        r.enabled = params.bend
        r.prop(params, 'curve_control', toggle=True)
        if params.bend and params.curve_control:
            r = col.row(align=True)
            r.prop(params, 'curve_control_easeout', slider=True)
            r.prop(params, 'curve_control_easein', slider=True)
            col.use_property_split = True
            col.use_property_decorate = False
            col.row().prop(params, 'curve_position')
            r = col.row()
            r.prop(params, 'curve_center', toggle=True)
            r.prop(params, 'curve_align', toggle=True)
            col.row().prop(params, 'curve_location')
            layout.separator(factor=0.2)

    ####################################################
    # SETTINGS

    @classmethod
    def add_parameters(self, params):
        super().add_parameters(params)

        params.curve_control = BoolProperty(
            name="Add Curve Control",
            default=False,
            description="Add a controller to alter the curvature from the center",
        )

        params.curve_location = StringProperty(
            name="Curve Location",
            default="",
            description="Move curve control to this bone",
        )

        params.curve_align = BoolProperty(
            name="Align",
            default=True,
            description="Align curve control to main controllers",
        )

        params.curve_position = IntProperty(
            name="Create at Segment",
            default=1,
            min=1,
            description="Position curve control at this segment",
        )

        params.curve_center = BoolProperty(
            name="Center",
            default=False,
            description="Position curve control at the segment center",
        )

        params.curve_control_easein = FloatProperty(
            name="Ease to End",
            default=1.0,
            soft_min=0.0,
            soft_max=2.0,
            description="B-Bone ease going out of curve control",
        )

        params.curve_control_easeout = FloatProperty(
            name="Ease from Start",
            default=1.0,
            soft_min=0.0,
            soft_max=2.0,
            description="B-Bone ease going into curve control",
        )

        params.use_parents_curve = BoolProperty(
            name="Complex Curve Parenting",
            default=False,
            description="Use complex parenting for the stretch curve control",
        )

        params.parents_curve_type_single = EnumProperty(
            name="Parenting Type",
            items=[
                ('CHILD_OF', "Child Of", "Child Of"),
                ('ARMATURE', "Armature", "Armature")
            ],
            default='CHILD_OF',
            description="Constraint type for single parenting. Use Armature to follow B-Bones.",
        )

        params.parents_curve_panel = EnumProperty(
            name="Parenting Panel",
            items=[
                ('NONE', "No UI", "No UI"),
                ('SWITCH', "Switch", "Switch"),
                ('SLIDER', "Slider", "Slider"),
                ('INDIVIDUAL', "Individual", "Individual")
            ],
            default='NONE',
            description="Property and panel variation to be used for dynamic parenting",
        )

        params.parents_curve_copy_rotation = StringProperty(
            name="World Rotation",
            default="",
            description="Copy world rotation from this bone",
        )

        params.parents_curve_copy_rotation_default = FloatProperty(
            name="Default",
            default=1.0,
            min=0.0,
            max=1.0,
            description="Default value for world rotation",
        )

        params.parents_curve_copy_rotation_panel = BoolProperty(
            name="World Rotation Panel",
            default=False,
            description="Add a panel for world rotation to the UI",
        )

        params.parents_curve_copy_scale = StringProperty(
            name="World Scale",
            default="",
            description="Copy world scale from this bone",
        )

        params.parents_curve_copy_scale_default = FloatProperty(
            name="Default",
            default=1.0,
            min=0.0,
            max=1.0,
            description="Default value for world scale",
        )

        params.parents_curve_copy_scale_panel = BoolProperty(
            name="Copy Scale Panel",
            default=False,
            description="Add a panel for world scale to the UI",
        )

    @classmethod
    def parameters_ui(self, layout, params):
        self.curve_ui(layout, params)
        super().parameters_ui(layout, params)