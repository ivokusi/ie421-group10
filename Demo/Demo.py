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
        
        paramName = 'Width'
        paramUnit = 'mm'

        paramExpression = 10.0
        paramExpressionString = f'{paramExpression} {paramUnit}'
        paramExpressionReal = adsk.core.ValueInput.createByString(paramExpressionString)

        params = design.userParameters
        param = params.itemByName(paramName)

        if param is not None:
            param.expression = paramExpressionString
        else:
            design.userParameters.add(paramName, paramExpressionReal, paramUnit, "")

    except:  #pylint:disable=bare-except
        # Write the error message to the TEXT COMMANDS window.
        ui.messageBox(f'Failed:\n{traceback.format_exc()}')
