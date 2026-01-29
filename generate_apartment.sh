for i in $(seq 0 4); do
    python -m infinigen_examples.generate_indoors --seed $i --task coarse --output_folder infinigen_outputs/scene_$i/apartment/coarse_multiroom -g multiroom.gin -p compose_indoors.terrain_enabled=True &&
    mkdir -p infinigen_outputs/scene_$i/omniverse &&
    python -m infinigen.tools.export --input_folder infinigen_outputs/scene_$i/apartment/coarse_multiroom --output_folder infinigen_outputs/scene_$i/omniverse/coarse_multiroom -f usdc -r 1024 --omniverse
done