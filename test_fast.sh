for i in $(seq 0 1); do
    CUDA_VISIBLE_DEVICES=1 python -m infinigen_examples.generate_indoors --seed $i --task coarse --output_folder outputs/indoors/coarse_fast_lighting_modified_ceilclass_$i -g fast_solve.gin base_indoors.gin -p compose_indoors.terrain_enabled=False
    mkdir -p /home/projects/infinigen_outputs/coarse_fast_lighting_modified_ceilclass_$i/omniverse
    python -m infinigen.tools.export --input_folder outputs/indoors/coarse_fast_lighting_modified_ceilclass_$i --output_folder /home/projects/infinigen_outputs/coarse_fast_lighting_modified_ceilclass_$i/omniverse/coarse -f usdc -r 1024 --omniverse
done