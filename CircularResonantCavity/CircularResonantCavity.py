# Circular resonant cavity – command with dialog + live preview

import traceback
import adsk.core # type: ignore
import adsk.fusion # type: ignore

import math
import os

_app = None
_ui  = None
_handlers = []
_previewOcc = None   # for live preview occurrence

# Geometric helpers

def get_circle_circum(circle):
    
    r = circle.radius
    
    return 2.0 * math.pi * r

def get_arc_length_theta(arc_length, radius):
    
    return arc_length * 360.0 / (2.0 * math.pi * radius)

# Sketch helpers

def reflect_point(points, orig_pt, x=False, y=False, z=False):

    new_pt = adsk.core.Point3D.create((-1) ** x * orig_pt.x, (-1) ** y * orig_pt.y, (-1) ** z * orig_pt.z)

    return points.add(new_pt)

def rotate_entities(geom_cons, center_sk_pt, entities, quantity):
    
    circular_pattern = geom_cons.createCircularPatternInput(entities, center_sk_pt)
    
    circular_pattern.quantity = adsk.core.ValueInput.createByReal(quantity)
    circular_pattern.totalAngle = adsk.core.ValueInput.createByString("360 deg")
    
    return geom_cons.addCircularPattern(circular_pattern)

def rotate_point(points, pt, ang_deg, center):
    
    theta = math.radians(ang_deg)
    
    dx = pt.x - center.x
    dy = pt.y - center.y
    
    x_new = center.x + dx * math.cos(theta) - dy * math.sin(theta)
    y_new = center.y + dx * math.sin(theta) + dy * math.cos(theta)
    
    new_pt = adsk.core.Point3D.create(x_new, y_new, pt.z)

    return points.add(new_pt)

def draw_circle(circles, center, radius):
    
    circle = circles.addByCenterRadius(center, radius)
    circle_center = circle.centerSketchPoint
    circle_center.isFixed = True
    
    return circle, circle_center

# Extrude helpers

def extrude_profiles(extrudes, profiles, distance, extrusion_is_sym=True, operation=adsk.fusion.FeatureOperations.NewBodyFeatureOperation):

    dist = adsk.core.ValueInput.createByReal(distance)
    ext_input = extrudes.createInput(profiles, operation)
    ext_input.setDistanceExtent(extrusion_is_sym, dist)
    
    return extrudes.add(ext_input)

# Exportation helper:

def export_to_stl(ui, design):
    try:
        exportMgr = design.exportManager
        # Asking for a targeted path
        dlg = ui.createFileDialog()
        dlg.isFolderDialog = True
        dlg.title = 'Choose folder to save STL files'
        dlg.initialDirectory = os.path.expanduser('~')
        if dlg.showSave() != adsk.core.DialogResults.DialogOK:
            return
        
        # Got path
        out_dir = dlg.filename

        allComps = design.allComponents

        exported = 0

        for comp in allComps:
            bodies = adsk.core.ObjectCollection.create()

            for b in comp.bRepBodies:
                # Only export solid, visible bodies
                if not b.isSolid:
                    continue
                if hasattr(b, 'isVisible') and not b.isVisible:
                    continue
                bodies.add(b)

            if bodies.count == 0:
                continue

            comp_name = comp.name.replace(' ', '_')
            out_path = os.path.join(out_dir, f'{comp_name}.stl')

            stlOptions = exportMgr.createSTLExportOptions(bodies, out_path)
            stlOptions.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
            stlOptions.sendToPrintUtility = False

            exportMgr.execute(stlOptions)
            exported += 1

        ui.messageBox(f'Exported {exported} STL file(s) to:\n{out_dir}', 'Export all components')

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

# Main

def build(comp, r, R, w, W, h, H, t, n):

    # Create sketch
    
    sketches = comp.sketches
    xy_plane = comp.xYConstructionPlane
    sketch = sketches.add(xy_plane)

    lines = sketch.sketchCurves.sketchLines
    circles = sketch.sketchCurves.sketchCircles
    
    points = sketch.sketchPoints
    dims = sketch.sketchDimensions
    geom_cons = sketch.geometricConstraints

    extrudes = comp.features.extrudeFeatures

    center = adsk.core.Point3D.create(0, 0, 0)
    center_sk = points.add(center)

    # Circles

    c1, c1_center_sk = draw_circle(circles, center_sk, r)
    
    c2, _ = draw_circle(circles, center_sk, R)
    c3, c3_center_sk = draw_circle(circles, center_sk, r + w)
    draw_circle(circles, center_sk, R + W)

    c3_circum = get_circle_circum(c3)

    # Gap line

    c1_pt = adsk.core.Point3D.create(c1.radius, 0, 0)
    c1_sk = points.add(c1_pt)

    c3_pt = adsk.core.Point3D.create(c3.radius, 0, 0)
    c3_sk = points.add(c3_pt)

    geom_cons.addCoincident(c1_sk, c1)
    geom_cons.addCoincident(c3_sk, c3)

    c1_text_pt = adsk.core.Point3D.create(t, 0, 0)
    c3_text_pt = adsk.core.Point3D.create(t, 0, 0)

    dims.addDistanceDimension(c1_center_sk, c1_sk, adsk.fusion.DimensionOrientations.VerticalDimensionOrientation, c1_text_pt).parameter.value = t / 2.0
    dims.addDistanceDimension(c3_center_sk, c3_sk, adsk.fusion.DimensionOrientations.VerticalDimensionOrientation, c3_text_pt).parameter.value = t / 2.0

    l1 = lines.addByTwoPoints(c1_sk, c3_sk)
    l1_length = l1.length

    # Mirror Gap line

    rc1_sk = reflect_point(points, c1_sk.geometry, y=True)
    rc3_sk = reflect_point(points, c3_sk.geometry, y=True)
    l2 = lines.addByTwoPoints(rc1_sk, rc3_sk)

    # Rotate gap lines

    rotate_entities(geom_cons, center_sk, [l1, l2], n)

    # Spruces

    gap_area = t * l1_length
    
    approx_gap_arc_lengths = n * l1_length
    approx_segment_arc_lengths = c3_circum - approx_gap_arc_lengths
    
    spruce_half_angle = (get_arc_length_theta(approx_segment_arc_lengths, c3.radius) / n) * 0.25

    for profile in sketch.profiles:
        
        props = profile.areaProperties()
        
        area = props.area
        centroid = props.centroid

        x, y   = centroid.x, centroid.y
        radius = math.sqrt(x * x + y * y)

        if (gap_area < area) and (r < radius < r + w):
            
            pos_rot1_sk = rotate_point(points, centroid, int(spruce_half_angle), center)
            pos_rot2_sk = rotate_point(points, centroid, int(spruce_half_angle), center)

            geom_cons.addCoincident(pos_rot1_sk, c2)
            geom_cons.addCoincident(pos_rot2_sk, c3)

            neg_rot1_sk = rotate_point(points, centroid, -int(spruce_half_angle), center)
            neg_rot2_sk = rotate_point(points, centroid, -int(spruce_half_angle), center)

            geom_cons.addCoincident(neg_rot1_sk, c2)
            geom_cons.addCoincident(neg_rot2_sk, c3)

            l3 = lines.addByTwoPoints(pos_rot1_sk, pos_rot2_sk)
            l4 = lines.addByTwoPoints(neg_rot1_sk, neg_rot2_sk)

            rotate_entities(geom_cons, center_sk, [l3, l4], n)

    # Spruce profile condition

    min_area = float("inf")
    for profile in sketch.profiles:
        
        props = profile.areaProperties()
        
        area = props.area
        centroid = props.centroid

        x, y = centroid.x, centroid.y
        radius = math.sqrt(x * x + y * y)

        if (r + w < radius < R):
            min_area = min(min_area, area)

    # Extrude spruces + electrode
    
    profile_collection = adsk.core.ObjectCollection.create()
    for profile in sketch.profiles:
        
        props = profile.areaProperties()
        
        area = props.area
        centroid = props.centroid

        x, y = centroid.x, centroid.y
        radius = math.sqrt(x * x + y * y)

        # electode profile
        if (gap_area < area) and (r < radius < r + w):
            profile_collection.add(profile)

        # spruce profile
        if abs(area - (1 + 1e-5) * min_area) <= 1e-5 and (r + w < radius < R):
            profile_collection.add(profile)

    extrude_profiles(extrudes, profile_collection, h)

    # Shield

    shield_profile = None
    max_diag_len = 0.0

    for profile in sketch.profiles:
        
        bb = profile.boundingBox
        diag_vec = bb.minPoint.vectorTo(bb.maxPoint)
        diag_len = diag_vec.length

        if max_diag_len < diag_len:
            shield_profile = profile
            max_diag_len = diag_len

    profile_collection = adsk.core.ObjectCollection.create()
    profile_collection.add(shield_profile)
    extrude_profiles(extrudes, profile_collection, H, operation=adsk.fusion.FeatureOperations.JoinFeatureOperation)

def _read_params_from_inputs(inputs):
    
    r = inputs.itemById("r").value
    R = inputs.itemById("R").value
    w = inputs.itemById("w").value
    W = inputs.itemById("W").value
    h = inputs.itemById("h").value
    H = inputs.itemById("H").value
    t = inputs.itemById("t").value
    n = inputs.itemById("n").value
    
    return r, R, w, W, h, H, t, int(n)

class CavityDestroyHandler(adsk.core.CommandEventHandler):
    
    def __init__(self):
        super().__init__()
    
    def notify(self, args):
        
        try:
            adsk.terminate()
        except:
            if _ui:
                _ui.messageBox("Destroy failed:\n{}".format(traceback.format_exc()))

class CavityExecuteHandler(adsk.core.CommandEventHandler):
    
    def __init__(self):
        super().__init__()
    
    def notify(self, args):
        
        try:
            
            design = adsk.fusion.Design.cast(_app.activeProduct)
            if not design:
                _ui.messageBox("No design is active. Open a design and try again.")
                return

            root_comp = design.rootComponent
            cmd = adsk.core.Command.cast(args.command)
            inputs = cmd.commandInputs

            r, R, w, W, h, H, t, n = _read_params_from_inputs(inputs)

            # If preview already created geometry, we can just keep it.
            # If for some reason preview was off, build once here.
            
            if _previewOcc is None or not _previewOcc.isValid:
                build(root_comp, r, R, w, W, h, H, t, n)
                export_to_stl(_ui, design)

        except:
            if _ui:
                _ui.messageBox("Execute failed:\n{}".format(traceback.format_exc()))

class CavityExecutePreviewHandler(adsk.core.CommandEventHandler):
    
    def __init__(self):
        super().__init__()
    
    def notify(self, args):
        
        global _previewOcc
        
        try:
            
            design = adsk.fusion.Design.cast(_app.activeProduct)
            if not design:
                return

            root_comp = design.rootComponent
            cmd = adsk.core.Command.cast(args.command)
            inputs = cmd.commandInputs

            r, R, w, W, h, H, t, n = _read_params_from_inputs(inputs)

            # Delete previous preview occurrence if it exists

            if _previewOcc and _previewOcc.isValid:
                _previewOcc.deleteMe()
                _previewOcc = None

            # Create a new occurrence for the preview

            occs = root_comp.occurrences
            new_occ = occs.addNewComponent(adsk.core.Matrix3D.create())
            comp = new_occ.component

            build(comp, r, R, w, W, h, H, t, n)

            _previewOcc = new_occ

            # Tell Fusion this preview is good enough to keep if user hits OK

            args.isValidResult = True

        except:
            if _ui:
                _ui.messageBox("Preview failed:\n{}".format(traceback.format_exc()))

class CavityCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    
    def __init__(self):
        super().__init__()
    
    def notify(self, args):
        
        try:
        
            cmd = adsk.core.Command.cast(args.command)

            # Destroy handler

            onDestroy = CavityDestroyHandler()
            cmd.destroy.add(onDestroy)
            _handlers.append(onDestroy)

            # Execute handler

            onExecute = CavityExecuteHandler()
            cmd.execute.add(onExecute)
            _handlers.append(onExecute)

            # Preview handler

            onPreview = CavityExecutePreviewHandler()
            cmd.executePreview.add(onPreview)
            _handlers.append(onPreview)

            inputs = cmd.commandInputs

            inputs.addValueInput("r", "Electrode radius r", "cm", adsk.core.ValueInput.createByReal(1.25))
            inputs.addValueInput("R", "Shield radius R", "cm", adsk.core.ValueInput.createByReal(1.8))
            inputs.addValueInput("w", "Electrode width w", "cm", adsk.core.ValueInput.createByReal(0.38))
            inputs.addValueInput("W", "Shield width W", "cm", adsk.core.ValueInput.createByReal(0.5))
            inputs.addValueInput("h", "Electrode height h", "cm", adsk.core.ValueInput.createByReal(2.0))
            inputs.addValueInput("H", "Shield height H", "cm", adsk.core.ValueInput.createByReal(2.25))
            inputs.addValueInput("t", "Gap length t", "cm", adsk.core.ValueInput.createByReal(0.2138))
            
            inputs.addIntegerSpinnerCommandInput("n", "Gap quantity n", 1, 100, 1, 6)

        except:
            if _ui:
                _ui.messageBox("CommandCreated failed:\n{}".format(traceback.format_exc()))


def run(context):
    
    try:
        
        global _app, _ui
        
        _app = adsk.core.Application.get()
        _ui  = _app.userInterface

        id = "circularResonantCavityCmd"

        cmdDef = _ui.commandDefinitions.itemById(id)
        if not cmdDef:
            cmdDef = _ui.commandDefinitions.addButtonDefinition(id, "Circular Resonant Cavity", "Creates a circular resonant cavity (with live preview).")

        onCommandCreated = CavityCommandCreatedHandler()
        cmdDef.commandCreated.add(onCommandCreated)
        _handlers.append(onCommandCreated)

        cmdDef.execute()

        # Keep script alive for events

        adsk.autoTerminate(False)

    except:
        if _ui:
            _ui.messageBox("Run failed:\n{}".format(traceback.format_exc()))
