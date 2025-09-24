import argparse
import pprint
from pathlib import Path
import os

import gin

from infinigen.core.sim import sim_factory as sf

def export_articulated_door(door_obj):
    asset_type_name = 'door'
    export_format = 'usd'
    export_dir = './sim_exports'
    doors_dir = "/".join([export_dir, export_format, asset_type_name])
    next_idx = max([int(i) for i in os.listdir(doors_dir)])
    export_path, semantic_mapping = sf.spawn_simready(
        name=asset_type_name,
        seed=next_idx,
        exporter=export_format,
        export_dir=Path(export_dir),
        visual_only=True,
        door=door_obj,
    )

    #print(f"Exported to {export_path.resolve()}")
