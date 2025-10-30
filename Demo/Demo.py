"""This file acts as the main module for this script."""

import traceback
import adsk.core
import adsk.fusion
# import adsk.cam

import math

# Initialize the global variables for the Application and UserInterface objects.
app = adsk.core.Application.get()
ui  = app.userInterface

def degToRad(deg: float) -> float:
    return deg * math.pi / 180

def run(_context: str):
    """This function is called by Fusion when the script is run."""

    try:
        
        # design = adsk.fusion.Design.cast(app.activeProduct)
        # rootComp = design.rootComponent

        if app.activeEditObject.objectType != adsk.fusion.Sketch.classType():
            ui.messageBox("Please select a sketch to continue.")
            return
            
        # sketch: adsk.fusion.Sketch = app.activeEditObject
        sketch = adsk.fusion.Sketch.cast(app.activeEditObject)
        
        sketchLines = sketch.sketchCurves.sketchLines
        sketchArcs = sketch.sketchCurves.sketchArcs
        sketchCircles = sketch.sketchCurves.sketchCircles

        posArr = [0, 1, 2, 3, 4, 5]
        xArr = [0, 0.225, 0.55, 0.55, 0.31, 0.31, 0.85]
        yArr = [0.31, 0.31, 0.635, 0.85, 0.85, 1.0, 1.0]

        # Q1

        for i in posArr:
            
            startPoint = adsk.core.Point3D.create(xArr[i], yArr[i], 0)
            endPoint = adsk.core.Point3D.create(xArr[i+1], yArr[i+1], 0)
            
            sketchLines.addByTwoPoints(startPoint, endPoint)
        
        arcStart = adsk.core.Point3D.create(0.85, 1.0, 0)
        arcCenter = adsk.core.Point3D.create(0.85, 0.85, 0)
        sketchArcs.addByCenterStartSweep(arcCenter, arcStart, degToRad(-90))

        for i in posArr:
            
            startPoint = adsk.core.Point3D.create(yArr[i], xArr[i], 0)
            endPoint = adsk.core.Point3D.create(yArr[i+1], xArr[i+1], 0)
            
            sketchLines.addByTwoPoints(startPoint, endPoint)

        # Q2

        for i in posArr:
            
            startPoint = adsk.core.Point3D.create(-xArr[i], yArr[i], 0)
            endPoint = adsk.core.Point3D.create(-xArr[i+1], yArr[i+1], 0)
            
            sketchLines.addByTwoPoints(startPoint, endPoint)
        
        arcStart = adsk.core.Point3D.create(-1.0, 0.85, 0)
        arcCenter = adsk.core.Point3D.create(-0.85, 0.85, 0)
        sketchArcs.addByCenterStartSweep(arcCenter, arcStart, degToRad(-90))

        for i in posArr:
            
            startPoint = adsk.core.Point3D.create(-yArr[i], xArr[i], 0)
            endPoint = adsk.core.Point3D.create(-yArr[i+1], xArr[i+1], 0)
            
            sketchLines.addByTwoPoints(startPoint, endPoint)

        # Q3

        for i in posArr:
            
            startPoint = adsk.core.Point3D.create(-xArr[i], -yArr[i], 0)
            endPoint = adsk.core.Point3D.create(-xArr[i+1], -yArr[i+1], 0)
            
            sketchLines.addByTwoPoints(startPoint, endPoint)
        
        arcStart = adsk.core.Point3D.create(-0.85, -1.0, 0)
        arcCenter = adsk.core.Point3D.create(-0.85, -0.85, 0)
        sketchArcs.addByCenterStartSweep(arcCenter, arcStart, degToRad(-90))

        for i in posArr:
            
            startPoint = adsk.core.Point3D.create(-yArr[i], -xArr[i], 0)
            endPoint = adsk.core.Point3D.create(-yArr[i+1], -xArr[i+1], 0)
            
            sketchLines.addByTwoPoints(startPoint, endPoint)

        # Q4

        for i in posArr:
            
            startPoint = adsk.core.Point3D.create(xArr[i], -yArr[i], 0)
            endPoint = adsk.core.Point3D.create(xArr[i+1], -yArr[i+1], 0)
            
            sketchLines.addByTwoPoints(startPoint, endPoint)
        
        arcStart = adsk.core.Point3D.create(1.0, -0.85, 0)
        arcCenter = adsk.core.Point3D.create(0.85, -0.85, 0)
        sketchArcs.addByCenterStartSweep(arcCenter, arcStart, degToRad(-90))

        for i in posArr:
            
            startPoint = adsk.core.Point3D.create(yArr[i], -xArr[i], 0)
            endPoint = adsk.core.Point3D.create(yArr[i+1], -xArr[i+1], 0)
            
            sketchLines.addByTwoPoints(startPoint, endPoint)

        circleCenter = adsk.core.Point3D.create(0, 0, 0)
        circleRadius = 0.25
        sketchCircles.addByCenterRadius(circleCenter, circleRadius)

    except:  #pylint:disable=bare-except
        # Write the error message to the TEXT COMMANDS window.
        ui.messageBox(f'Failed:\n{traceback.format_exc()}')
