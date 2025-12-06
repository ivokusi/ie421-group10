"""This file acts as the main module for this script."""

import traceback
import adsk.core # type: ignore
import adsk.fusion # type: ignore
# import adsk.cam

import math

# Initialize the global variables for the Application and UserInterface objects.
app = adsk.core.Application.get()
ui  = app.userInterface

# User input helpers

def get_param_length(units_manager: adsk.core.UnitsManager, prompt: str, title: str, default: str) ->  None | float:

    while True:

        param, cancelled = ui.inputBox(prompt, title, default)

        if cancelled:
            return None

        try:

            param_in_cms = units_manager.evaluateExpression(param, "cm")
            return param_in_cms
        
        except:

            ui.messageBox(f"Could not understand '{param}'. Please enter a valid length.")        

def get_param_quantity(prompt: str, title: str, default: str) -> None | int:

    while True:
        
        param, cancelled = ui.inputBox(prompt, title, default)

        if cancelled:
            return None

        try:
            
            value = int(param)
            
            if value <= 0:
                raise ValueError
            
            return value

        except ValueError:
            
            ui.messageBox(f"'{param}' is not a valid positive integer.")

# Sketch helpers

def reflect_point(points: adsk.fusion.SketchPoints, orig_pt: adsk.core.Point3D, x: bool=False, y: bool=False, z:bool=False) -> adsk.fusion.SketchPoint:

    new_pt = adsk.core.Point3D.create((-1) ** x * orig_pt.x, (-1) ** y * orig_pt.y, (-1) ** z * orig_pt.z)
    new_sk = points.add(new_pt)

    return new_sk

def rotate_entities(geom_cons, center_sk_pt, entities, quantity):

    cp_input = geom_cons.createCircularPatternInput(entities, center_sk_pt)
    
    cp_input.quantity   = adsk.core.ValueInput.createByReal(quantity)
    cp_input.totalAngle = adsk.core.ValueInput.createByString("360 deg")

    cp = geom_cons.addCircularPattern(cp_input)

    return cp

def rotate_point(pt: adsk.core.Point3D, ang_deg: float, center: adsk.core.Point3D):

    theta = math.radians(ang_deg)

    dx = pt.x - center.x
    dy = pt.y - center.y

    x_new = center.x + dx * math.cos(theta) - dy * math.sin(theta)
    y_new = center.y + dx * math.sin(theta) + dy * math.cos(theta)

    return adsk.core.Point3D.create(x_new, y_new, pt.z)

# Geometry helpers

def get_circle_circum(circle: adsk.fusion.SketchCircle) -> float:

    r = circle.radius
    return 2 * math.pi * r

def get_arc_length_theta(arc_length: float, radius: float) -> float:

    theta = arc_length * 360 / (2 * math.pi * radius)
    return theta

# Script helpers

def get_params(units_manager: adsk.core.UnitsManager) -> list[float | int]:

    # Get electrode radius

    r = get_param_length(units_manager, "Enter the electrode radius r:", "Electrode Radius", "12.5 mm")

    if r is None:
        exit(0)
    
    # Get shield radius

    R = get_param_length(units_manager, "Enter the shield radius R:", "Shield Radius", "18 mm")

    if R is None:
        exit(0)
    
    # Get electrode width

    w = get_param_length(units_manager, "Enter the electrode width w:", "Electrode Width", "3.8 mm")

    if w is None:
        exit(0)

    # Get shield width

    W = get_param_length(units_manager, "Enter the shield width W:", "Shield Width", "5 mm")

    if W is None:
        exit(0)

    # Get electrode height

    h = get_param_length(units_manager, "Enter the electrode height h:", "Electrode Height", "20 mm")

    if h is None:
        exit(0)

    # Get shield height

    H = get_param_length(units_manager, "Enter the shield height H:", "Shield Height", "22.5 mm")

    if H is None:
        exit(0)

    # Get gap length

    t = get_param_length(units_manager, "Enter the gap length t:", "Gap Length", "2.138 mm")

    if H is None:
        exit(0)

    # Get gap quantity

    n = get_param_quantity("Enter the quantity of gaps n:", "Gap Quantity", "6")

    if n is None:
        exit(0)

    return [r, R, w, W, h, H, t, n]

def draw_circle(circles: adsk.fusion.SketchCircles, center: adsk.core.Point3D, radius: float) -> tuple[adsk.fusion.SketchCircle, adsk.fusion.SketchPoint]:

    circle = circles.addByCenterRadius(center, radius)

    # Fix circle at its center
    circle_center = circle.centerSketchPoint
    circle_center.isFixed = True

    return circle, circle_center

def extrude_profiles(extrudes: adsk.fusion.ExtrudeFeatures, profiles: adsk.core.ObjectCollection, distance: float, extrusion_is_sym: bool=True, extrusion_op: adsk.fusion.ExtrudeFeatureInput=adsk.fusion.FeatureOperations.NewBodyFeatureOperation):

    dist = adsk.core.ValueInput.createByReal(distance)

    extrusion = extrudes.createInput(profiles, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    extrusion.setDistanceExtent(extrusion_is_sym, dist)
    extrudes.add(extrusion)

# Main

def run(_context: str):
    
    """This function is called by Fusion when the script is run."""

    try:
        
        design = adsk.fusion.Design.cast(app.activeProduct)
        root_comp = design.rootComponent
        units_manager = design.unitsManager

        # Sketches

        sketches = root_comp.sketches
        xy_plane = root_comp.xYConstructionPlane
        sketch   = sketches.add(xy_plane)

        lines = sketch.sketchCurves.sketchLines
        circles = sketch.sketchCurves.sketchCircles

        points = sketch.sketchPoints
        dims = sketch.sketchDimensions
        geom_cons = sketch.geometricConstraints

        # Bodies

        extrudes = root_comp.features.extrudeFeatures

        # Get Params

        [r, R, w, W, h, H, t, n] = get_params(units_manager)
        
        # Create model 

        center = adsk.core.Point3D.create(0, 0, 0)
        center_sk = points.add(center)

        # Draw circles and get properties
        
        c1, c1_center_sk = draw_circle(circles, center_sk, r)
        c2, _ = draw_circle(circles, center_sk, R)

        c3, c3_center_sk = draw_circle(circles, center_sk, r + w)
        draw_circle(circles, center_sk, R + W)

        c3_circum = get_circle_circum(c3)

        # Draw gap line

        c1_pt = adsk.core.Point3D.create(c1.radius, 0, 0)
        c1_sk = points.add(c1_pt)

        c3_pt = adsk.core.Point3D.create(c3.radius, 0, 0)
        c3_sk = points.add(c3_pt)

        sketch.geometricConstraints.addCoincident(c1_sk, c1)
        sketch.geometricConstraints.addCoincident(c3_sk, c3)

        c1_text_pt = adsk.core.Point3D.create(t, 0, 0)
        c3_text_pt = adsk.core.Point3D.create(t, 0, 0)

        dims.addDistanceDimension(c1_center_sk, c1_sk, adsk.fusion.DimensionOrientations.VerticalDimensionOrientation, c1_text_pt).parameter.value = t / 2
        dims.addDistanceDimension(c3_center_sk, c3_sk, adsk.fusion.DimensionOrientations.VerticalDimensionOrientation, c3_text_pt).parameter.value = t / 2

        l1 = lines.addByTwoPoints(c1_sk, c3_sk)
        l1_length = l1.length

        # Mirror gap line

        rc1_sk = reflect_point(points, c1_sk.geometry, y=True)
        rc3_sk = reflect_point(points, c3_sk.geometry, y=True)
        
        l2 = lines.addByTwoPoints(rc1_sk, rc3_sk)

        # Rotate lines n times

        rotate_entities(geom_cons, center_sk, [l1, l2], n)

        # Draw spruces

        gap_area = t * l1_length

        approx_gap_arc_lengths = n * l1_length
        approx_segment_arc_lengths = c3_circum - approx_gap_arc_lengths

        spruce_half_angle = (get_arc_length_theta(approx_segment_arc_lengths, c3.radius) / n) * 0.25

        for profile in sketch.profiles:

            props = profile.areaProperties()

            area = props.area
            centroid = props.centroid

            x, y = centroid.x, centroid.y
            radius = math.sqrt(x * x + y * y)

            if (gap_area < area) and (r < radius and radius < r + w):
                
                pos_rot1 = rotate_point(centroid, int(spruce_half_angle), center)
                pos_rot2 = pos_rot1

                pos_rot1_sk_pt = points.add(pos_rot1)
                pos_rot2_sk_pt = points.add(pos_rot2)

                geom_cons.addCoincident(pos_rot1_sk_pt, c2)
                geom_cons.addCoincident(pos_rot2_sk_pt, c3)

                neg_rot1 = rotate_point(centroid, -int(spruce_half_angle), center)
                neg_rot2 = neg_rot1

                neg_rot1_sk_pt = points.add(neg_rot1)
                neg_rot2_sk_pt = points.add(neg_rot2)

                geom_cons.addCoincident(neg_rot1_sk_pt, c2)
                geom_cons.addCoincident(neg_rot2_sk_pt, c3)

                l3 = lines.addByTwoPoints(pos_rot1_sk_pt, pos_rot2_sk_pt)
                l4 = lines.addByTwoPoints(neg_rot1_sk_pt, neg_rot2_sk_pt)

                rotate_entities(geom_cons, center_sk, [l3, l4], n)

        # Get spruce area

        min_area = float("inf")
        for profile in sketch.profiles:

            props = profile.areaProperties() 
            
            area = props.area           
            centroid = props.centroid

            x, y = centroid.x, centroid.y
            radius = math.sqrt(x * x + y * y)

            if (r + w < radius and radius < R):
                min_area = min(min_area, area)

        # Extrude spruce and electrode

        profile_collection = adsk.core.ObjectCollection.create()

        for profile in sketch.profiles:

            props = profile.areaProperties() 
            
            area = props.area           
            centroid = props.centroid

            x, y = centroid.x, centroid.y
            radius = math.sqrt(x * x + y * y)

            if (gap_area < area) and (r < radius and radius < r + w):
                profile_collection.add(profile)

            if abs(area - (1 + 1e-5) * min_area) <= 1e-5 and (r + w < radius and radius < R):
                profile_collection.add(profile)
        
        extrude_profiles(extrudes, profile_collection, h)

        # Extrude shield

        shield_profile = None
        max_diag_len = 0
        for profile in sketch.profiles:

            bb = profile.boundingBox
            diag_vec = bb.minPoint.vectorTo(bb.maxPoint)
            diag_len = diag_vec.length 

            if max_diag_len < diag_len:
                shield_profile = profile
                max_diag_len = diag_len
        
        profile_collection = adsk.core.ObjectCollection.create()
        profile_collection.add(shield_profile)

        extrude_profiles(extrudes, profile_collection, H)
        
    except:  #pylint:disable=bare-except
        # Write the error message to the TEXT COMMANDS window.
        ui.messageBox(f'Failed:\n{traceback.format_exc()}')
