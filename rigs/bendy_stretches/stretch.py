from rigify.utils.layers import ControlLayersOption

from .stretch_bendy_rigs import HarmonicScaleStretchRig, \
StraightStretchBendyRig, ConnectingStretchBendyRig, ParentedStretchBendyRig, \
VolumeStretchBendyRig, AlignedStretchBendyRig, CurvyStretchBendyRig

class Rig(
    CurvyStretchBendyRig,
    ParentedStretchBendyRig,
    ConnectingStretchBendyRig,
    VolumeStretchBendyRig,
    StraightStretchBendyRig,
    HarmonicScaleStretchRig
    ):
    """
    All-mighty stretchy bender
    """

    ####################################################
    # SETTINGS
    
    @classmethod
    def parameters_ui(self, layout, params):
        self.bend_ui(layout, params)
        self.straight_ui(layout, params)
        self.harmonic_scale_ui(layout, params)
        self.volume_ui(layout, params)
        ControlLayersOption.TWEAK.parameters_ui(layout, params)
        