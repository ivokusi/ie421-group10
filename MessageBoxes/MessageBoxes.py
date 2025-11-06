"""This file acts as the main module for this script."""

import traceback
import adsk.core # type: ignore
import adsk.fusion # type: ignore
# import adsk.cam

# Initialize the global variables for the Application and UserInterface objects.
app = adsk.core.Application.get()
ui  = app.userInterface


def run(_context: str):
    """This function is called by Fusion when the script is run."""

    try:

        OKButtonPress = ui.messageBox("OKCancelButtonType", "OK Cancel Button", 1, 2)

        if OKButtonPress == 0:
            ui.messageBox("OK Button Pressed")
            return
        
        ui.messageBox("Cancel Button Pressed")

    except:  #pylint:disable=bare-except
        # Write the error message to the TEXT COMMANDS window.
        ui.messageBox(f'Failed:\n{traceback.format_exc()}')
