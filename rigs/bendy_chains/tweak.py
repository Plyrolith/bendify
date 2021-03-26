from rigify.utils.layers import ControlLayersOption

from ...bendy_rigs import HandleBendyRig, ComplexBendyRig, AlignedBendyRig, ConnectingBendyRig

class Rig(ConnectingBendyRig, AlignedBendyRig, ComplexBendyRig):
    """
    Simple bendy tweak chain
    """

    @classmethod
    def parameters_ui(self, layout, params):
        layout.row().prop(params, 'show_advanced')
        if params.show_advanced:
            box = layout.box()
            self.tip_ui(self, box, params)
            self.align_ui(self, box, params)
            self.complex_stretch_ui(self, box, params)
            self.rotation_mode_tweak_ui(self, box, params)
            self.org_transform_ui(self, box, params)
            self.volume_ui(self, box, params)
        box = layout.box()
        self.bbones_ui(self, box, params)
