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

def get_param_length(design: adsk.fusion.Design, prompt: str, title: str, default: str) -> None | float:

    units_manager = design.unitsManager

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

def reflect_point(pt, x=False, y=False, z=False):

    new_pt = adsk.core.Point3D.create((-1) ** x * pt.x, (-1) ** y * pt.y, (-1) ** z * pt.z)
    return new_pt

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

# Main

def run(_context: str):
    
    """This function is called by Fusion when the script is run."""

    try:
        
        design = adsk.fusion.Design.cast(app.activeProduct)
        root_comp = design.rootComponent

        extrudes = root_comp.features.extrudeFeatures

        sketches = root_comp.sketches
        xy_plane = root_comp.xYConstructionPlane
        sketch   = sketches.add(xy_plane)

        lines = sketch.sketchCurves.sketchLines
        circles = sketch.sketchCurves.sketchCircles

        points = sketch.sketchPoints
        dims = sketch.sketchDimensions
        geom_cons = sketch.geometricConstraints

        center = adsk.core.Point3D.create(0, 0, 0)
        center_sk_pt = points.add(center)

        # Get electrode inner circle radius

        r = get_param_length(design, "Enter the electrode inner circle radius r:", "Electrode Inner Circle Radius", "12.5 mm")
        
        if r is None:
            return

        # Get shield radius

        R = get_param_length(design, "Enter the shield radius R:", "Shield Radius", "18 mm")
        
        if R is None:
            return

        # Get electrode width

        w = get_param_length(design, "Enter the electrode width w:", "Electrode Width", "3.8 mm")

        if w is None:
            return

        # Get shield width

        W = get_param_length(design, "Enter the shield width W:", "Shield Width", "5 mm")

        if W is None:
            return

        # Get gap length

        t = get_param_length(design, "Enter the gap length t:", "Gap Length", "2.138 mm")

        if t is None:
            return

        # Get gap quantity

        n = get_param_quantity("Enter the quantity of gaps n:", "Gap Quantity", "6")

        if n is None:
            return

        # Create model based on constraints
        
        c1 = circles.addByCenterRadius(center, r)
        c1_center_pt = c1.centerSketchPoint
        c1_center_pt.isFixed = True

        c2 = circles.addByCenterRadius(center, R)
        c2_center_pt = c2.centerSketchPoint
        c2_center_pt.isFixed = True

        c3 = circles.addByCenterRadius(center, r + w) # + offset w
        c3_circum = 2 * math.pi * (r + w)

        c3_center_pt = c3.centerSketchPoint
        c3_center_pt.isFixed = True 

        c4 = circles.addByCenterRadius(center, R + W) # + offset w
        c4_center_pt = c4.centerSketchPoint
        c4_center_pt.isFixed = True 

        # Add guess pts

        c1_guess = adsk.core.Point3D.create(r, 0, 0)
        c1_sk_pt = points.add(c1_guess)

        c3_guess = adsk.core.Point3D.create(r + w, 0, 0)
        c3_sk_pt = points.add(c3_guess)

        # Add coincident constraint to guess pts

        sketch.geometricConstraints.addCoincident(c1_sk_pt, c1)
        sketch.geometricConstraints.addCoincident(c3_sk_pt, c3)

        c1_text_pt = adsk.core.Point3D.create(t, 0, 0)
        c3_text_pt = adsk.core.Point3D.create(t, 0, 0)

        # Set gap pts

        dims.addDistanceDimension(c1_center_pt, c1_sk_pt, adsk.fusion.DimensionOrientations.VerticalDimensionOrientation, c1_text_pt).parameter.value = t / 2
        dims.addDistanceDimension(c3_center_pt, c3_sk_pt, adsk.fusion.DimensionOrientations.VerticalDimensionOrientation, c3_text_pt).parameter.value = t / 2

        # Add line between gap pts

        l1 = lines.addByTwoPoints(c1_sk_pt, c3_sk_pt)
        l1_length = l1.length

        # mirror line

        rc1_sk_pt = reflect_point(c1_sk_pt.geometry, y=True)
        rc3_sk_pt = reflect_point(c3_sk_pt.geometry, y=True)
        l2 = lines.addByTwoPoints(rc1_sk_pt, rc3_sk_pt)

        # rotate lines

        rotate_entities(geom_cons, center_sk_pt, [l1, l2], n)

        # Find segment

        gap_area = t * l1_length
        segment_deg = ((c3_circum - n * l1_length) / (2 * math.pi * (r + w)) * 360) / n * 0.25

        for profile in sketch.profiles:

            props = profile.areaProperties()

            area = props.area
            centroid = props.centroid

            x, y = centroid.x, centroid.y
            radius = math.sqrt(x * x + y * y)

            if (gap_area < area) and (r < radius and radius < r + w):
                
                pos_rot1 = rotate_point(centroid, int(segment_deg), center)
                pos_rot2 = pos_rot1

                neg_rot1 = rotate_point(centroid, -int(segment_deg), center)
                neg_rot2 = neg_rot1
                
                pos_rot1_sk_pt = points.add(pos_rot1)
                pos_rot2_sk_pt = points.add(pos_rot2)

                sketch.geometricConstraints.addCoincident(pos_rot1_sk_pt, c2)
                sketch.geometricConstraints.addCoincident(pos_rot2_sk_pt, c3)

                neg_rot1_sk_pt = points.add(neg_rot1)
                neg_rot2_sk_pt = points.add(neg_rot2)

                sketch.geometricConstraints.addCoincident(neg_rot1_sk_pt, c2)
                sketch.geometricConstraints.addCoincident(neg_rot2_sk_pt, c3)

                l3 = lines.addByTwoPoints(pos_rot1_sk_pt, pos_rot2_sk_pt)
                l4 = lines.addByTwoPoints(neg_rot1_sk_pt, neg_rot2_sk_pt)

                rotate_entities(geom_cons, center_sk_pt, [l3, l4], n)

        min_area = float("inf")
        for profile in sketch.profiles:

            props = profile.areaProperties() 
            
            area = props.area           
            centroid = props.centroid

            x, y = centroid.x, centroid.y
            radius = math.sqrt(x * x + y * y)

            if (r + w < radius and radius < R):
                # ui.messageBox(area)
                min_area = min(min_area, area)

        profile_collection = adsk.core.ObjectCollection.create()
        
        for profile in sketch.profiles:

            props = profile.areaProperties()

            area = props.area
            centroid = props.centroid

            x, y = centroid.x, centroid.y
            radius = math.sqrt(x * x + y * y)

            if (gap_area < area) and (r < radius and radius < r + w):
                profile_collection.add(profile)

        for profile in sketch.profiles:

            props = profile.areaProperties() 
            
            area = props.area           
            centroid = props.centroid

            x, y = centroid.x, centroid.y
            radius = math.sqrt(x * x + y * y)

            if abs(area - (1 + 1e-5) * min_area) <= 1e-5 and (r + w < radius and radius < R):
                profile_collection.add(profile)

        distance = adsk.core.ValueInput.createByReal(2)
        
        ext_input = extrudes.createInput(profile_collection, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        ext_input.setDistanceExtent(True, distance)

        extrudes.add(ext_input)

        distance = adsk.core.ValueInput.createByReal(2.5)

        wanted_profile = None
        max_area = 0

        for profile in sketch.profiles:

            props = profile.areaProperties()

            area = props.area
            centroid = props.centroid

            x, y = centroid.x, centroid.y   

            if abs(x) <= 1e-5 and abs(y) <= 1e-5 and max_area < area:
                wanted_profile = profile
                max_area = area

        distance = adsk.core.ValueInput.createByReal(2.25)
        
        profile_collection = adsk.core.ObjectCollection.create()
        profile_collection.add(wanted_profile)

        ext_input = extrudes.createInput(profile_collection, adsk.fusion.FeatureOperations.JoinFeatureOperation)
        ext_input.setDistanceExtent(True, distance)

        extrudes.add(ext_input)
        
    except:  #pylint:disable=bare-except
        # Write the error message to the TEXT COMMANDS window.
        ui.messageBox(f'Failed:\n{traceback.format_exc()}')
