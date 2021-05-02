bl_info = {
    "name": "Random Shot",
    "blender": (2, 80, 0),
    "category": "Object",
}

import math, bpy, mathutils, random, os, time, glob

# generate x,y coordinates within an annulus and z within ranges
# divide the circle into sectors to achieve more equal density
def randomizeCoord(minR, maxR, minZ, maxZ, targetSector, maxIter):
    rad = math.sqrt(random.uniform(minR**2, maxR**2))
    sectorSize = (2*math.pi)/maxIter
    angle = random.uniform(targetSector*sectorSize, (targetSector+1)*sectorSize)
    x, y = rad*math.cos(angle),rad*math.sin(angle)
    if math.hypot(x - 0, y - 0) < minR:
        x, y = 0 - x, 0 - y
    z = random.uniform(minZ, maxZ)
    return round(x, 2), round(y, 2), round(z, 2)

# point object (cam) to target
def pointAt(obj, target, roll=0):
    if not isinstance(target, mathutils.Vector):
        target = mathutils.Vector(target)
    loc = obj.location
    direction = target - loc
    quat = direction.to_track_quat('-Z', 'Y')
    quat = quat.to_matrix().to_4x4()
    rollMatrix = mathutils.Matrix.Rotation(roll, 4, 'Z')
    loc = loc.to_tuple()
    obj.matrix_world = quat @ rollMatrix
    obj.location = loc

def updateAutofocus(self, context):
    my_tool = bpy.context.scene.my_tool
    camera = getMyRandomCamera()
    if my_tool.af_enable:
        camera.data.show_limits = True
        camera.data.dof.use_dof = True
        camera.data.display_size = 0.2
        calculateAutofocus()
        updateShutterSpeed(self, context)
    else:
        camera.data.dof.use_dof = False
        camera.data.show_limits = False

def updateShutterSpeed(self, context):
    fps = bpy.context.scene.render.fps
    shutter = bpy.context.scene.my_tool.shutter_speed
    motion = fps * shutter
    # only for EEVEE or Cycles renderer
    bpy.context.scene.render.motion_blur_shutter = motion
    bpy.context.scene.eevee.motion_blur_shutter = motion

def calculateAutofocus():
    obj = getMyRandomCamera()
    # shoot ray from center of camera until it hits a mesh and calculate distance
    ray = bpy.context.scene.ray_cast(bpy.context.view_layer.depsgraph, obj.location, obj.matrix_world.to_quaternion() @ mathutils.Vector((0.0, 0.0, -1.0)))
    distance = (ray[1] - obj.location).magnitude
    obj.data.dof.focus_distance = distance

def getMyRandomCamera(cameraname='randomcamera'):
    return bpy.data.objects[cameraname]

class AddonProperties(bpy.types.PropertyGroup):
    resx: bpy.props.IntProperty(
        name="Viewport X",
        default=1920,
    )
    resy: bpy.props.IntProperty(
        name="Viewport Y",
        default=1080,
    )
    rit: bpy.props.IntProperty(
        name="Iteration",
        default=15,
    )
    camdistmin: bpy.props.FloatProperty(
        name="Camera R min",
        default=5.0,
    )
    camdistmax: bpy.props.FloatProperty(
        name="Camera R max",
        default=30.0,
    )
    camzmin: bpy.props.FloatProperty(
        name="Camera Z min",
        default=5.0,
    )
    camzmax: bpy.props.FloatProperty(
        name="Camera Z max",
        default=10.0,
    )
    af_enable : bpy.props.BoolProperty(
        name = "Autofocus",
        description = "Enable autofocus",
        default = False,
        update = updateAutofocus
    )
    shutter_speed : bpy.props.FloatProperty(
        name = "Shutter speed",
        description = "Exposure time of the sensor in seconds. From 1/10000 to 10. Gives a motion blur effect",
        min = 0.0001,
        max = 100,
        step = 10,
        precision = 4,
        default = 0.5,
        update = updateShutterSpeed
    )

class AddonMainPanel(bpy.types.Panel):
    bl_label = "Main Panel"
    bl_idname = "object.random_shot"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "TC plugins"

    @classmethod
    def poll(cls, context):
        return bpy.context.object.data

    def draw(self, context):
        cam = getMyRandomCamera()
        layout = self.layout
        scene = context.scene
        randRenderer = scene.my_tool
        layout.label(text="Preferences for Random Shot")
        layout.use_property_split = True
        layout.use_property_decorate = False
        flow = layout.grid_flow(row_major=True, columns=0, even_columns=False, even_rows=False, align=True)
        col = flow.column()
        sub = col.column(align=True)
        sub.prop(randRenderer, "resx")
        sub.prop(randRenderer, "resy")
        sub.prop(randRenderer, "rit")
        sub.prop(randRenderer, 'af_enable')
        sub.prop(randRenderer, "camdistmin")
        sub.prop(randRenderer, "camdistmax")     
        sub.prop(randRenderer, "camzmin")
        sub.prop(randRenderer, "camzmax")
        sub.prop(randRenderer, 'shutter_speed')
        sub.prop(cam.data, 'lens', text="Focal length")
        layout.label(text=" ")
        layout.operator("object.random_shot")

class AddonRandomShot(bpy.types.Operator):
    """Random Shot Script with Autofocus support"""
    bl_idname = "object.random_shot"
    bl_label = "[ Generate keyframes ]"
    bl_options = {'REGISTER'}

    def execute(self,context):
        scene = context.scene
        randRenderer = scene.my_tool
        cam = getMyRandomCamera()

        # set camera view
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                area.spaces[0].region_3d.view_perspective = 'CAMERA'
                break

        # delete all existing keyframes
        for ob in bpy.data.objects:
            ob.animation_data_clear()

        # delete dof keyframes            
        try:
            fcurves = cam.animation_data.action.fcurves
        except AttributeError:
            pass
        else:
            for c in fcurves:
                if c.data_path.startswith("dof.focus_distance"):
                    fcurves.remove(c)

        scene = bpy.data.scenes['Scene']
        scene = context.scene
        scene.render.resolution_x = randRenderer.resx
        scene.render.resolution_y = randRenderer.resy
        scene.frame_start = 1
        scene.frame_end = randRenderer.rit
        for step in range(0, randRenderer.rit-1):
            bpy.context.scene.frame_set(step)
            x, y, z = randomizeCoord(randRenderer.camdistmax,randRenderer.camdistmin,randRenderer.camzmin,randRenderer.camzmax,step,randRenderer.rit)
            cam.location = (x,y,z)
            cam.keyframe_insert('location')
            pointAt(cam, (0,0,0), roll=math.radians(0))
            cam.keyframe_insert('rotation_euler')
            calculateAutofocus()
            cam.data.dof.keyframe_insert('focus_distance')
        return {'FINISHED'}

classes = [AddonProperties, AddonMainPanel, AddonRandomShot]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.my_tool = bpy.props.PointerProperty(type=AddonProperties)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.my_tool

if __name__ == "__main__":
    register()