# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Infinigen is a Python codebase for procedurally generating photorealistic 3D scenes via Blender's `bpy` API. It has three main "modes":

- **Infinigen-Nature** — outdoor/terrain scenes ([infinigen_examples/generate_nature.py](infinigen_examples/generate_nature.py))
- **Infinigen-Indoors** — interior rooms with constraint-based furniture solving ([infinigen_examples/generate_indoors.py](infinigen_examples/generate_indoors.py))
- **Infinigen-Articulated** — articulated simulation-ready assets exported as MJCF/URDF/USD ([scripts/spawn_sim_ready_asset.sh](scripts/spawn_sim_ready_asset.sh), [infinigen/assets/sim_objects/](infinigen/assets/sim_objects/))

Python 3.11 only. Most code runs inside Blender's embedded Python via `bpy==4.2.0` (installed as a pip dep), so it is headless by default.

## Install / Build

```bash
# Dev install (recommended when working in-repo)
pip install -e ".[dev,terrain,vis]"
pre-commit install

# Sim asset extras (mujoco, usd-core, coacd)
pip install -e ".[sim]"
```

Compiled native components live behind Make targets and are only needed for specific features:
- `make terrain` — compiles the CUDA/CPU terrain mesher (needed for full nature scenes)
- `make customgt` — compiles OpenGL ground-truth extractor
- `make flip_fluids` — compiles fluid sim plugin

If you install via the Blender-Python script path instead (`bash scripts/install/interactive_blender.sh`), every `python -m <MODULE> <ARGS>` invocation in the docs must become `python -m infinigen.launch_blender -m <MODULE> -- <ARGS>`.

## Lint / Test

```bash
ruff check .                            # lint (config in pyproject.toml)
ruff check --preview --select CPY001 .  # copyright-header check (CI runs this)
pytest tests --disable-warnings         # full test suite
pytest tests -k 'not skip_for_ci'       # what CI runs
pytest tests/path/to/test_file.py::test_name  # single test
```

CI ([.github/workflows/checks.yml](.github/workflows/checks.yml)) runs ruff + pytest on Python 3.11 with `INFINIGEN_INSTALL_TERRAIN=False` and `INFINIGEN_INSTALL_CUSTOMGT=False`, so anything requiring the compiled terrain/opengl modules must be marked `skip_for_ci` (see [tests/conftest.py](tests/conftest.py) and the registered pytest markers `nature`, `indoors`, `skip_for_ci` in [pyproject.toml](pyproject.toml)).

Each test gets a clean Blender state via the autouse `cleanup` fixture (clears gin config + resets `bpy`).

## Big-picture architecture

### Two-script pipeline

Almost every workflow is the composition of two scripts:

1. **Driver** — `infinigen_examples/generate_{nature,indoors}.py`. Performs scene composition for one seed and one task (`coarse` / `populate` / `fine_terrain` / `render` / `blender_gt` / `opengl_gt`). The driver dispatches by the `--task` flag through [`infinigen.core.execute_tasks`](infinigen/core/execute_tasks.py).
2. **Job manager** — [`infinigen.datagen.manage_jobs`](infinigen/datagen/manage_jobs.py). Spawns the driver many times across seeds and tasks, locally or on SLURM via `submitit`. Outputs land in `outputs/<JOB>/<SEED>/{logs,coarse,fine,frames,...}`.

Driver flags target `--configs` / `-p` (overrides applied inside `generate_*`); manager flags target `--pipeline_configs` / `--pipeline_overrides` (overrides applied to `manage_jobs` itself). Mixing these up is the most common configuration bug.

### Gin config layering

Configuration is [Gin](https://github.com/google/gin-config), not argparse. Every function annotated `@gin.configurable` can have any kwarg overridden from the command line or a `.gin` file.

- Driver configs live in [infinigen_examples/configs_nature/](infinigen_examples/configs_nature/) and [infinigen_examples/configs_indoor/](infinigen_examples/configs_indoor/). `base.gin` / `base_nature.gin` / `base_indoors.gin` is always implicitly loaded; `--configs` files layer on top in left-to-right order.
- Manager configs live in [infinigen/datagen/configs/](infinigen/datagen/configs/) (`compute_platform/local_*.gin` or `slurm.gin`, `data_schema/monocular*|stereo*.gin`, `gt_options/blender_gt.gin|opengl_gt.gin`, `cuda_terrain.gin`).
- Scene-type configs in [infinigen_examples/configs_nature/scene_types/](infinigen_examples/configs_nature/scene_types/) (`desert.gin`, `forest.gin`, ...) encode habitat semantics. Exactly one is expected for nature runs.
- `simple.gin` / `dev.gin` reduce mesh/render quality drastically — without them, scenes assume large RAM/VRAM.

When users want to "turn an asset off" or "change a probability", the lever is almost always `compose_nature.<stage_name>_chance` / `compose_indoors.<stage_name>_enabled`, where `<stage_name>` is the first arg of a `run_stage(...)` call inside `compose_nature` / `compose_indoors`. This is the `RandomStageExecutor` pattern — search for `run_stage(` to find the available toggles.

### Asset factories

3D assets are subclasses of `AssetFactory` in [infinigen/core/placement/factory.py](infinigen/core/placement/factory.py). The contract is `__init__(factory_seed)` (use `FixedSeed` for reproducibility) and `create_asset(**kwargs) -> bpy.types.Object`. Factories live under [infinigen/assets/objects/](infinigen/assets/objects/) (one subfolder per asset family) and [infinigen/assets/sim_objects/](infinigen/assets/sim_objects/) for articulated/sim-exportable variants.

Many assets are partly auto-generated by the **Node Transpiler** ([infinigen/nodes/node_transpiler/](infinigen/nodes/node_transpiler/)), which converts a hand-built Blender geometry/shader nodegraph into a Python file using `NodeWrangler`. This is why many files in `infinigen/assets/` have unusual amounts of unused locals — the per-file ignore for `F841` in [pyproject.toml](pyproject.toml) (`infinigen/assets/*`) is intentional.

### Indoor constraint solver

Indoor furniture placement runs through a constraint-graph solver in [infinigen/core/constraints/](infinigen/core/constraints/) (`example_solver/`, `constraint_language/`, `reasoning/`). Constraints are defined in [infinigen_examples/constraints/](infinigen_examples/constraints/) (notably `home.py` and `semantics.py`). `restrict_solving.*` gin params (parent_rooms, child_primary, child_secondary, consgraph_filters, solve_max_rooms) prune the graph for faster/targeted solves — this is the primary tool for debugging indoor generation. Available room/object tags are enumerated in [infinigen/core/tags.py](infinigen/core/tags.py).

### Terrain

The terrain subsystem ([infinigen/terrain/](infinigen/terrain/)) is a separate compiled pipeline (marching cubes via `OpaqueSphericalMesher` / `TransparentSphericalMesher` or `OcMesher`) with optional CUDA acceleration. Anything terrain-related is gated behind `compose_*.terrain_enabled` and the optional `[terrain]` install extra. `OcMesher` is a git submodule under [infinigen/OcMesher](infinigen/OcMesher) — `git submodule update` if it appears empty.

### Excluded from ruff/typing

[infinigen/datagen/customgt/dependencies/](infinigen/datagen/customgt/dependencies/), `infinigen/OcMesher`, `infinigen/infinigen_gpl`, and the `mesh_to_sdf` / `marching_cubes_lewiner` directories are vendored externals — do not lint, edit, or restructure them as part of unrelated work.

## Common entry points

```bash
# Single-step nature generation (each step writes/reads a folder)
python -m infinigen_examples.generate_nature --seed 0 --task coarse \
    -g desert.gin simple.gin --output_folder outputs/hello_world/coarse

# One-command full pipeline
python -m infinigen.datagen.manage_jobs --output_folder outputs/hello_world \
    --num_scenes 1 --specific_seed 0 \
    --configs desert.gin simple.gin \
    --pipeline_configs local_16GB.gin monocular.gin blender_gt.gin \
    --pipeline_overrides LocalScheduleHandler.use_gpu=False

# Indoor single room
python -m infinigen_examples.generate_indoors --seed 0 --task coarse \
    --output_folder outputs/indoors/coarse \
    -g fast_solve.gin singleroom.gin \
    -p compose_indoors.terrain_enabled=False \
       restrict_solving.restrict_parent_rooms=\[\"DiningRoom\"\]

# Open a generated scene in Blender UI
python -m infinigen.launch_blender outputs/.../scene.blend

# Spawn N articulated sim-ready assets
./scripts/spawn_sim_ready_asset.sh door 10 mjcf   # also: urdf, usd

# Export an indoor scene to USD for IsaacSim
python -m infinigen.tools.export --input_folder outputs/indoors/coarse \
    --output_folder outputs/my_export -f usdc -r 1024 --omniverse
```

When scenes crash, logs are at `outputs/<JOB>/<SEED>/logs/<TASK>.log` and `.err` — always check these before guessing. Reproduce with `--debug` for full verbosity.

## Conventions worth knowing

- `from infinigen.X import Y` — relative imports across packages are banned (`ban-relative-imports = "parents"` in ruff config); siblings only.
- `# ruff: noqa: E402` appears at the top of driver scripts because `logging.basicConfig` must run before any module-level imports that log.
- Drivers contain large `# unused imports required for gin to find modules` blocks — gin resolves `@gin.configurable` references by import path, so removing an "unused" import can silently break config files that reference functions from that module.
- New Python files in the repo need a copyright header (CI's `CPY001` check will fail otherwise). `__init__.py` files are exempt.
- Reproducibility wraps randomness in `with FixedSeed(seed):` from [infinigen/core/util/math.py](infinigen/core/util/math.py).
