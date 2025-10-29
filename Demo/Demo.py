"""This file acts as the main module for this script."""

import traceback
import adsk.core
import adsk.fusion
# import adsk.cam

# Initialize the global variables for the Application and UserInterface objects.
app = adsk.core.Application.get()
ui  = app.userInterface

def run(_context: str):
    """This function is called by Fusion when the script is run."""

    try:
        
        design = adsk.fusion.Design.cast(app.activeProduct)
        
        rootComp = design.rootComponent
        
        sketches = rootComp.sketches
        xyPlane = rootComp.xYConstructionPlane
        
        sketch = sketches.add(xyPlane)
        
        sketchLines = sketch.sketchCurves.sketchLines
        startPoint = adsk.core.Point3D.create(0, 0, 0)
        endPoint = adsk.core.Point3D.create(5, 5, 0)

        sketchLines.addCenterPointRectangle(startPoint, endPoint)
        sketchLines.addByTwoPoints(startPoint, endPoint)

    except:  #pylint:disable=bare-except
        # Write the error message to the TEXT COMMANDS window.
        ui.messageBox(f'Failed:\n{traceback.format_exc()}')
