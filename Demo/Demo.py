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
        
        # Prompt the user for a string and validate it's valid.
        isValid = False
        input = '1 in'  # The initial default value.
        
        while not isValid:
            # Get a string from the user.
            retVals = ui.inputBox('Enter a distance', 'Distance', input)
            if retVals[0]:
                (input, isCancelled) = retVals
            
            # Exit the program if the dialog was cancelled.
            if isCancelled:
                return
            
            # Check that a valid length description was entered.
            unitsMgr = design.unitsManager
            try:
                realValue = unitsMgr.evaluateExpression(input, unitsMgr.defaultLengthUnits)
                isValid = True
            except:
                # Invalid expression so display an error and set the flag to allow them
                # to enter a value again.
                ui.messageBox('"' + input + '" is not a valid length expression.', 'Invalid entry', 
                              adsk.core.MessageBoxButtonTypes.OKButtonType, 
                              adsk.core.MessageBoxIconTypes.CriticalIconType)
                isValid = False
        
        # Use the value for something.
        ui.messageBox('input: ' + input + ', result: ' + str(realValue))

    except:  #pylint:disable=bare-except
        # Write the error message to the TEXT COMMANDS window.
        ui.messageBox(f'Failed:\n{traceback.format_exc()}')
