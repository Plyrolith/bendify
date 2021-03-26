from bpy.props import *

from itertools import count

from rigify.base_rig import stage
from rigify.utils.bones import align_bone_orientation, align_bone_x_axis, copy_bone_position, put_bone, set_bone_widget_transform
from rigify.utils.layers import ControlLayersOption
from rigify.utils.misc import map_list
from rigify.utils.naming import make_derived_name, strip_org
from rigify.utils.widgets_basic import create_bone_widget
from rigify.utils.widgets_special import create_neck_bend_widget

from ...bendy_rigs import HandleBendyRig, ComplexBendyRig, AlignedBendyRig, AttachedBendyRig, ConnectingBendyRig, ScaleOffsetMixin
from .chain_bendy_rigs import ChainBendyRig

from ...utils.bones import align_bone_to_bone_axis, real_bone
from ...utils.misc import threewise_nozip
from ...utils.mechanism import make_armature_constraint
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
        start = self.make_control_start()
        end = self.make_control_end()
        self.bones.ctrl.stretch = [start, end]
        
    def make_control_start(self):
        orgs = self.bones.org
        start = make_derived_name(orgs[0], 'ctrl', "_in")
        start = self.copy_bone(orgs[0], start, parent=False, scale=0.75)
        self.default_prop_bone = start
        return start
    
    def make_control_end(self):
        orgs = self.bones.org
        end = make_derived_name(orgs[0], 'ctrl', "_out")
        end = self.copy_bone(orgs[-1], end, parent=False, scale=0.75)
        put_bone(self.obj, end, self.get_bone(orgs[-1]).tail)
        return end
        
    @stage.parent_bones
    def parent_control_chain(self):
        for ctrl in self.bones.ctrl.stretch:
            self.set_bone_parent(ctrl, self.root_bone)

    @stage.configure_bones
    def configure_control_chain(self):
        #orgs = self.bones.org
        for ctrl in self.bones.ctrl.stretch:
        #for ctrl, org in zip(self.bones.ctrl.stretch, [orgs[0], orgs[-1]]):
            #self.copy_bone_properties(org, ctrl)
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
        create_bone_widget(self.obj, ctrl, r1=1.0, l1=-0.5, r2=1.0, l2=0.5)

    ####################################################
    # Tweak Targets

    def check_mch_parents(self):
        return (len(self.bones.org) + 1) * [self.bones.mch.stretch[0]]

    def check_mch_targets(self):
        ctrls = self.bones.ctrl.stretch
        return threewise_nozip([ctrls[0], *self.bones.org[1:], ctrls[-1]])

    ####################################################
    # Tweak chain

    @stage.generate_bones
    def make_tweak_chain(self):
        '''Removed first tweak as default prop bone'''
        orgs = self.bones.org
        self.bones.ctrl.tweak = map_list(self.make_tweak_bone, count(0), orgs + orgs[-1:])

    @stage.configure_bones
    def configure_tweak_chain(self):
        super().configure_tweak_chain()
        ControlLayersOption.TWEAK.assign(self.params, self.obj, self.bones.ctrl.tweak)

    ####################################################
    # Tweak MCH chain

    @stage.rig_bones
    def rig_tweak_mch_chain(self):
        for mch in self.attribute_return(['bones', 'mch', 'tweak'], True):
            self.make_constraint(
                mch, 'COPY_SCALE', self.root_bone,
                space='CUSTOM', space_object=self.obj, space_subtarget=self.root_bone
            )

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
        self.make_constraint(bone, 'COPY_ROTATION', start, use_x=False, use_z=False, space='LOCAL')
        self.make_constraint(bone, 'COPY_ROTATION', end, use_x=False, use_z=False, space='LOCAL', mix_mode='ADD')
        self.make_constraint(bone, 'DAMPED_TRACK', end)
        stretch = self.make_constraint(bone, 'STRETCH_TO', end)
        self.make_driver(stretch, 'bulge', variables=[(self.default_prop_bone, 'volume_stretch')])

    ##############################
    # Deform chain

    @stage.rig_bones
    def rig_deform_chain(self):
        ctrls = self.bones.ctrl
        for args in zip(self.bones.deform, ctrls.tweak, ctrls.tweak[1:]):
            self.rig_deform_bone(*args, self.root_bone)

    ####################################################
    # UI

    def volume_ui(self, layout, params):
        r = layout.row(align=True)
        r.prop(params, 'volume_stretch_default', slider=True)
        r.prop(params, 'volume_stretch_panel', text="", icon='OPTIONS')
        super().volume_ui(self, layout, params)

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
            description="Default value for stretch volume variation"
        )

        params.volume_stretch_panel = BoolProperty(
            name="Stretch Volume Variation Panel",
            default=False,
            description="Add panel to control volume variation to the UI"
        )

    @classmethod
    def parameters_ui(self, layout, params):
        self.volume_ui(self, layout, params)
        self.rotation_mode_tweak_ui(self, layout, params)
        self.org_transform_ui(self, layout, params)
        self.bbones_ui(self, layout, params)
        ControlLayersOption.TWEAK.parameters_ui(layout, params)


class SingleSegmentStretchBendyRig(StretchBendyRig):
    """
    Stretchy rig with reduced complexity for single segment
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
    # Stretch MCHs

    @stage.generate_bones
    def make_stretch_mch_chain(self):
        if not self.single_segment:
            super().make_stretch_mch_chain()
    
    @stage.parent_bones
    def parent_stretch_mch_chain(self):
        if not self.single_segment:
            super().parent_stretch_mch_chain()

    @stage.rig_bones
    def rig_stretch_mch_chain(self):
        if not self.single_segment:
            super().rig_stretch_mch_chain()

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


class ArmatureStretchBendyRig(SingleSegmentStretchBendyRig):
    """
    Base stretchy rig with additional MCH layer for more complex mechanics
    """

    def initialize(self):
        super().initialize()

        self.arma_mch = False

    ####################################################
    # Tweak Targets

    def check_mch_parents(self):
        if self.arma_mch:
            return self.bones.mch.arma
        else:
            return super().check_mch_parents()

    def check_mch_targets(self):
        if self.arma_mch:
            return threewise_nozip(self.check_mch_parents())
        else:
            return super().check_mch_targets()

    ####################################################
    # Tweak MCH chain

    @stage.rig_bones
    def rig_tweak_mch_chain(self):
        mchs = self.attribute_return(['bones', 'mch', 'tweak'])
        if mchs:
            ctrls = self.bones.ctrl
            if self.arma_mch and not len(ctrls.stretch) == len(ctrls.tweak):
                targets = self.check_mch_targets()

                for i, mch, p, c, n  in zip(count(0), mchs, *targets):
                    self.rig_tweak_mch_bone(i, mch, self.root_bone, p, c, n)
            else:
                super().rig_tweak_mch_chain()

    ####################################################
    # Armature MCHs

    @stage.generate_bones
    def make_arma_mch_chain(self):
        if self.arma_mch:
            orgs = self.bones.org
            self.bones.mch.arma = map_list(self.make_arma_mch_bone, count(0), orgs + orgs[-1:])

    def make_arma_mch_bone(self, i, org):
        name = make_derived_name(org, 'mch', '_arma')
        name = self.copy_bone(org, name, parent=False)

        if i == len(self.bones.org):
            put_bone(self.obj, name, self.get_bone(org).tail)
        
        return name
    
    @stage.parent_bones
    def parent_arma_mch_chain(self):
        if self.arma_mch:
            for arma in self.bones.mch.arma:
                self.set_bone_parent(arma, self.bones.mch.stretch[0])
    
    @stage.parent_bones
    def align_arma_mch_chain(self):
        if self.arma_mch:
            for arma in self.bones.mch.arma:
                align_bone_orientation(self.obj, arma, self.bones.mch.stretch[0])


### Combine from the following

class ComplexStretchBendyRig(SingleSegmentStretchBendyRig, ComplexBendyRig):
    """
    Stretchy rig with copied stretch constraints for better non-uniform scalability
    """


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
            description="Offset tweak X and Z scale by stretch main controls scale"
        )


    @classmethod
    def parameters_ui(self, layout, params):
        self.harmonic_scale_ui(self, layout, params)
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
            ctrls = self.bones.ctrl.stretch
            orgs = self.bones.org
            first_org = self.get_bone(orgs[0])
            last_org = self.get_bone(orgs[-1])
            for ctrl in (ctrls[0], ctrls[-1]):
                bone = self.get_bone(ctrl)
                length = bone.length
                bone.head = first_org.head
                bone.tail = last_org.tail
                bone.length = length
            put_bone(self.obj, ctrls[-1], last_org.tail)
            align_bone_x_axis(self.obj, ctrls[0], last_org.x_axis if self.straight_orientation == 'LAST' else first_org.x_axis)
            align_bone_x_axis(self.obj, ctrls[-1], first_org.x_axis if self.straight_orientation == 'FIRST' else last_org.x_axis)

    ####################################################
    # UI

    def straight_ui(self, layout, params):
        layout.row().prop(params, 'straight', toggle=True)
        if params.straight:
            layout.row().prop(params, 'straight_orientation', expand=True)

    ####################################################
    # SETTINGS

    @classmethod
    def add_parameters(self, params):
        super().add_parameters(params)

        params.straight = BoolProperty(
            name="Straighten CTRLs",
            default=False,
            description="Align stretch controls to form a straight line by default"
        )

        params.straight_orientation = EnumProperty(
            items=[
                ('FIRST', "Use First", "Use First"),
                ('LAST', "Use Last", "Use Last"),
                ('BOTH', "Individual", "Individual")
            ],
            name="Orientation",
            default='FIRST',
            description="New orientation for stretch controllers"
        )


    @classmethod
    def parameters_ui(self, layout, params):
        self.straight_ui(self, layout, params)
        super().parameters_ui(layout, params)


class ConnectingStretchBendyRig(SingleSegmentStretchBendyRig, ConnectingBendyRig):
    """
    Stretchy rig that can connect to a (tweak of its) parent, as well as attach its tip to another bone.
    """
    def initialize(self):
        super().initialize()
        self.base = None if self.single_segment else self.params.base
        self.tip = None if self.single_segment else self.params.tip
        self.base_type = 'NONE' if self.single_segment else self.params.base_type

    ####################################################
    # Tweak MCH chain

    @stage.generate_bones
    def make_tweak_mch_chain(self):
        if not self.single_segment:
            ConnectingBendyRig.make_tweak_mch_chain(self)
        else:
            mchs = self.bones.mch
            mchs.base = None
            mchs.tip = None


class ParentedStretchBendyRig(SingleSegmentStretchBendyRig, ScaleOffsetMixin):
    """
    Stretchy rig with armature constrained start and end handles
    """

    def initialize(self):
        super().initialize()

        self.parent_start = self.params.parent_start
        self.parent_start_scale_offset = self.params.parent_start_scale_offset
        self.parent_start_scale_x = self.params.parent_start_scale_x
        self.parent_start_scale_y = self.params.parent_start_scale_y
        self.parent_start_scale_z = self.params.parent_start_scale_z

        self.parent_end = self.params.parent_end
        self.parent_end_scale_offset = self.params.parent_end_scale_offset
        self.parent_end_scale_x = self.params.parent_end_scale_x
        self.parent_end_scale_y = self.params.parent_end_scale_y
        self.parent_end_scale_z = self.params.parent_end_scale_z

    ##############################
    # Controls & MCHs

    @stage.configure_bones
    def offset_scale_stretch_controls(self):
        stretchs = self.bones.ctrl.stretch
        if self.real_bone(self.parent_start) and self.parent_start_scale_offset:
            self.bone_scale_offset(
                stretchs[0],
                self.parent_start,
                self.parent_start_scale_x,
                self.parent_start_scale_y,
                self.parent_start_scale_z
            )
        if self.real_bone(self.parent_end) and self.parent_end_scale_offset:
            self.bone_scale_offset(
                stretchs[-1],
                self.parent_end,
                self.parent_end_scale_x,
                self.parent_end_scale_y,
                self.parent_end_scale_z
            )

    @stage.configure_bones
    def arma_constraint_control_arma_mch(self):
        mchs = self.bones.mch
        arma_mchs = [mchs.arma_in, mchs.arma_out]
        subtargets = [self.parent_start, self.parent_end]
        scales = [self.parent_start_scale_offset, self.parent_end_scale_offset]
        for mch, subtarget, scale in zip(arma_mchs, subtargets, scales):
            if mch and self.real_bone(subtarget):
                make_armature_constraint(self.obj, self.get_bone(mch), [subtarget])
                if scale:
                    self.make_constraint(mch, 'COPY_SCALE', self.root_bone)

    @stage.apply_bones
    def reparent_control_arma_mch(self):
        stretchs = self.bones.ctrl.stretch
        ctrls = [stretchs[0], stretchs[-1]]
        mchs = self.bones.mch
        mchs_arma = [mchs.arma_in, mchs.arma_out]
        checks = [self.parent_start, self.parent_end]
        for mch, ctrl, check in zip(mchs_arma, ctrls, checks):
            if mch and self.real_bone(check):
                self.get_bone(mch).parent = None
                self.set_bone_parent(ctrl, mch)

    ##############################
    # Stretch control
    
    @stage.generate_widgets
    def make_control_widgets(self):
        ctrls = self.bones.ctrl
        if self.real_bone(self.parent_start):
            create_simple_arrow_widget(
                self.obj,
                ctrls.stretch[0],
                size=0.75
            )
        if self.real_bone(self.parent_end):
            create_simple_arrow_widget(
                self.obj,
                ctrls.stretch[-1],
                size=0.75,
                invert=True
            )
        super().make_control_widgets()


    ##############################
    # Control MCH

    @stage.generate_bones
    def make_control_arma_mch(self):
        orgs = self.bones.org
        mchs = self.bones.mch
        if self.parent_start:
            if self.single_segment:
                start = self.make_tweak_mch_bone(0, orgs[0])
            else:
                start = make_derived_name(orgs[0], 'mch', "_in")
                start = self.copy_bone(orgs[0], start, parent=False)
            mchs.arma_in = start
        else:
            mchs.arma_in = None

        if self.parent_end:
            if self.single_segment:
                end = self.make_tweak_mch_bone(1, orgs[-1])
            else:
                end = make_derived_name(orgs[-1], 'mch', "_out")
                end  = self.copy_bone(orgs[-1], end, parent=False)
                put_bone(self.obj, end, self.get_bone(orgs[-1]).tail)
            mchs.arma_out = end
        else:
            mchs.arma_out = None

    ####################################################
    # UI

    def parent_start_ui(self, layout, params):
        r = layout.row(align=True)
        r.prop(params, 'parent_start')
        if params.parent_start:
            r.prop(params, 'parent_start_scale_offset', text="", icon='CON_SIZELIKE')
            if params.parent_start_scale_offset:
                r = layout.row()
                r.prop(params, 'parent_start_scale_x', text="X")
                r.prop(params, 'parent_start_scale_y', text="Y")
                r.prop(params, 'parent_start_scale_z', text="Z")

    def parent_end_ui(self, layout, params):
        r = layout.row(align=True)
        r.prop(params, 'parent_end')
        if params.parent_end:
            r.prop(params, 'parent_end_scale_offset', text="", icon='CON_SIZELIKE')
            if params.parent_end_scale_offset:
                r = layout.row()
                r.prop(params, 'parent_end_scale_x', text="X")
                r.prop(params, 'parent_end_scale_y', text="Y")
                r.prop(params, 'parent_end_scale_z', text="Z")

    def parent_ui(self, layout, params):
        self.parent_start_ui(self, layout, params)
        self.parent_end_ui(self, layout, params)


    ####################################################
    # SETTINGS

    @classmethod
    def add_parameters(self, params):
        super().add_parameters(params)

        params.parent_start = StringProperty(
            name="Start Parent",
            default="",
            description="Set the parent for the start handle of the stretchy control curve"
        )

        params.parent_end = StringProperty(
            name="End Parent",
            default="",
            description="Set the parent for the end handle of the stretchy control curve"
        )

        params.parent_start_scale_offset = BoolProperty(
            name="Copy Start Parent Scale",
            default=False,
            description="Set scale offset for start controller"
        )

        params.parent_end_scale_offset = BoolProperty(
            name="Copy End Parent Scale",
            default=False,
            description="Set scale offset for end controller"
        )

        params.parent_start_scale_x = EnumProperty(
            items=self.offset_axes,
            name="X Source Axis",
            default='X',
            description="Source axis for X scale start offset"
        )

        params.parent_start_scale_y = EnumProperty(
            items=self.offset_axes,
            name="Y Source Axis",
            default='Y',
            description="Source axis for Y scale start offset"
        )

        params.parent_start_scale_z = EnumProperty(
            items=self.offset_axes,
            name="Z Source Axis",
            default='Z',
            description="Source axis for Z scale start offset"
        )

        params.parent_end_scale_x = EnumProperty(
            items=self.offset_axes,
            name="X Source Axis",
            default='X',
            description="Source axis for X scale end offset"
        )

        params.parent_end_scale_y = EnumProperty(
            items=self.offset_axes,
            name="Y Source Axis",
            default='Y',
            description="Source axis for Y scale end offset"
        )

        params.parent_end_scale_z = EnumProperty(
            items=self.offset_axes,
            name="Z Source Axis",
            default='Z',
            description="Source axis for Z scale end offset"
        )


    @classmethod
    def parameters_ui(self, layout, params):
        self.parent_ui(self, layout, params)
        super().parameters_ui(layout, params)


class ScalingStretchBendyRig(SingleSegmentStretchBendyRig, ScaleOffsetMixin):
    """
    Stretchy rig with volume scaling control
    """

    def initialize(self):
        super().initialize()

        self.deform_scale = self.params.deform_scale
        self.deform_scale_x = self.params.deform_scale_x
        self.deform_scale_z = self.params.deform_scale_z

    ##############################
    # Deform

    @stage.finalize
    def offset_scale_deform_chain(self):
        if self.real_bone(self.deform_scale):
            for deform in self.bones.deform:
                self.bone_scale_offset(
                    deform,
                    self.deform_scale,
                    self.deform_scale_x,
                    'Y',
                    self.deform_scale_z,
                    use_y=False
                )

    ####################################################
    # UI

    def scale_ui(self, layout, params):
        layout.row().prop(params, 'deform_scale')
        if params.deform_scale:
            r = layout.row()
            r.prop(params, 'deform_scale_x', text="X")
            r.prop(params, 'deform_scale_z', text="Z")

    ####################################################
    # SETTINGS

    @classmethod
    def add_parameters(self, params):
        super().add_parameters(params)

        params.deform_scale = StringProperty(
            name="Volume Copy",
            default="",
            description="Copy X/Y scale from this bone"
        )

        params.deform_scale_x = EnumProperty(
            items=self.offset_axes,
            name="X Source Axis",
            default='X',
            description="Source axis for X scale deform offset"
        )

        params.deform_scale_z = EnumProperty(
            items=self.offset_axes,
            name="Z Source Axis",
            default='Z',
            description="Source axis for Z scale deform offset"
        ) 

    @classmethod
    def parameters_ui(self, layout, params):
        self.scale_ui(self, layout, params)
        super().parameters_ui(layout, params)


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
            if self.real_bone(self.align_y_start):
                align_bone_to_bone_axis(
                    self.obj, stretchs[0],
                    self.align_y_start, self.align_y_start_axis, self.align_y_start_preserve
                )
            if self.real_bone(self.align_y_end):
                align_bone_to_bone_axis(
                    self.obj, stretchs[-1],
                    self.align_y_end, self.align_y_end_axis, self.align_y_end_preserve
                )


# Classify these first though


class EasingStretchBendyRig(ArmatureStretchBendyRig):
    """
    Bendy stretchy rig
    """
    def initialize(self):
        super().initialize()

        self.bend = False if self.single_segment else self.params.bend
        self.bend_easein = self.params.bend_easein
        self.bend_easeout = self.params.bend_easeout
        if self.bend:
            self.arma_mch = True

    ##############################
    # Stretch control

    @stage.rig_bones
    def unlock_control_chain_scale_y_rotation(self):
        if self.bend:
            ctrls = self.bones.ctrl.stretch
            for ctrl in ctrls:
                ctrl_pb = self.get_bone(ctrl)
                ctrl_pb.lock_rotation_w = False
                ctrl_pb.lock_rotation = [False] * 3
                if len(self.bones.org) >= len(self.bones.ctrl.stretch):
                    ctrl_pb.lock_scale[1] = False
    
    ####################################################
    # Bend MCH

    @stage.generate_bones
    def make_bend_mch_chain(self):
        if self.bend:
            orgs = self.bones.org
            bend = make_derived_name(orgs[0], 'mch', "_bend")
            self.bones.mch.bend = [self.copy_bone(orgs[0], bend, parent=False)]
            self.get_bone(bend).tail = self.get_bone(orgs[-1]).tail
            align_bone_x_axis(self.obj, bend, self.get_bone(orgs[0]).x_axis)

    @stage.parent_bones
    def parent_bend_mch_chain(self):
        if self.bend:
            for bend in self.bones.mch.bend:
                self.set_bone_parent(bend, self.root_bone)

    @stage.parent_bones
    def ease_bend_mch_chain(self):
        if self.bend:
            ctrls = self.bones.ctrl.stretch
            segments = min(len(self.bones.org) * 3, 32)
            for bend, handle_start, handle_end in zip(self.bones.mch.bend, ctrls, ctrls[1:]):
                self.setup_bbone(bend, segments, self.bend_easein, self.bend_easeout, handle_start, handle_end)

    @stage.rig_bones
    def rig_bend_mch_chain(self):
        if self.bend:
            ctrls = self.bones.ctrl.stretch
            mchs = self.bones.mch
            for args in zip(mchs.bend, ctrls, ctrls[1:], mchs.stretch):
                self.rig_bend_mch_bone(*args)

    def rig_bend_mch_bone(self, bone, start, end, scale):
        self.make_constraint(bone, 'COPY_LOCATION', start)
        self.make_constraint(bone, 'DAMPED_TRACK', end)
        self.make_constraint(
            bone, 'COPY_SCALE', scale,
            space='CUSTOM', space_object=self.obj, space_subtarget=self.root_bone
        )
        
    @stage.rig_bones
    def drivers_bend_mch_chain(self):
        if self.bend and len(self.bones.org) >= len(self.bones.ctrl.stretch):
            ctrls = self.bones.ctrl.stretch
            for mch, handle_in, handle_out in zip(self.bones.mch.bend, ctrls, ctrls[1:]):
                self.driver_bbone_ease(mch, [handle_in], [handle_out])

    ####################################################
    # Armature MCHs
    
    @stage.apply_bones
    def apply_arma_mch_chain(self):
        if self.bend:
            for arma in self.bones.mch.arma:
                self.get_bone(arma).parent = None

    @stage.rig_bones
    def rig_arma_mch_chain(self):
        if self.bend:
            for arma in self.bones.mch.arma:
                owner = self.get_bone(arma)
                make_armature_constraint(self.obj, owner, [self.bones.mch.bend[0]])

    ####################################################
    # UI

    def bend_ui(self, layout, params):
        layout.row().prop(params, 'bend', toggle=True)
        if params.bend:
            r = layout.row(align=True)
            r.prop(params, 'bend_easein', slider=True)
            r.prop(params, 'bend_easeout', slider=True)

    ####################################################
    # SETTINGS

    @classmethod
    def add_parameters(self, params):
        super().add_parameters(params)

        params.bend = BoolProperty(
            name="Bend Between CTRLs",
            default=True,
            description="Use a bendy control curve between start and end handles"
        )

        params.bend_easein = FloatProperty(
            name="Ease In",
            default=1.0,
            soft_min=0.0,
            soft_max=2.0,
            description="Easing in for the control curve"
        )

        params.bend_easeout = FloatProperty(
            name="Ease Out",
            default=1.0,
            soft_min=0.0,
            soft_max=2.0,
            description="Easing out for the control curve"
        )

    @classmethod
    def parameters_ui(self, layout, params):
        self.bend_ui(self, layout, params)
        super().parameters_ui(layout, params)


class CurvyStretchBendyRig(EasingStretchBendyRig, ScaleOffsetMixin):
    """
    Stretchy rig with curve control
    """

    def initialize(self):
        super().initialize()

        self.curve_control = self.params.curve_control if self.bend else False
        self.curve_position = self.params.curve_position
        self.curve_center = self.params.curve_center
        self.curve_control_easein = self.params.curve_control_easein
        self.curve_control_easeout = self.params.curve_control_easeout

        self.curve_parent = self.params.curve_parent
        self.curve_parent_scale_offset = self.params.curve_parent_scale_offset
        self.curve_parent_scale_x = self.params.curve_parent_scale_x
        self.curve_parent_scale_y = self.params.curve_parent_scale_y
        self.curve_parent_scale_z = self.params.curve_parent_scale_z

        self.curve_location = self.params.curve_location

        if self.curve_control:
            self.arma_mch = True

        if not self.single_segment and self.curve_control and not (self.curve_position < len(self.bones.org)):
            self.raise_error("Please specify a valid curve control position.")

    ####################################################
    # Utilities

    def place_chain(self, bone, handle_in, handle_out):
        bone_e = self.get_bone(bone)
        in_e = self.get_bone(handle_in)
        out_e = self.get_bone(handle_out)
        
        bone_e.head = in_e.head
        bone_e.tail = out_e.head
        align_bone_x_axis(self.obj, bone, in_e.x_axis)


    ####################################################
    # Curve control

    @stage.generate_bones
    def make_control_chain(self):
        if self.curve_control:
            start = self.make_control_start()
            curve = self.make_control_curve()
            end = self.make_control_end()
            self.bones.ctrl.stretch = [start, curve, end]
        else:
            super().make_control_chain()

    def make_control_curve(self):
        orgs = self.bones.org
        pos = orgs[self.curve_position]
        curve = make_derived_name(orgs[0], 'ctrl', "_curve")
        curve = self.copy_bone(pos, curve, parent=False, scale=0.75)
        if self.curve_center:
            pos_b = self.get_bone(pos)
            pos_v = pos_b.head + (pos_b.tail - pos_b.head) / 2
            put_bone(self.obj, curve, pos=pos_v)
        self.curve_bone = curve
        return curve

    @stage.parent_bones
    def parent_control_curve(self):
        if self.curve_control:
            if self.real_bone(self.curve_location):
                copy_bone_position(self.obj, self.curve_location, self.curve_bone)
            if self.curve_control:
                self.set_bone_parent(self.curve_bone, self.bones.mch.curve)

    """
    @stage.configure_bones
    def configure_control_curve(self):
        if self.curve_bone:
            self.copy_bone_properties(self.bones.org[self.curve_position], self.curve_bone)
    """

    @stage.rig_bones
    def offset_scale_control_curve(self):
        if self.curve_control and self.real_bone(self.curve_parent) and self.curve_parent_scale_offset:
            self.bone_scale_offset(
                self.curve_bone,
                self.curve_parent,
                self.curve_parent_scale_x,
                self.curve_parent_scale_y,
                self.curve_parent_scale_z
            )

    ####################################################
    # Curve MCH

    @stage.generate_bones
    def make_curve_mch(self):
        if self.curve_control:
            orgs = self.bones.org
            pos = orgs[self.curve_position]
            curve = make_derived_name(orgs[0], 'mch', "_curve")
            self.bones.mch.curve = self.copy_bone(pos, curve, parent=False)
            if self.curve_center:
                pos_b = self.get_bone(pos)
                pos_v = pos_b.head + (pos_b.tail - pos_b.head) / 2
                put_bone(self.obj, curve, pos=pos_v)

    @stage.parent_bones
    def align_curve_mch(self):
        if self.curve_control:
            if self.real_bone(self.curve_parent):
                target = self.curve_parent
            else:
                target = self.bones.mch.curve_stretch
            align_bone_orientation(self.obj, self.bones.mch.curve, target)

    @stage.apply_bones
    def apply_curve_mch(self):
        if self.curve_control:
            self.get_bone(self.bones.mch.curve).parent = None
            
    @stage.rig_bones
    def rig_curve_mch(self):
        if self.curve_control:
            if self.real_bone(self.curve_parent):
                target = self.curve_parent
            else:
                target = self.bones.mch.curve_stretch
            mch = self.bones.mch.curve
            make_armature_constraint(self.obj, self.get_bone(mch), [target])
            self.make_constraint(
                mch, 'COPY_SCALE', self.root_bone,
                space='CUSTOM', space_object=self.obj, space_subtarget=self.root_bone
            )

    ####################################################
    # Curve stretch MCH

    """
    NEEDS COMPLEX #FIX
    """

    @stage.generate_bones
    def make_curve_stretch_mch(self):
        if self.curve_control and not self.real_bone(self.curve_parent):
            orgs = self.bones.org
            curve_stretch = make_derived_name(orgs[0], 'mch', "_curve_stretch")
            self.bones.mch.curve_stretch = self.copy_bone(orgs[0], curve_stretch, parent=False)
            self.get_bone(curve_stretch).tail = self.get_bone(orgs[-1]).tail
            align_bone_x_axis(self.obj, curve_stretch, self.get_bone(orgs[0]).x_axis)
    
    @stage.parent_bones
    def parent_curve_stretch_mch(self):
        if self.curve_control and not self.real_bone(self.curve_parent):
            self.set_bone_parent(self.bones.mch.curve_stretch, self.root_bone)

    @stage.rig_bones
    def rig_curve_stretch_mch(self):
        if self.curve_control and not self.real_bone(self.curve_parent):
            mch = self.bones.mch.curve_stretch
            ctrls = self.bones.ctrl.stretch
            self.make_constraint(mch, 'COPY_LOCATION', ctrls[0])
            self.make_constraint(mch, 'DAMPED_TRACK', ctrls[-1])
            stretch = self.make_constraint(mch, 'STRETCH_TO', ctrls[-1])
            self.make_driver(stretch, 'bulge', variables=[(self.default_prop_bone, 'volume_stretch')])

    ####################################################
    # Bend MCH

    @stage.generate_bones
    def make_bend_mch_chain(self):
        if self.curve_control:
            orgs = self.bones.org
            bend_in = make_derived_name(orgs[0], 'mch', "_bend_in")
            bend_out = make_derived_name(orgs[0], 'mch', "_bend_out")
            self.bones.mch.bend = [
                self.copy_bone(orgs[0], bend_in, parent=False),
                self.copy_bone(orgs[0], bend_out, parent=False),
            ]
        else:
            super().make_bend_mch_chain()

    @stage.apply_bones
    def transform_bend_mch_chain(self):
        if self.curve_control:
            ctrls = self.bones.ctrl.stretch
            for args in zip(self.bones.mch.bend, ctrls, ctrls[1:]):
                self.place_chain(*args)

    @stage.parent_bones
    def ease_bend_mch_chain(self):
        if self.curve_control:
            ctrls = self.bones.ctrl.stretch
            segments = min(len(self.bones.org) * 3, 32)
            eases = [self.bend_easein, self.curve_control_easein, self.curve_control_easeout, self.bend_easeout]
            for bend, ease_in, ease_out, handle_start, handle_end in zip(self.bones.mch.bend, eases, eases[2:], ctrls, ctrls[1:]):
                self.setup_bbone(bend, segments, ease_in, ease_out, handle_start, handle_end)
        else:
            super().ease_bend_mch_chain()

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

    def rig_stretch_mch_bone(self, bone, start, end):
        if self.curve_control and not self.real_bone(self.curve_parent):
            self.make_constraint(bone, 'COPY_LOCATION', start)
            self.make_constraint(bone, 'COPY_ROTATION', start, use_x=False, use_z=False, space='LOCAL')
            self.make_constraint(bone, 'COPY_ROTATION', end, use_x=False, use_z=False, space='LOCAL', mix_mode='ADD')
            self.make_constraint(bone, 'DAMPED_TRACK', end)
            self.make_constraint(bone, 'STRETCH_TO', end, bulge=0, volume='NO_VOLUME')
        else:
            super().rig_stretch_mch_bone(bone,start,end)

    ####################################################
    # Armature MCHs

    @stage.parent_bones
    def align_arma_mch_chain(self):
        if self.curve_control:
            bend = self.bones.mch.bend
            for i, arma in zip(count(0), self.bones.mch.arma):
                target = bend[0] if i <= self.curve_position else bend[1]
                align_bone_orientation(self.obj, arma, target)
        else:
            super().align_arma_mch_chain()
    
    @stage.rig_bones
    def rig_arma_mch_chain(self):
        if self.curve_control:
            bend = self.bones.mch.bend
            for i, arma in zip(count(0), self.bones.mch.arma):
                owner = self.get_bone(arma)
                target = bend[0] if i <= self.curve_position else bend[1]
                make_armature_constraint(self.obj, owner, [target])
        else:
            super().rig_arma_mch_chain()

    ####################################################
    # UI

    def bend_ui(self, layout, params):
        super().bend_ui(self, layout, params)
        if params.bend:
            layout.row().prop(params, 'curve_control', toggle=True)
            if params.curve_control:
                r = layout.row(align=True)
                r.prop(params, 'curve_position')
                r.prop(params, 'curve_center', text="", icon='SNAP_MIDPOINT')
                r = layout.row(align=True)
                r.prop(params, 'curve_control_easeout', slider=True)
                r.prop(params, 'curve_control_easein', slider=True)
                layout.row().prop(params, 'curve_location')
                r = layout.row(align=True)
                r.prop(params, 'curve_parent')
                if params.curve_parent:
                    r.prop(params, 'curve_parent_scale_offset', text="", icon='CON_SIZELIKE')
                    if params.curve_parent_scale_offset:
                        r = layout.row()
                        r.prop(params, 'curve_parent_scale_x', text="X")
                        r.prop(params, 'curve_parent_scale_y', text="Y")
                        r.prop(params, 'curve_parent_scale_z', text="Z")

    ####################################################
    # SETTINGS

    @classmethod
    def add_parameters(self, params):
        super().add_parameters(params)

        params.curve_control = BoolProperty(
            name="Add Curve Control",
            default=False,
            description="Add a controller to alter the curvature from the center"
        )

        params.curve_parent = StringProperty(
            name="Parent",
            default="",
            description="Switch parenting to this bone"
        )

        params.curve_location = StringProperty(
            name="Location",
            default="",
            description="Move curve control to this bone"
        )

        params.curve_position = IntProperty(
            name="Curve Position",
            default=1,
            min=1,
            description="Position curve control at this segment"
        )

        params.curve_center = BoolProperty(
            name="Curve Center",
            default=False,
            description="Position curve control at the segment center"
        )

        params.curve_control_easein = FloatProperty(
            name="Ease to End",
            default=1.0,
            soft_min=0.0,
            soft_max=2.0,
            description="B-Bone ease going out of curve control"
        )

        params.curve_control_easeout = FloatProperty(
            name="Ease from Start",
            default=1.0,
            soft_min=0.0,
            soft_max=2.0,
            description="B-Bone ease going into curve control"
        )

        params.curve_parent_scale_offset = BoolProperty(
            name="Copy Curve Parent Scale",
            default=False,
            description="Set scale offset for curve controller"
        )

        params.curve_parent_scale_x = EnumProperty(
            items=self.offset_axes,
            name="X Source Axis",
            default='X',
            description="Source axis for X scale curve offset"
        )

        params.curve_parent_scale_y = EnumProperty(
            items=self.offset_axes,
            name="Y Source Axis",
            default='Y',
            description="Source axis for Y scale curve offset"
        )

        params.curve_parent_scale_z = EnumProperty(
            items=self.offset_axes,
            name="Z Source Axis",
            default='Z',
            description="Source axis for Z scale curve offset"
        )

    @classmethod
    def parameters_ui(self, layout, params):
        self.curve_ui(self, layout, params)
        super().parameters_ui(layout, params)