from bpy.props import *

from itertools import count

from rigify.base_rig import stage
from rigify.utils.naming import strip_org, make_derived_name
from rigify.utils.misc import map_list
from rigify.utils.layers import ControlLayersOption
from rigify.utils.bones import align_bone_orientation, align_bone_roll, align_bone_x_axis, align_bone_y_axis, copy_bone_position, set_bone_widget_transform
from rigify.utils.widgets_basic import create_bone_widget
from rigify.rigs.widgets import create_ballsocket_widget

from ...bendy_rigs import HandleBendyRig, ComplexBendyRig, AlignedBendyRig, ConnectingBendyRig
from ...utils.bones import align_bone_to_bone_axis, align_bone, distance, real_bone
from ...utils.misc import threewise_nozip


class ChainBendyRig(HandleBendyRig):
    """
    FK bendy rig
    """

    def initialize(self):
        super().initialize()
        self.org_transform = self.params.org_transform_fk

    ##############################
    # Control chain

    @stage.generate_bones
    def make_control_chain(self):
        self.bones.ctrl.fk = map_list(self.make_control_bone, count(0), self.bones.org)
        self.default_prop_bone = self.bones.ctrl.fk[0]

    def make_control_bone(self, i, org):
        return self.copy_bone(org, make_derived_name(org, 'ctrl'), parent=True)

    @stage.parent_bones
    def parent_control_chain(self):
        self.parent_bone_chain(self.bones.ctrl.fk, use_connect=False)
        self.set_bone_parent(self.bones.ctrl.fk[0], self.root_bone)

    @stage.configure_bones
    def configure_control_chain(self):
        for args in zip(count(0), self.bones.ctrl.fk, self.bones.org):
            self.configure_control_bone(*args)

    def configure_control_bone(self, i, ctrl, org):
        self.copy_bone_properties(org, ctrl)

    @stage.generate_widgets
    def make_control_widgets(self):
        for args in zip(count(0), self.bones.ctrl.fk):
            self.make_control_widget(*args)

    def make_control_widget(self, i, ctrl):
        create_bone_widget(self.obj, ctrl)

    ####################################################
    # Tweak Targets

    def check_mch_parents(self):
        fks = self.bones.ctrl.fk
        return fks + fks[-1:]

    def check_mch_targets(self):
        return threewise_nozip(self.check_mch_parents())

    ####################################################
    # Tweak chain

    @stage.generate_bones
    def make_tweak_chain(self):
        '''Removed first tweak as default prop bone'''
        orgs = self.bones.org
        self.bones.ctrl.tweak = map_list(self.make_tweak_bone, count(0), orgs + orgs[-1:])

    @stage.configure_bones
    def configure_tweak_chain(self):
        tweaks = self.bones.ctrl.tweak
        for args in zip(count(0), tweaks):
            self.configure_tweak_bone(*args)

        ControlLayersOption.TWEAK.assign(self.params, self.obj, tweaks)

    ##############################
    # ORG chain
    
    @stage.rig_bones
    def rig_org_chain(self):
        ctrls = self.bones.ctrl
        for args in zip(self.bones.org, self.bones.deform, ctrls.tweak, ctrls.tweak[1:], ctrls.fk):
            self.rig_org_bone(*args)
            
    def rig_org_bone(self, org, deform, tweak, next_tweak, fk):
        if self.org_transform == 'FK':
            self.make_constraint(org, 'COPY_TRANSFORMS', fk)
        else:
            super().rig_org_bone(org, deform, tweak, next_tweak)


    ####################################################
    # Deform bones

    @stage.rig_bones
    def rig_deform_chain(self):
        ctrls = self.bones.ctrl
        for args in zip(self.bones.deform, ctrls.tweak, ctrls.tweak[1:], ctrls.fk):
            self.rig_deform_bone(*args)

    ####################################################
    # UI
    
    def org_transform_ui(self, layout, params):
        layout.row().prop(params, 'org_transform_fk', text="ORGs")

    ####################################################
    # SETTINGS

    @classmethod
    def add_parameters(self, params):
        params.org_transform_fk = EnumProperty(
            name="ORG Transform base",
            items=(
                ('FK', "FK Controls", "FK Controls"),
                ('DEF', "Deforms", "Deforms"),
                ('TWEAK', "Single Tweak", "Single Tweak"),
                ('TWEAKS', "Between Tweaks", "BetweenTweaks")
            ),
            default='FK',
            description="Source of ORG transformation; useful to determine children's behaviour"
        )  

    @classmethod
    def parameters_ui(self, layout, params):
        super().parameters_ui(layout, params)
        ControlLayersOption.TWEAK.parameters_ui(layout, params)


### Combine from the following:

# Frankensteined classes

class ComplexChainBendyRig(ComplexBendyRig, ChainBendyRig):
    """
    Bendy chain rig with copied stretch constraints for better non-uniform scalability
    """

    ##############################
    # Deform MCH

    @stage.rig_bones
    def rig_deform_mch_chain(self):
        if self.complex_stretch:
            ctrls = self.bones.ctrl
            for args in zip(count(0), self.bones.mch.deform, ctrls.tweak, ctrls.tweak[1:], ctrls.fk):
                self.rig_deform_mch_bone(*args)


class AlignedChainBendyRig(AlignedBendyRig, ChainBendyRig):
    """
    Bendy chain rig with start and end Y-alignment
    """


class ConnectingChainBendyRig(ConnectingBendyRig, ChainBendyRig):
    """
    Bendy rig that can connect to a (tweak of its) parent, as well as attach its tip to another bone.
    """


# End of Frankensteined classes... following are specific to Bendy Chains; still combinable!


class SegmentedChainBendyRig(ChainBendyRig):
    """
    Bendy chain with indivdually scaling fk segments
    """

    def initialize(self):
        super().initialize()

        self.segmented_fk = self.params.segmented_fk if len(self.bones.org) > 1 else False
        self.segmented_align = self.params.segmented_align
        self.segmented_rotation_follow_default = self.params.segmented_rotation_follow_default
        self.segmented_rotation_follow_panel = self.params.segmented_rotation_follow_panel

    ####################################################
    # Control chain

    @stage.parent_bones
    def parent_control_chain(self):
        if self.segmented_fk:
            fks = self.bones.ctrl.fk
            self.set_bone_parent(fks[0], self.root_bone)
            for fk, parent in zip(fks[1:], self.bones.mch.fk):
                self.set_bone_parent(fk, parent)
        else:
            super().parent_control_chain()

    @stage.configure_bones
    def configure_rotation_follow_properties(self):
        ctrls = self.bones.ctrl
        master = self.default_prop_bone
        if master:
            for fk in ctrls.fk[1:]:
                self.make_property(
                    master,
                    'rotation_follow_' + fk,
                    default=self.segmented_rotation_follow_default,
                    min=0.0,
                    max=1.0,
                    description='Rotation Follow for Segment ' + fk
                )

                if self.segmented_rotation_follow_panel:
                    panel = self.script.panel_with_selected_check(self, self.bones.ctrl.flatten())
                    panel.custom_prop(
                        master,
                        'rotation_follow_' + fk,
                        text=fk + ' Follow',
                        slider=True
                    )

    ####################################################
    # FK MCH chain

    @stage.generate_bones
    def make_fk_mch_chain(self):
        if self.segmented_fk:
            self.bones.mch.fk = map_list(self.make_fk_mch_bone, count(0), self.bones.org[1:])

    def make_fk_mch_bone(self, i, org):
        name = make_derived_name(org, 'mch')
        name = self.copy_bone(org, name, parent=False)
        
        return name

    @stage.parent_bones
    def parent_fk_mch_chain(self):
        if self.segmented_fk:
            for mch in self.bones.mch.fk:
                self.set_bone_parent(mch, self.root_bone)

    @stage.rig_bones
    def rig_fk_mch_chain(self):
        if self.segmented_fk:
            mchs = self.bones.mch
            for mch, target, fk in zip(mchs.fk, mchs.fktarget, self.bones.ctrl.fk[1:]):
                self.make_constraint(mch, 'COPY_LOCATION', target)
                rotation = self.make_constraint(mch, 'COPY_ROTATION', target, space='CUSTOM', space_object=self.obj, space_subtarget=self.root_bone)
                self.make_driver(rotation, 'influence', variables=[(self.default_prop_bone, 'rotation_follow_' + fk)])

    ####################################################
    # FK MCH target chain

    @stage.generate_bones
    def make_fktarget_mch_chain(self):
        if self.segmented_fk:
            self.bones.mch.fktarget = map_list(self.make_fktarget_mch_bone, count(0), self.bones.org[1:])

    def make_fktarget_mch_bone(self, i, org):
        name = make_derived_name(org + "_target", 'mch')
        name = self.copy_bone(org, name, parent=False)
        
        return name

    @stage.parent_bones
    def parent_fktarget_mch_chain(self):
        if self.segmented_fk:
            for mch, parent in zip(self.bones.mch.fktarget, self.bones.ctrl.fk):
                self.set_bone_parent(mch, parent, inherit_scale='ALIGNED' if self.params.segmented_align else 'FULL')
    
    ####################################################
    # UI

    def segmented_fk_ui(self, layout, params):
        split = layout.split(align=True)
        split.row(align=True).prop(params, "segmented_fk", toggle=True)
        r = split.row(align=True)
        r.row(align=True).prop(params, "segmented_align", toggle=True)
        if not params.segmented_fk:
            r.enabled = False
        if params.segmented_fk:
            r = layout.row(align=True)
            r.prop(params, "segmented_rotation_follow_default", slider=True)
            r.prop(params, "segmented_rotation_follow_panel", text="", icon='OPTIONS')

    ####################################################
    # SETTINGS

    @classmethod
    def add_parameters(self, params):
        super().add_parameters(params)

        params.segmented_fk = BoolProperty(
            name="Segmented FK",
            description="Isolate FK controller scaling",
            default=False
            )
        
        params.segmented_align = BoolProperty(
            name="Align Segments",
            description="Align segment scaling by default for better control; may result in unexprected master scaling behavior",
            default=True
            )

        params.segmented_rotation_follow_default = FloatProperty(
            name="Rotation Follow Default",
            default=1.0,
            min=0.0,
            max=1.0,
            description="Default rotation follow per segment"
        )

        params.segmented_rotation_follow_panel = BoolProperty(
            name="Rotation Follow Panel",
            default=False,
            description="Add panel to control rotation follow to the UI"
        )


    @classmethod
    def parameters_ui(self, layout, params):
        self.segmented_fk_ui(self, layout, params)
        super().parameters_ui(layout, params)


class MasterControlChainBendyRig(ChainBendyRig):
    """
    Connecting Bendy with a master controller.
    """

    def initialize(self):
        super().initialize()

        self.master_control = self.params.master_control
        self.master_rotation_mode = self.params.master_rotation_mode

    ####################################################
    # Master control

    @stage.generate_bones
    def make_master_control(self):
        if self.master_control:
            base = self.base_bone
            self.bones.ctrl.master = self.copy_bone(base, make_derived_name(base, 'ctrl', '_master'))
    
    @stage.parent_bones
    def parent_master_control(self):
        if self.master_control:
            self.set_bone_parent(self.bones.ctrl.master, self.root_bone)

    @stage.configure_bones
    def configure_master_control(self):
        if self.master_control:
            master = self.bones.ctrl.master
            bone = self.get_bone(master)
            bone.lock_location = (True, True, True)
            bone.lock_scale = (True, True, True)
            bone.rotation_mode = self.master_rotation_mode

    @stage.generate_widgets
    def make_master_control_widget(self):
        if self.master_control:
            ctrls = self.bones.ctrl
            bone = ctrls.master
            create_ballsocket_widget(self.obj, bone, size=0.7)
            transform = ctrls.fk[-1] if self.attribute_return(['tip_bone']) else ctrls.tweak[-1]
            set_bone_widget_transform(self.obj, bone, transform)

    
    ####################################################
    # Copy rotation

    @stage.rig_bones
    def rig_copy_rotation(self):
        if self.master_control:
            fktarget = self.attribute_return(['bones', 'mch', 'fktarget'])
            if fktarget:
                rots = [self.bones.ctrl.fk[0]] + fktarget
            else:
                rots = self.bones.ctrl.fk

            for ctrl in rots:
                self.make_constraint(ctrl, 'COPY_ROTATION', self.bones.ctrl.master, space='LOCAL', mix_mode='BEFORE')

    ####################################################
    # UI

    def master_control_ui(self, layout, params):
        split = layout.row(align=True).split(align=True)
        split.row(align=True).prop(params, "master_control", toggle=True)
        r = split.row(align=True)
        r.prop(params, "master_rotation_mode", text="")
        if not params.master_control:
            r.enabled=False

    ####################################################
    # SETTINGS

    @classmethod
    def add_parameters(self, params):
        super().add_parameters(params)

        rotation_modes = (
            ('QUATERNION', 'Quaternion (WXYZ)', 'Quaternion (WXYZ)'),
            ('XYZ', 'XYZ', 'XYZ'),
            ('XZY', 'XZY', 'XZY'), 
            ('YXZ', 'YXZ', 'YXZ'),
            ('YZX', 'YZX', 'YZX'),
            ('ZXY', 'ZXY', 'ZXY'),
            ('ZYX', 'ZYX', 'ZYX'),
            ('AXIS_ANGLE', 'Axis Angle', 'Axis Angle') 
        )

        params.master_rotation_mode = EnumProperty(
            name="Default Master Control Rotation Mode",
            items=rotation_modes,
            default='XYZ',
            description="Default rotation mode for master control"
        )

        params.master_control = BoolProperty(
            name="Master Control",
            description="Add master controller for the whole chain",
            default=False
            )

    @classmethod
    def parameters_ui(self, layout, params):
        self.master_control_ui(self, layout, params)
        super().parameters_ui(layout, params)


class RotMechChainBendyRig(ChainBendyRig):
    """
    Connecting Bendy rig that can copy or cancel its parent's rotation.
    """

    def initialize(self):
        super().initialize()
        
        self.rotation_bones = []

    ####################################################
    # Utilities

    def get_parent_parent_mch(self, default_bone):
        """ Return the parent's master control bone if connecting and found. """
        master = self.attribute_return(['rigify_parent', 'bones', 'ctrl', 'master'])
        if master and self.attribute_return(['base_type']) in ('PARENT', 'TWEAK'):
            return master
        else:
            return default_bone

    def get_parent_master_panel(self, default_bone):
        """ Return the parent's master control bone if connecting and found, and script panel. """

        controls = self.bones.ctrl.flatten()
        prop_bone = self.get_parent_parent_mch(default_bone)

        if prop_bone != default_bone:
            owner = self.rigify_parent
            controls += self.rigify_parent.bones.ctrl.flatten()
        else:
            owner = self

        return prop_bone, self.script.panel_with_selected_check(owner, controls)

    ####################################################
    # Rotation follow

    @stage.generate_bones
    def make_mch_control_bones(self):
        self.bones.mch.rot = self.make_mch_follow_bone(self.base_bone, self.base_bone, 1.0)
        self.root_bone = self.bones.mch.rot

    def make_mch_follow_bone(self, org, name, defval, *, copy_scale=False):
        bone = self.copy_bone(org, make_derived_name('ROT-'+name, 'mch'), parent=True)
        self.rotation_bones.append((org, name, bone, defval, copy_scale))
        return bone

    ####################################################
    # MCH bones associated with main controls

    @stage.parent_bones
    def parent_mch_control_bones(self):
        self.set_bone_parent(self.bones.mch.rot, self.rig_parent_bone)

    @stage.parent_bones
    def align_mch_follow_bones(self):
        #self.follow_bone = self.get_parent_parent_mch('root')
        self.follow_bone = 'root'

        for org, name, bone, defval, copy_scale in self.rotation_bones:
            align_bone_orientation(self.obj, bone, self.follow_bone)

    @stage.configure_bones
    def configure_mch_follow_bones(self):
        self.prop_bone, panel = self.get_parent_master_panel(self.default_prop_bone)

        for org, name, bone, defval, copy_scale in self.rotation_bones:
            textname = name.replace('_',' ').title() + ' Follow'

            self.make_property(self.prop_bone, name+'_follow', default=defval)
            panel.custom_prop(self.prop_bone, name+'_follow', text=textname, slider=True)

    @stage.rig_bones
    def rig_mch_follow_bones(self):
        for org, name, bone, defval, copy_scale in self.rotation_bones:
            self.rig_mch_rotation_bone(bone, name+'_follow', copy_scale)

    def rig_mch_rotation_bone(self, mch, prop_name, copy_scale):
        con = self.make_constraint(mch, 'COPY_ROTATION', self.follow_bone)

        self.make_driver(con, 'influence', variables=[(self.prop_bone, prop_name)], polynomial=[1,-1])

        if copy_scale:
            self.make_constraint(mch, 'COPY_SCALE', self.follow_bone)
