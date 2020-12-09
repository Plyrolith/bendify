rigify_info = {
    "name": "Bendify",
    "link": "https://github.com/Plyrolith/bendify"
}

from bpy.utils import register_class, unregister_class
from bpy.types import Scene
from bpy.props import PointerProperty

from . import alm_ops
from . import alm_ui
from .properties import BendifySceneSettings

classes = (
    BendifySceneSettings,
    alm_ops.BENDIFY_OT_AlmToggle,
    alm_ops.BENDIFY_OT_AlmSelect,
    alm_ops.BENDIFY_OT_AlmLock,
    alm_ops.BENDIFY_OT_AlmAdd,
    alm_ops.BENDIFY_OT_AlmSolo,
    alm_ui.BENDIFY_PT_ArmatureLayerManagerViewport,
)

def register():
    for c in classes:
        register_class(c)
    Scene.bendify = PointerProperty(type=BendifySceneSettings, name="Bendify Settings")

def unregister():
    for c in classes:
        unregister_class(c)