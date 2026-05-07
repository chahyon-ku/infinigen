# TODO

Open follow-ups for the whole-house articulated USD export pipeline. Pipeline
overview lives in [docs/simulation/ExportingToSimulators.md](docs/simulation/ExportingToSimulators.md);
authoring entry point is `doors/base.py` → tag, `tools/export.py` → extract,
`scripts/usd_articulated_scene_composer.py` → compose.

## Articulation correctness

### Door panels are not aligned with their doorframes
**Symptom:** in IsaacSim, the door panel (`link_1`) renders inside the room but
visibly offset from the doorframe (`link_0` / `world`). Actuating the hinge
makes the panel sweep through empty space rather than swinging within the
opening.

**Likely causes to investigate, in order:**
1. The hinge joint's `localPos0` / `localPos1` are stored in the asset's local
   frame ([infinigen/core/sim/exporters/usd_exporter.py:217-249](infinigen/core/sim/exporters/usd_exporter.py#L217-L249)),
   but the per-link visual meshes have already been re-centered on their AABB
   centers by `_get_geometry_info` ([usd_exporter.py:586-587](infinigen/core/sim/exporters/usd_exporter.py#L586-L587))
   — `translation = -aabb_center`. Frame and panel get *different* offsets,
   so the joint axis no longer passes through the hinge edge. Removing the
   per-link AABB recenter (or compensating for it in the joint pose) is the
   first thing to try.
2. The frame mesh and panel mesh are written under separate USD Xforms
   (`/Asset/world/visual/door_frame_0` vs `/Asset/link_1/visual/door_left_door_*`).
   If those parent Xforms don't carry the per-link translation that the AABB
   recenter implied, alignment is permanently lost.
3. The standalone (non-scene) export from
   `./scripts/spawn_sim_ready_asset.sh door 1 usd` should be inspected first —
   it's the cleanest reproduction case. If frame and panel are misaligned even
   there, the bug is purely in `usd_exporter.py` and not in our scene pipeline.

### Articulation root anchor under per-instance world transform (untested)
The per-asset USD's `root_joint` is a `PhysicsFixedJoint` with `body0` unset
([usd_exporter.py:159-163](infinigen/core/sim/exporters/usd_exporter.py#L159-L163)),
anchoring `body1` in **world space** at its local-frame `localPos0`. When wrapped
in our `/World/Articulated/<kind>_<idx>` Xform with a translate/rotate, the
geometry visibly moves but the fixed-joint anchor may resolve to `(0,0,0)`
world rather than to the per-instance world pose, which would let doors snap
toward origin under physics.

Currently masked by the alignment bug above; needs verification once panels
align with frames. If reproduced, fix options:
- Have the composer write `localPos0` / `localPos1` of `root_joint` after
  applying the world transform, so the anchor is in scene world space.
- Or replace `PhysicsFixedJoint(body0=None, body1=world)` with applying
  `PhysicsArticulationRootAPI` directly to the `world` rigid body and pinning
  it via `physics:kinematicEnabled = true`. This composes more cleanly under a
  parent Xform.

## Visual diversity

### All doors render with the same appearance despite parameter variation
**Symptom:** in the composed scene, every door instance looks visually
identical — same wood, same panel pattern, same handle finish — even though
the underlying `DoorFactory` / `GlassPanelDoorFactory` / `PanelDoorFactory`
factories produce per-seed variation in geometry and material when spawned
standalone.

**Likely causes:**
1. The articulated USD twin is generated with `seed = next_idx` (a monotonic
   1001+ counter) at [scripts/usd_articulated_asset_exporter.py:13-18](scripts/usd_articulated_asset_exporter.py#L13-L18),
   not with the door's actual factory seed. Material sampling inside
   `SimDoorFactory.sample_joint_parameters` and the texture-bake colors may
   end up keyed on a near-uniform sequence rather than the diverse seeds the
   in-scene doors used.
2. `spawn_simready` baked textures live under
   `<asset_dir>/assets/door_frame_0_DIFFUSE.png` etc. — since each per-asset
   USD has its own `assets/` folder in its bundle directory, the textures
   *should* differ per door. Worth diff-ing two of them as a sanity check
   before chasing the seed angle.
3. The `existing_asset=copydoor` path in `SimDoorFactory.spawn_asset` may be
   ignoring the copy's materials and re-sampling its own — visual variation in
   the source `door_joined` would then be silently discarded.

**First diagnostic step:** `diff` the diffuse textures of two adjacent door
bundles; compare per-asset `metadata.json` for stiffness/damping spread.

## Pipeline coverage

### Extend articulation to remaining `OBJECT_CLASS_MAP` types
Doors are wired up; the same tag-and-extract pattern needs to be replicated
in each factory listed in
[infinigen/assets/sim_objects/mapping.py](infinigen/assets/sim_objects/mapping.py).
Concrete callsites to tag (mirror the doors block at
[infinigen/assets/objects/elements/doors/base.py:1093-1124](infinigen/assets/objects/elements/doors/base.py#L1093-L1124)):
- **Cabinet** — partially wired but commented out at
  [infinigen/assets/objects/shelves/cabinet.py:1952-1955](infinigen/assets/objects/shelves/cabinet.py#L1952-L1955)
  and re-spawned (not copied from existing) at
  [single_cabinet.py:316-317](infinigen/assets/objects/shelves/single_cabinet.py#L316-L317).
  Needs the same `existing_asset=copy` path doors use, plus the snapshot-diff
  cleanup of `bpy.data.objects` after `export_articulated_asset`.
- **Fridge / dishwasher / oven / microwave / window** — find their factory
  classes, identify the `_create_asset` join point analogous to `door_joined`
  in `doors/base.py`, and add the inline export + tagging block.

`tools/export.py:extract_articulated_assets` and the composer are kind-agnostic,
so no changes are needed downstream once the new factories tag themselves.

## Robustness / ergonomics

### Source `sim_exports/usd/<kind>/<idx>/` accumulates indefinitely
The inline exporter keeps writing to a globally shared directory at the repo
root and uses a monotonic `next_idx = 1001+` counter
([scripts/usd_articulated_asset_exporter.py:13-18](scripts/usd_articulated_asset_exporter.py#L13-L18)),
so per-scene generations never collide but disk usage grows without bound and
indices leak the order of past runs. Once the bundling step is the canonical
delivery path (which it is now), the source dir could become a per-scene
`<output_folder>/sim_exports_staging/` that's deleted after the composer runs.
Lower priority — only matters at scale.

### Topology repair was a one-shot fix; remove if no longer needed
[scripts/repair_per_asset_usd_topology.py](scripts/repair_per_asset_usd_topology.py)
was added to repair USDs produced by the buggy `faceVertexCounts` sizing in
`usd_exporter.py`. The source bug is fixed. Once the user confirms no buggy
USDs remain on any machine, this script can be removed.
