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

def getEmptyObjects():
    objects = bpy.context.scene.objects    
    empties = []
    for obj in objects:
        if obj.type == 'EMPTY':
            empties.append(obj.name)
    return empties

def isDeleted(o):
    return not (o in bpy.context.scene.objects)

def showMessageBoxInfo(message = "", title = "Message Box", icon = 'INFO'):
    def draw(self, context):
        self.layout.label(text = message)
    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)

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
    camtargetbool : bpy.props.BoolProperty(
        name = "Camera target",
        description = "Set custom camera target using Empty Plain Axes",
        default = False,
        #update = updateCameraTargetBool
    )

class PANEL_PT_AddonMainPanel(bpy.types.Panel):
    bl_label = "Main Panel"
    bl_idname = "PANEL_PT_AddonMainPanel" #not mandatory
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "TC plugins"

    @classmethod
    def poll(cls, context):
       if bpy.context.object is not None:
           return bpy.context.object.data
       else:
           return None

    def draw(self, context):
        error = False
        try:
            cam = getMyRandomCamera()
        except:
            error = True
                
        layout = self.layout
        scene = context.scene
        randRenderer = scene.my_tool
        if not error:
            layout.label(text="Preferences for Random Shot")
            layout.use_property_split = True
            layout.use_property_decorate = False
            flow = layout.grid_flow(row_major = True, columns = 0, even_columns = False, even_rows = False, align = True)
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
            sub.prop(randRenderer, "shutter_speed")
            sub.prop(cam.data, "lens", text = "Focal length")
            layout.label(text = " ")
            sub.prop(randRenderer, "camtargetbool")
            if randRenderer.camtargetbool:
                if not getEmptyObjects():
                    sub.operator_menu_enum("object.select_object", "select_objects", text = "<Select an object>")
                else:
                    sub.operator_menu_enum("object.select_object", "select_objects", text = OBJECT_OT_FillEmptiesDropdownMenu.bl_label) 
            layout.operator("object.random_shot")
        else:
            layout.label(text="Could not find 'randomcamera'")

class OBJECT_OT_FillEmptiesDropdownMenu(bpy.types.Operator):
    bl_idname = "object.select_object" # as on 2.7
    bl_label = "<Select an object>"

    def avail_objects(self,context):
        items = [(x,x,str(i)) for i,x in enumerate(getEmptyObjects())]
        print("DEBUG: 'Empty' object tuples are: "+str(items))
        return items    

    select_objects : bpy.props.EnumProperty(items = avail_objects, name = "Available Objects")

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'
        
    def execute(self,context):
        self.__class__.bl_label = self.select_objects
        print("DEBUG: Selected 'Empty' object: "+self.select_objects)
        return {'FINISHED'}

class OBJECT_OT_AddonRandomShot(bpy.types.Operator):
    """TC's Random Shot Script"""
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
        
        if not randRenderer.camtargetbool:
            camTargetLocation = (0,0,0)
        else:
            if not getEmptyObjects():
                showMessageBoxInfo("There are no Empty objects to point at, setting target to 0,0,0.")
                camTargetLocation = (0,0,0)
            else:
                if isDeleted(OBJECT_OT_FillEmptiesDropdownMenu.bl_label):
                    showMessageBoxInfo("No Empty object selected, or the selected object has been deleted. Choose another one to point at.")
                    camTargetLocation = (0,0,0)
                else:
                    camTargetLocation = bpy.data.objects[OBJECT_OT_FillEmptiesDropdownMenu.bl_label].location
             
        for step in range(0, randRenderer.rit-1):
            bpy.context.scene.frame_set(step)
            x, y, z = randomizeCoord(randRenderer.camdistmax,randRenderer.camdistmin,randRenderer.camzmin,randRenderer.camzmax,step,randRenderer.rit)
            cam.location = (x,y,z)
            cam.keyframe_insert('location')
            pointAt(cam, camTargetLocation, roll=math.radians(0))
            cam.keyframe_insert('rotation_euler')
            calculateAutofocus()
            cam.data.dof.keyframe_insert('focus_distance')
        return {'FINISHED'}

classes = [AddonProperties, PANEL_PT_AddonMainPanel, OBJECT_OT_AddonRandomShot, OBJECT_OT_FillEmptiesDropdownMenu]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.my_tool = bpy.props.PointerProperty(type = AddonProperties)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.my_tool

if __name__ == "__main__":
    register()
