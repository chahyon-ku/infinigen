import bpy
import os
from tqdm import tqdm
from mathutils import Quaternion
import math
import argparse
import sys
import shutil # Import shutil for file operations

# add light at object
def add_light_at_object(obj):
    light_data = bpy.data.lights.new(name=f"{obj.name}", type='POINT')
    light_data.energy = 0.003

    light_obj = bpy.data.objects.new(name=f"{obj.name}", object_data=light_data)
    light_obj.location = obj.location
    light_obj.location.z = obj.location.z - 0.5

    current_quat = obj.rotation_quaternion
    z_flip_quat = Quaternion((0.0, 0.0, 1.0), math.pi)
    new_quat = z_flip_quat @ current_quat
    light_obj.rotation_quaternion = new_quat
    bpy.context.collection.objects.link(light_obj)

# main
def main():
    parser = argparse.ArgumentParser(
        description="Add lights to 'CeilingLightFactory' objects in a Blender scene.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        "--scene_directory",
        type=str,
        help="Path to the directory containing 'scene.blend'."
    )

    args = parser.parse_args()

    dir_scene = args.scene_directory
    original_blend_file = os.path.join(dir_scene, "scene.blend")
    backup_blend_file = os.path.join(dir_scene, "scene_ori.blend")
    modified_blend_file = os.path.join(dir_scene, "scene.blend") # This will be the new scene.blend

    if not os.path.exists(original_blend_file):
        print(f"Error: scene.blend not found at {original_blend_file}")
        sys.exit(1)

    # Step 1: Rename the original scene.blend to scene_ori.blend
    print(f"🔄 Renaming original scene.blend to {backup_blend_file}")
    try:
        shutil.move(original_blend_file, backup_blend_file)
    except Exception as e:
        print(f"Error renaming original scene.blend: {e}")
        sys.exit(1)

    # Now load the renamed original file (which is now scene_ori.blend)
    # Important: We must load the renamed file
    print(f"📂 Loading: {backup_blend_file}")
    bpy.ops.wm.open_mainfile(filepath=backup_blend_file)

    # iterate over all objects
    all_objects = bpy.context.scene.objects
    for obj in tqdm(all_objects):
        # if "CeilingLightFactory" in obj.name or "spawn_asset" in obj.name:
        if "CeilingLightFactory" in obj.name:
            print(f"💡 Processing object: {obj.name}")
            add_light_at_object(obj)

    # Step 2: Save the modified file as the new scene.blend
    print(f"💾 Saving modified scene as: {modified_blend_file}")
    bpy.ops.wm.save_as_mainfile(filepath=modified_blend_file)
    print("✅ Process completed successfully!")

if __name__ == "__main__":
    main()
