from rigify.utils.layers import ControlLayersOption

from ...bendy_rigs import HandleBendyRig, AlignedBendyRig, ConnectingBendyRig

class Rig(ConnectingBendyRig, AlignedBendyRig):
    """
    Simple bendy tweak chain
    """
    @classmethod
    def parameters_ui(self, layout, params):
        pass
