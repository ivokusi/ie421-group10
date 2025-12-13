"""This file acts as the main module for this script."""

import traceback
import math
import adsk.core
import adsk.fusion

# Initialize the global variables for the Application and UserInterface objects.
app = adsk.core.Application.get()
ui  = app.userInterface

def run(_context: str):
    """This function is called by Fusion when the script is run."""
    try:
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            ui.messageBox("A Fusion 360 design must be active to run this script.")
            return

        rootComp = design.rootComponent

        # 1) Get user inputs: outer radius (R), height (H), hole radius (r), hole depth (D)
        # Use a single input box that asks for four numbers, separated by commas.
        # If you prefer separate dialogs, you can implement four sequential inputBox calls.
        defaultVals = "5.0, 2.0, 2.0, 2.0"  # R, H, r, D in cm (example)
        inputBoxResult = ui.inputBox("Enter: outerRadius, height, holeRadius, holeDepth (cm), e.g. 5, 2, 2, 2", "Nut Parameters", defaultVals)
        if not inputBoxResult[0]:
            return  # User canceled
        vals = inputBoxResult[0].split(",")
        if len(vals) != 4:
            ui.messageBox("Please provide four comma-separated values: outerRadius, height, holeRadius, holeDepth.")
            return

        R = float(vals[0].strip())
        H = float(vals[1].strip())
        r = float(vals[2].strip())
        D = float(vals[3].strip())

        # 2) Create a new component for the nut
        newOcc = rootComp.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        nutComp = adsk.fusion.Component.cast(newOcc.component)
        nutComp.name = "Hex Nut"

        # 3) Create a sketch on the XY plane for the hexagon (centered at origin)
        sketches = nutComp.sketches
        xyPlane = nutComp.xYConstructionPlane
        hexSketch = sketches.add(xyPlane)

        # 4) Compute hexagon vertices for a regular hexagon with circumradius R
        # Vertex angles: 0, 60, 120, 180, 240, 300 degrees
        pts = []
        for i in range(6):
            angle = math.radians(60 * i)
            x = R * math.cos(angle)
            y = R * math.sin(angle)
            pts.append(adsk.core.Point3D.create(x, y, 0))
        # Create hexagon edges by connecting consecutive points
        lines = hexSketch.sketchCurves.sketchLines
        for i in range(6):
            p1 = pts[i]
            p2 = pts[(i + 1) % 6]
            lines.addByTwoPoints(p1, p2)

        # 5) Create an extrude to the nut height H
        prof = hexSketch.profiles.item(0)
        extrudes = nutComp.features.extrudeFeatures
        
        extInput = extrudes.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        distance = adsk.core.ValueInput.createByReal(H)
        extInput.setDistanceExtent(False, distance)  # distance-based
        ext = extrudes.add(extInput)

        # 6) Create a through-hole (cylinder) in the nut
        # Create a hole sketch directly on the top face of the extrusion
        topFace = ext.endFaces[0]
        holeSketch = nutComp.sketches.add(topFace)

        # Center for the hole is at origin (0, 0, 0) projected onto the top face
        circle_hole = holeSketch.sketchCurves.sketchCircles
        circle = circle_hole.addByCenterRadius(adsk.core.Point3D.create(0, 0, 0), r)
        holeProf = holeSketch.profiles.item(1)  # profile should be a circle with diameter = 2*r

        extInput = extrudes.createInput(holeProf, adsk.fusion.FeatureOperations.CutFeatureOperation)
        distance = adsk.core.ValueInput.createByReal(-D)
        extInput.setDistanceExtent(False, distance)  # distance-based
        ext = extrudes.add(extInput)

        ui.messageBox("Hex nut with through-hole created successfully.")
    except Exception as ex:  #pylint:disable=bare-except
        ui.messageBox(f"Failed:\n{traceback.format_exc()}")