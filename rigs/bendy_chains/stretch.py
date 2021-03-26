from rigify.utils.layers import ControlLayersOption

from .stretch_bendy_rigs import ComplexStretchBendyRig, HarmonicScaleStretchRig, \
StraightStretchBendyRig, ConnectingStretchBendyRig, ParentedStretchBendyRig, \
ScalingStretchBendyRig, AlignedStretchBendyRig, CurvyStretchBendyRig

class Rig(
    CurvyStretchBendyRig,
    AlignedStretchBendyRig,
    ScalingStretchBendyRig,
    ParentedStretchBendyRig,
    ConnectingStretchBendyRig,
    StraightStretchBendyRig,
    HarmonicScaleStretchRig,
    ComplexStretchBendyRig
    ):
    """
    All-mighty stretchy bender
    """

    ####################################################
    # SETTINGS
    
    @classmethod
    def parameters_ui(self, layout, params):
        box = layout.box()
        box.label(text="Settings For At Least 2 Segments", icon='INFO')
        self.bend_ui(self, box, params)
        self.harmonic_scale_ui(self, box, params)
        self.straight_ui(self, box, params)
        layout.prop(params, 'show_advanced')
        if params.show_advanced:
            box = layout.box()
            self.parent_ui(self, box, params)
            self.scale_ui(self, box, params)
            self.align_ui(self, box, params)
            box_a = box.box()
            box_a.label(text="Tweak Attaching Requires At Least 2 Segments", icon='INFO')
            self.volume_ui(self, box, params)
            self.complex_stretch_ui(self, box, params)
            self.rotation_mode_tweak_ui(self, box, params)
            self.org_transform_ui(self, box, params)
        box = layout.box()
        self.bbones_ui(self, box, params)
        ControlLayersOption.TWEAK.parameters_ui(layout, params)
        