rigify_info = {
    "name": "Bendify",
    "link": "https://github.com/Plyrolith/bendify"
}

from bpy.utils import register_class, unregister_class
from bpy.types import Scene
from bpy.props import PointerProperty

from .alm_ops import *
from .alm_ui import *
from .tools_ops import *
from .tools_ui import *
from .widgets_ops import *
from .widgets_ui import *
from .rigify_ui import *
from .props import BendifySceneSettings

classes = (
    BENDIFY_OT_AlmToggle,
    BENDIFY_OT_AlmSelect,
    BENDIFY_OT_AlmLock,
    BENDIFY_OT_AlmAdd,
    BENDIFY_OT_AlmSolo,
    BENDIFY_OT_DrawBlendSwitch,
    BENDIFY_OT_StretchToReset,
    BENDIFY_OT_ConstraintsMirror,
    BENDIFY_OT_ConstraintsAddArmature,
    BENDIFY_OT_ObjectNamesNormalize,
    BENDIFY_OT_MaterialSlotsSwitch,
    BENDIFY_OT_MirrorAllWeights,
    BENDIFY_OT_RigifyCopyToSelected,
    BENDIFY_OT_WidgetsSelect,
    BENDIFY_OT_WidgetsTransform,
    BENDIFY_OT_WidgetsEditStart,
    BENDIFY_OT_WidgetsEditStop,
    BENDIFY_OT_WidgetsNamesFix,
    BENDIFY_OT_WidgetsRemoveUnused,
    BENDIFY_OT_AddBoneGroups,
    BENDIFY_PT_ArmatureLayerManagerViewport,
    BENDIFY_PT_BoneGroups,
    BENDIFY_PT_BoneType,
    BENDIFY_PT_RigifyButtons,
    BENDIFY_PT_BendifyToolsPose,
    BENDIFY_PT_BendifyToolsObject,
    BENDIFY_PT_BendifyToolsWeightPaint,
    BENDIFY_PT_BendifyWidgets,
    BendifySceneSettings,
)

def register():
    for c in classes:
        register_class(c)
    Scene.bendify = PointerProperty(type=BendifySceneSettings, name="Bendify Settings")

def unregister():
    for c in classes:
        unregister_class(c)