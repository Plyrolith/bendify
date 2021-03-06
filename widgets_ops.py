import bpy
from mathutils import Color, Matrix

from rigify.utils.widgets import obj_to_bone
from rigify.utils.widgets_basic import *
from rigify.utils.widgets_special import *
from rigify.rigs.widgets import *

from .utils.misc import attribute_return
from .utils.widgets_bendy import *


widgets_dict = {
    'KEEP':
    {
        "name": "Keep",
        "icon": 'LOCKED',
        "function": None,
        "kwargs": [],
    },
    'LINE':
    {
        "name": "Line",
        "icon": 'IPO_LINEAR',
        "function": create_line_widget,
        "kwargs": [],
    },
    'CIRCLE':
    {
        "name": "Circle",
        "icon": 'MESH_CIRCLE',
        "function": create_circle_widget,
        "kwargs": ["radius", "head_tail", "with_line"],
    },
    'CUBE':
    {
        "name": "Cube",
        "icon": 'MESH_CUBE',
        "function": create_cube_widget,
        "kwargs": ["radius"],
    },
    'CHAIN':
    {
        "name": "Chain",
        "icon": 'UGLYPACKAGE',
        "function": create_chain_widget,
        "kwargs": ["radius", "cube", "invert", "offset"],
            
    },
    'SPHERE':
    {
        "name": "Sphere",
        "icon": 'SPHERE',
        "function": create_sphere_widget,
        "kwargs": [],    
    },
    'LIMB':
    {
        "name": "Limb",
        "icon": 'SNAP_NORMAL',
        "function": create_limb_widget,
        "kwargs": [],
    },
    'BONE':
    {
        "name": "Bone",
        "icon": 'PMARKER_SEL',
        "function": create_bone_widget,
        "kwargs": ["r1", "l1", "r2", "l2"],

    },
    'PIVOT':
    {
        "name": "Pivot",
        "icon": 'EMPTY_AXIS',
        "function": create_pivot_widget,
        "kwargs": ["axis_size", "cap_size", "square"],
    },
    'COMPASS':
    {
        "name": "Compass",
        "icon": 'MOD_CAST',
        "function": create_compass_widget,
        "kwargs": [],
    },
    'ROOT':
    {
        "name": "Root",
        "icon": 'PIVOT_CURSOR',
        "function": create_root_widget,
        "kwargs": [],
    },
    'NECK_BEND':
    {
        "name": "Neck Bendy",
        "icon": 'ORIENTATION_CURSOR',
        "function": create_neck_bend_widget,
        "kwargs": ["radius", "head_tail"],
    },
    'NECK_TWEAK':
    {
        "name": "Neck Tweak",
        "icon": 'PROP_OFF',
        "function": create_neck_tweak_widget,
        "kwargs": ["size"],
    },
    'EYE':
    {
        "name": "Eye",
        "icon": 'MESH_CIRCLE',
        "function": create_eye_widget,
        "kwargs": ["size"],
    },
    'EYES':
    {
        "name": "Eyes",
        "icon": 'PROP_PROJECTED',
        "function": create_eyes_widget,
        "kwargs": ["size"],
    },
    'EAR':
    {
        "name": "Ear",
        "icon": 'MESH_TORUS',
        "function": create_ear_widget,
        "kwargs": ["size"],
    },
    'JAW':
    {
        "name": "Jaw",
        "icon": 'INVERSESQUARECURVE',
        "function": create_jaw_widget,
        "kwargs": ["size"],
    },
    'TEETH':
    {
        "name": "Teeth",
        "icon": 'SNAP_OFF',
        "function": create_teeth_widget,
        "kwargs": ["size"],
    },
    'FACE':
    {
        "name": "Face",
        "icon": 'UGLYPACKAGE',
        "function": create_face_widget,
        "kwargs": ["size"],
    },
    'IKARROW':
    {
        "name": "IK Arrow",
        "icon": 'UV_SYNC_SELECT',
        "function": create_ikarrow_widget,
        "kwargs": ["size"],
    },
    'SIMPLE_ARROW':
    {
        "name": "Simple Arrow",
        "icon": 'SORT_DESC',
        "function": create_simple_arrow_widget,
        "kwargs": ["size", "invert"],
    },
    'WIDE_ARROW':
    {
        "name": "Wide Arrow",
        "icon": 'INDIRECT_ONLY_ON',
        "function": create_wide_arrow_widget,
        "kwargs": ["size", "invert"],
    },
    'HAND':
    {
        "name": "Hand",
        "icon": 'VIEW_PAN',
        "function": create_hand_widget,
        "kwargs": ["size"],
    },
    'FOOT':
    {
        "name": "Foot",
        "icon": 'MOD_DYNAMICPAINT',
        "function": create_foot_widget,
        "kwargs": ["size"],
    },
    'BALLSOCKET':
    {
        "name": "Ballsocket",
        "icon": 'GIZMO',
        "function": create_ballsocket_widget,
        "kwargs": ["size"],
    },
    'GEAR':
    {
        "name": "Gear",
        "icon": 'PREFERENCES',
        "function": create_gear_widget,
        "kwargs": ["radius"],
    },
    'SUB_TWEAK':
    {
        "name": "Sub Tweak",
        "icon": 'EMPTY_DATA',
        "function": create_sub_tweak_widget,
        "kwargs": ["size"],
    },
    'SQUARE':
    {
        "name": "Square",
        "icon": 'MESH_PLANE',
        "function": create_square_widget,
        "kwargs": ["size"],
    },
    'PIN':
        {
        "name": "Pin",
        "icon": 'UNPINNED',
        "function": create_pin_widget,
        "kwargs": ["size", "axis_size", "cap_size", "square", "invert"],
    },
}


#=============================================
# Mixin Classes
#=============================================

class WidgetNamesMixin():
    """Collect all widgets with their armature object and pose bone names"""

    @staticmethod
    def collect_widgets():
        D = bpy.data
        widgets = {}
        for obj in D.objects:
            if obj.type == 'ARMATURE' and not obj.data.rigify_layers:
                for pbone in obj.pose.bones:
                    if pbone.custom_shape:
                        if not pbone.custom_shape in widgets:
                            widgets[pbone.custom_shape] = {"rig": obj, "bone": pbone, "multi": False}
                        else:
                            widgets[pbone.custom_shape]["multi"] = True
        return widgets


class WidgetEditMixin():
    """Mixin class for temporary cursor, orientation and pivot settings"""
    
    @staticmethod
    def cursor(context, matrix=None, compare=None):
        c = context.scene.cursor
        matrix_old = c.matrix
        matrix_new = Matrix(compare) if compare else None
        if matrix and (not matrix_new or c.matrix == matrix_new):
            c.matrix = matrix
        return [matrix_old, c.matrix]

    @staticmethod
    def orientation(context, orientation=None):
        s = context.scene.transform_orientation_slots[0]
        orient_old = s.type
        if not orientation:
            s.type = 'LOCAL'
        elif s.type == 'LOCAL':
            s.type = orientation
        return orient_old

    @staticmethod
    def pivot(context, pivot=None):
        t = context.scene.tool_settings
        pivot_old = t.transform_pivot_point
        if not pivot:
            t.transform_pivot_point = 'CURSOR'
        elif t.transform_pivot_point == 'CURSOR':
            t.transform_pivot_point = pivot
        return pivot_old


class WidgetObjectsMixin():
    """Mixin class for collecting widget objects"""

    @staticmethod
    def widgets_from_pose_bones(pose_bones):
        """Collect widget objects from pose bones and correct their transforms
        """
        widgets = []
        for pbone in pose_bones:
            widget = pbone.custom_shape
            if widget and not widget in widgets:
                obj_to_bone(widget, pbone.id_data, pbone.name)
                widgets.append(widget)
        return widgets
    
    @staticmethod
    def collection_tmp_add(widgets, col_name="Widgets_edit"):
        """Build temporary widget collection and select widgets
        """
        D = bpy.data
        col = None
        if widgets:
            if col_name in D.collections:
                D.collections.remove(D.collections[col_name])
            col = D.collections.new(col_name)
            bpy.context.scene.collection.children.link(col)
            col.hide_select = False
            col.hide_viewport = False
            col.hide_render = True

            for widget in widgets:
                col.objects.link(widget)
                widget.hide_select = False
                widget.hide_viewport = False
                widget.hide_set(False)
                widget.select_set(True)    
        return col

    @staticmethod
    def collection_tmp_remove(col_name="Widgets_edit"):
        """Build temporary widget collection and select widgets
        """
        if col_name in bpy.data.collections:
            bpy.data.collections.remove(bpy.data.collections[col_name])

#=============================================
# Operators
#=============================================

class BENDIFY_OT_WidgetsSelect(bpy.types.Operator):
    """Select new widgets for selected bones"""
    bl_idname = "pose.widgets_select"
    bl_label = "Select Widgets"
    bl_options = {'REGISTER', 'UNDO'}

    def widgets(self, context):
        enum = []
        index = 0
        for w, a in widgets_dict.items():
            enum.append((w, a["name"], a["name"], a["icon"], index))
            index += 1
        return enum

    widget: bpy.props.EnumProperty(name="Widget", items=widgets, default=0)
    radius: bpy.props.FloatProperty(name="Radius", default=1.0, min=0.0)
    head_tail: bpy.props.FloatProperty(name="Head/Tail Position", default=0.0)
    with_line: bpy.props.BoolProperty(name="With Line", default=False)
    cube: bpy.props.BoolProperty(name="Cube", default=False)
    invert: bpy.props.BoolProperty(name="Invert", default=False)
    offset: bpy.props.FloatProperty(name="Offset", default=0.0)
    r1: bpy.props.FloatProperty(name="Head Radius", default=0.1)
    l1: bpy.props.FloatProperty(name="Head Position", default=0.0)
    r2: bpy.props.FloatProperty(name="Tail Radius", default=0.04)
    l2: bpy.props.FloatProperty(name="Tail Position", default=1.0)
    axis_size: bpy.props.FloatProperty(name="Axis Size", default=1.0, min=0.0)
    cap_size: bpy.props.FloatProperty(name="Cap Size", default=1.0, min=0.0)
    square: bpy.props.BoolProperty(name="Square" , default=True)
    size: bpy.props.FloatProperty(name="Size", default=1.0, min=0.0)

    @classmethod
    def poll(cls, context):
        return context.mode == 'POSE' and context.selected_pose_bones

    def execute(self, context):  
        rig = context.active_object

        for pb in context.selected_pose_bones:
            if not self.widget == 'KEEP':
                # Delete old widget
                wgt_name = "WGT-" + rig.name + "_" + pb.name
                if wgt_name in bpy.data.objects:
                    bpy.data.objects.remove(bpy.data.objects[wgt_name])
                
                # Basic viewport settings
                pb.custom_shape_scale = 1.0
                pb.use_custom_shape_bone_size = True

                # Create new widgets
                kwlist = widgets_dict[self.widget]["kwargs"]
                kwargs = {"rig": rig, "bone_name": pb.name}
                for kw in kwlist:
                    kwargs[kw] = getattr(self, kw)
                widgets_dict[self.widget]["function"](**kwargs)
                wgt_obj = bpy.data.objects[wgt_name]

                # Additinal resizing if missing
                if not "size" in kwargs and not "radius" in kwargs:
                    for v in wgt_obj.data.vertices:
                        v.co *= self.size
                
                # Select new widget as custom shape
                if wgt_name in bpy.data.objects:
                    pb.custom_shape = wgt_obj

        return {'FINISHED'}
    
    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.prop(self, 'widget', expand=True)
        col.row().separator()
        box = col.box()
        
        # Default arguments
        kwargs = widgets_dict[self.widget]["kwargs"]
        for a in kwargs:
            box.row().prop(self, a)

        # Guaranteed size argument
        if not "size" in kwargs and not "radius" in kwargs:
            box.row().prop(self, 'size')

    def invoke(self, context, event):
        self.widget = 'KEEP'
        return context.window_manager.invoke_props_popup(self, event)


class BENDIFY_OT_WidgetsBevel(bpy.types.Operator, WidgetObjectsMixin):
    """Convert selected widgets to curves and set bevel"""
    bl_idname = "pose.widgets_bevel"
    bl_label = "Bevel Widgets"
    bl_options = {'REGISTER', 'UNDO'}

    remove: bpy.props.BoolProperty(name="Remove", default=False)
    delta: bpy.props.FloatProperty(name="Delta", default=0.0)
    bevel_resolution: bpy.props.IntProperty(name="Resolution", default=2)
    use_fill_caps: bpy.props.BoolProperty(name="Fill Caps", default=True)
    use_smooth: bpy.props.BoolProperty(name="Smooth Curves", default=True)

    @classmethod
    def poll(cls, context):
        return context.mode == 'POSE' and context.selected_pose_bones

    def execute(self, context):
        self.prepare_widgets(context)
        self.bevel()
        self.curve_settings()
        self.curve_fix_remove()
        self.cleanup_widgets(context)
        self.collection_tmp_remove(col_name="Widgets_bevel")
        context.window.cursor_modal_restore()
        return {'FINISHED'}

    def cancel(self, context):
        for k, v in self.widgets.items():
            bpy.data.objects[k].data.bevel_depth = v['depth']
        self.curve_fix_remove()
        self.cleanup_widgets(context)
        self.collection_tmp_remove(col_name="Widgets_bevel")
        context.window.cursor_modal_restore()

    def modal(self, context, event):
        if event.shift:
            self.precision = 10000
        else:
            self.precision = 1000

        if event.type == 'MOUSEMOVE' or event.type == 'LEFT_SHIFT':
            self.delta = (event.mouse_x - self.x_init) / self.precision
            self.bevel()
        
        elif event.type == 'X':
            if event.value == 'PRESS':
                if self.remove:
                    self.remove = False
                else:
                    self.remove = True
                self.bevel()

        elif event.type == 'LEFTMOUSE':
            self.execute(context)
            return {'FINISHED'}
        
        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cancel(context)
            return {'CANCELLED'}
        
        return {'RUNNING_MODAL'}
        
    def invoke(self, context, event):
        widgets_obj = self.prepare_widgets(context)

        # Store initial bevel depth and mouse position, set viewport fix
        self.widgets = {}
        for w in widgets_obj:
            self.widgets[w.name] = {
                'depth': w.data.bevel_depth,
                'scale': w.scale
            }

        # Initial curve settings
        self.curve_fix_add()
        self.curve_settings()

        # Setup modal values
        self.x_init = event.mouse_x
        self.delta = 0
        self.precision = 1000
        self.remove = False
        
        # Modal
        context.window.cursor_modal_set('SCROLL_X')
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def draw(self, context):
        layout = self.layout
        layout.column().row().prop(self, 'remove', toggle=True)
        col = layout.column()
        col.row().prop(self, 'delta')
        col.row().prop(self, 'bevel_resolution')
        col.row().prop(self, 'use_fill_caps')
        col.row().prop(self, 'use_smooth')
        if self.remove:
            col.enabled = False

    def bevel(self):
        for k, v in self.widgets.items():
            scale_avg = max((v['scale'][0] + v['scale'][1] + v['scale'][2]) / 3, 0.0001)
            bpy.data.objects[k].data.bevel_depth = 0 if self.remove else abs(
                v['depth'] + self.delta / scale_avg
            )

    def curve_settings(self):
        for widget in self.widgets:
            w = bpy.data.objects[widget]
            w.data.bevel_resolution = self.bevel_resolution
            w.data.use_fill_caps = self.use_fill_caps
            for spline in w.data.splines:
                spline.use_smooth = self.use_smooth

    def prepare_widgets(self, context):
        """Collect widgets
        """
        widgets_obj = self.widgets_from_pose_bones(context.selected_pose_bones)
        self.collection_tmp_add(widgets_obj, col_name="Widgets_bevel")

        # Convert to curves
        widgets_mesh = [w for w in widgets_obj if not w.type == 'CURVE']
        if widgets_mesh:
            act = context.active_object
            c = context.copy()
            c['mode'] = 'OBJECT'
            c['active_object'] = widgets_mesh[0]
            c['selected_objects'] = widgets_mesh
            bpy.ops.object.convert(c, target='CURVE')
            context.view_layer.objects.active = act
        
        return widgets_obj
    
    def cleanup_widgets(self, context):
        """Convert widgets back to mesh if there's no bevel
        """
        widgets_mesh = [
            bpy.data.objects[w] for w in self.widgets \
            if bpy.data.objects[w].data.bevel_depth <= 0
        ]
        if widgets_mesh:
            act = context.active_object
            c = context.copy()
            c['mode'] = 'OBJECT'
            c['active_object'] = widgets_mesh[0]
            c['selected_objects'] = widgets_mesh
            bpy.ops.object.convert(c, target='MESH')
            context.view_layer.objects.active = act

    def curve_fix_add(self):
        """Add triangulate modifiers to fix zero bevel invisibility
        """
        for widget in self.widgets:
            w = bpy.data.objects[widget]
            if not any(m.name == "Viewport Fix" for m in w.modifiers):
                tri = w.modifiers.new(name="Viewport Fix", type='TRIANGULATE')
                tri.quad_method = 'FIXED'
                tri.ngon_method = 'CLIP'
                tri.min_vertices = 128

    def curve_fix_remove(self):
        """Remove triangulate modifiers if bevel > 0
        """
        for widget in self.widgets:
            w = bpy.data.objects[widget]
            if w.data.bevel_depth > 0:
                for mod in w.modifiers:
                    if mod.name == "Viewport Fix":
                        w.modifiers.remove(mod)


class BENDIFY_OT_WidgetsEditStart(bpy.types.Operator, WidgetEditMixin, WidgetObjectsMixin):
    """Enter edit mode for selected bones' widgets"""
    bl_idname = "pose.widgets_edit_start"
    bl_label = "Start Editing Widgets"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object \
        and context.active_object.type == 'ARMATURE' \
        and context.mode == 'POSE' \
        and context.active_pose_bone \
        and context.selected_pose_bones \
        and not hasattr(context.scene, 'edit_widgets')

    def execute(self, context):
        armas = [context.active_object]
        armas.extend([obj for obj in context.selected_objects if obj.type == 'ARMATURE' and obj not in armas])
        s = context.scene
        D = bpy.data

        widgets = self.widgets_from_pose_bones(
            context.selected_pose_bones + [context.active_pose_bone]
        )
        
        # Save active pose bone widget...
        widget_active = attribute_return(context, ['active_pose_bone', 'custom_shape'])
        
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        self.collection_tmp_add(widgets)
            
        # ... or set it to the first selected
        if not widget_active:
            widget_active = widgets[-1]
        context.view_layer.objects.active = widget_active
        
        # Set temporary cursor, orientation and pivot; add scene property
        s['edit_widgets'] = {
            "armatures": armas,
            "cursor": self.cursor(context, widget_active.matrix_world),
            "orientation": self.orientation(context),
            "pivot": self.pivot(context),
        }

        # Switch to edit mode
        bpy.ops.object.mode_set(mode='EDIT')
        return {'FINISHED'}


class BENDIFY_OT_WidgetsEditStop(bpy.types.Operator, WidgetEditMixin, WidgetObjectsMixin):
    """Exit widget edit mode and clean up"""
    bl_idname = "scene.widgets_edit_stop"
    bl_label = "Stop Editing Widgets"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return hasattr(context.scene, '["edit_widgets"]')

    def execute(self, context):
        col_name = "Widgets_edit"
        s = context.scene
        D = bpy.data

        # Find collection and property
        if col_name in D.collections:
            col = D.collections[col_name]
            if col_name in s.collection.children \
            and context.mode == 'EDIT_MESH' or context.mode == 'EDIT_CURVE' or context.mode == 'OBJECT' \
            and context.active_object.name in col.objects \
            and s['edit_widgets'] \
            and any(arma for arma in s['edit_widgets']["armatures"] if arma.name in s.objects):
                # Select/activate armatures and go into pose mode
                bpy.ops.object.mode_set(mode='OBJECT')
                bpy.ops.object.select_all(action='DESELECT')
                context.view_layer.objects.active = s['edit_widgets']["armatures"][0]
                for arma in s['edit_widgets']["armatures"]:
                    if arma.name in s.objects:
                        arma.hide_select = False
                        arma.hide_viewport = False
                        arma.hide_set(False)
                        arma.select_set(True)
                bpy.ops.object.mode_set(mode='POSE')

                # Restore cursor, orientation and pivot
                self.cursor(context, s['edit_widgets']["cursor"][0], s['edit_widgets']["cursor"][1])
                self.orientation(context, s['edit_widgets']["orientation"])
                self.pivot(context, s['edit_widgets']["pivot"])
    
        # Remove Widget_edit collection
        self.collection_tmp_remove()
        
        # Remove temporary scene property
        del s['edit_widgets']
        return {'FINISHED'}


class BENDIFY_OT_WidgetsNamesFix(bpy.types.Operator, WidgetNamesMixin):
    """Rename widgets after their bones"""
    bl_idname = "scene.widgets_names_fix"
    bl_label = "Fix Widgets Names"
    bl_options = {'REGISTER', 'UNDO'}

    #multi: bpy.props.BoolProperty(name="Include Multi-User", default=False)
    position: bpy.props.BoolProperty(name="Fix Position", default=True)

    @classmethod
    def poll(cls, context):
        return any(obj for obj in bpy.data.objects if obj.type == 'ARMATURE')

    def execute(self, context):
        changes = 0
        positions = 0
        widgets = self.collect_widgets()
        for w, v in widgets.items():
            name_new = "WGT-" + v["rig"].name + "_" + v["bone"].name
            if not v["multi"]:
                if not w.name == name_new:
                    w.name = name_new
                    print(w.name + " renamed to " + name_new)
                    changes += 1
                if self.position:
                    obj_to_bone(w, v["rig"], v["bone"].name)
                    positions += 1
        self.report({'INFO'}, str(changes) + " widgets renamed")
        return {'FINISHED'}


class BENDIFY_OT_WidgetsRemoveUnused(bpy.types.Operator, WidgetNamesMixin):
    """Remove all unused widget objects from file"""
    bl_idname = "scene.widgets_remove_unused"
    bl_label = "Remove Unused Widgets"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return any(obj for obj in bpy.data.objects if obj.type == 'ARMATURE')

    def execute(self, context):
        D = bpy.data
        deletes = 0
        widgets = self.collect_widgets()
        for obj in D.objects:
            if obj.name.startswith("WGT-") and not obj in widgets.keys():
                print(obj.name + " deleted.")
                D.objects.remove(obj)
                deletes += 1
        self.report({'INFO'}, str(deletes) + " unused widgets removed")
        return {'FINISHED'}


class BENDIFY_OT_AddBoneGroups(bpy.types.Operator):
    bl_idname = "armature.bendify_add_bone_groups"
    bl_label = "Add Bendify Bone Groups"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == 'ARMATURE'

    def execute(self, context):
        obj = context.object
        arma = obj.data
        if not hasattr(arma, 'rigify_colors'):
            return {'FINISHED'}

        groups = {
            'Root': [
                Color((1.0, 1.0, 1.0)),
                Color((1.0, 0.5, 0.0)),
                Color((1.0, 0.75, 0.5))
            ],
            'Left': [
                Color((1.0, 1.0, 1.0)),
                Color((1.0, 0.1, 0.1)),
                Color((1.0, 0.5, 0.5))
            ],
            'Center': [
                Color((1.0, 1.0, 1.0)),
                Color((0.0, 1.0, 1.0)),
                Color((0.5, 1.0, 1.0))
            ],
            'Right': [
                Color((1.0, 1.0, 1.0)),
                Color((0.0, 0.15, 1.0)),
                Color((0.5, 0.5, 1.0))
            ],
            'Tweak': [
                Color((1.0, 1.0, 1.0)),
                Color((1.0, 1.0, 0.0)),
                Color((1.0, 1.0, 0.5))
            ],
            'Details': [
                Color((1.0, 1.0, 1.0)),
                Color((0.0, 1.0, 0.0)),
                Color((0.5, 1.0, 0.5))
            ],
            'Extra': [
                Color((1.0, 1.0, 1.0)),
                Color((1.0, 0.0, 1.0)),
                Color((1.0, 0.5, 1.0))
            ]
        }

        for g in groups:
            if g in arma.rigify_colors.keys():
                continue

            col = arma.rigify_colors.add()
            col.name = g

            col.active = groups[g][0]
            col.normal = groups[g][1]
            col.select = groups[g][2]
            col.standard_colors_lock = True
        
        arma.rigify_colors_lock = False

        return {'FINISHED'}
