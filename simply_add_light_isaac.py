import omni.usd
from pxr import UsdGeom, UsdLux, Sdf, Gf
from omni.isaac.core.simulation_context import SimulationContext
from omni.isaac.core.utils.prims import get_prim_at_path
import os
import carb

# Function to add a light at a specific USD prim's location
def add_light_at_prim_location(stage, target_prim):
    """
    Adds a sphere light at the world-space location of a given USD prim.

    Args:
        stage (Usd.Stage): The USD stage to add the light to.
        target_prim (Usd.Prim): The prim whose location will be used for the light.
    """
    prim_path = target_prim.GetPath()
    light_name = f"Light_{prim_path.GetName()}"
    light_prim_path = prim_path.GetParentPath().AppendChild(light_name) # Place light next to the original prim

    # Get the world transform of the target prim
    # UsdGeom.Xformable is used to query transform properties
    xform_prim = UsdGeom.Xformable(target_prim)
    world_transform = xform_prim.ComputeLocalToWorldTransform(Usd.TimeCode.Default())
    light_location = world_transform.ExtractTranslation()

    print(f"💡 Adding light '{light_prim_path}' at location: {light_location}")

    # Define a Sphere Light (similar to Blender's POINT light)
    sphere_light = UsdLux.SphereLight.Define(stage, light_prim_path)
    sphere_light.CreateIntensityAttr(10000.0) # Adjust intensity as needed (higher for USD than Blender)
    sphere_light.CreateRadiusAttr(0.2)       # Size of the light source
    sphere_light.CreateColorAttr(Gf.Vec3f(1.0, 1.0, 1.0)) # White light

    # Set the translation of the light prim
    # UsdGeom.XformCommonAPI provides a simpler way to set common transforms
    xform_common_api = UsdGeom.XformCommonAPI(sphere_light.GetPrim())
    xform_common_api.SetTranslate(Gf.Vec3d(light_location[0], light_location[1], light_location[2]))

# Main program entry for Isaac Sim
def main():
    # --- Configuration ---
    # Make sure this path is accessible by Isaac Sim.
    # For local files, it should be a full path like /home/user/my_scene.usdc
    # For Nucleus files, it should start with omniverse://localhost/...
    input_usdc_path = "/home/projects/infinigen_outputs/coarse_fast_lighting_2/omniverse/coarse/export_scene.blend/export_scene.usdc"  
    output_usdc_path = "/home/projects/infinigen_outputs/coarse_fast_lighting_2/omniverse/coarse/export_scene.blend/export_scene_with_lights.usdc"
    # input_usdc_path = "/path/to/your/input_scene.usdc" # <-- IMPORTANT: REPLACE WITH YOUR USDC FILE PATH
    # output_usdc_path = "/path/to/your/output_scene_with_lights.usdc" # <-- IMPORTANT: REPLACE WITH DESIRED OUTPUT PATH

    # Initialize Isaac Sim
    simulation_context = SimulationContext()
    # Check if a stage is already open, if so, clear it.
    if simulation_context.is_initialized() and simulation_context.stage is not None:
        simulation_context.stop()
        simulation_context.clear()
    
    simulation_context.initialize()
    stage = simulation_context.stage

    print(f"📂 Loading: {input_usdc_path}")

    # Load the specified .usdc file
    # This will load the USD content into the current stage
    if os.path.exists(input_usdc_path) or input_usdc_path.startswith("omniverse://"):
        stage.Load(input_usdc_path)
        print("USD file loaded successfully.")
    else:
        print(f"Error: Input USDC file not found or invalid path: {input_usdc_path}")
        print("Creating an empty stage to proceed with adding lights for demonstration.")
        # Optionally, create a new stage if the input path is bad
        # stage.DefinePrim(Sdf.Path("/World"), "Xform") # Add a default /World prim
        # Save this empty stage if you want to see just the lights
        # stage.GetRootLayer().SaveAs(output_usdc_path)
        # return # Exit if you can't load the base scene
        
    # Set up some default lighting if the scene is empty (optional)
    # You might want to remove default lights if they interfere with your custom lights
    UsdLux.DomeLight.Define(stage, Sdf.Path("/World/defaultDomeLight")).CreateIntensityAttr(500.0)
    
    # Iterate through all prims on the stage
    # stage.Traverse() yields all prims recursively
    found_any_target = False
    for prim in stage.Traverse():
        # Check if the prim is a model or a component that might represent a light fixture
        prim_name = prim.GetPath().GetName()
        prim_type = prim.GetTypeName() # UsdGeom.Xform, UsdGeom.Mesh, etc.

        # You might need to refine these conditions based on your actual USDC file's structure.
        # For example, check if it's a UsdGeom.Xformable or UsdGeom.Mesh that represents a light fixture.
        if "CeilingLightFactory" in prim_name or "spawn_asset" in prim_name:
            # Ensure it's a prim that has a transform (e.g., not just an attribute prim)
            if UsdGeom.Xformable(prim):
                print(f"💡 Processing prim: {prim_path} (Type: {prim_type})")
                add_light_at_prim_location(stage, prim)
                found_any_target = True

    if not found_any_target:
        print("No target prims ('CeilingLightFactory' or 'spawn_asset') found in the USD scene.")

    # Save the modified USDC stage
    stage.GetRootLayer().SaveAs(output_usdc_path)
    print(f"💾 Modified USDC saved to: {output_usdc_path}")

    # Run simulation (optional, if you want to visualize immediately)
    print("Starting Isaac Sim to display the scene...")
    simulation_context.play()
    
    # Keep the simulation running until closed manually or by code
    # This is important in a standalone script to keep the Sim window open
    carb.app.get_app().run_until_closed()

    simulation_context.stop()
    simulation_context.clear()
    print("Isaac Sim closed.")

if __name__ == "__main__":
    main()
