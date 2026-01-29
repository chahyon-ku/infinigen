# 1. Generate the scene, this step we get the scene.blend file
python -m infinigen_examples.generate_indoors --seed $i --task coarse --output_folder $output_folder -g fast_solve.gin base_indoors.gin -p compose_indoors.terrain_enabled=False


# 2. Add light at CeilingLightFactory (blender), this step we get the scene_modified.blend file 
python simply_add_light.py --scene_directory $output_folder

# 3. Export the scene
mkdir -p $output_folder/omniverse
python -m infinigen.tools.export --input_folder $output_folder --output_folder $output_folder/omniverse/coarse -f usdc -r 1024 --omniverse

# Notes:
# 1. If the light is too bright, you can adjust the energy and wattage in the export.py and simply_add_light.py
# 2. If the light location is not correct, you can adjust the location in the simply_add_light.py