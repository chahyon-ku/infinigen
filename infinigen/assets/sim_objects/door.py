# Copyright (C) 2024, Princeton University.
# This source code is licensed under the BSD 3-Clause license found in the LICENSE file in the root directory of this source tree.

# Authors: Lingjie Mei
import bpy
import gin
import numpy as np
from numpy.random import uniform

from infinigen.core.placement.factory import AssetFactory
from infinigen.core.util.math import FixedSeed


def random_door_factory():
    from infinigen.assets.objects.elements.doors.panel import PanelDoorFactory
    door_factories = [
        PanelDoorFactory,
        # TODO(anton): -- some of the import were causing issues so I just removed them... we need to bring them back in order to preserve the ability to just generate any random door .usd asset in the future.
        # GlassPanelDoorFactory,
        # LouverDoorFactory,
        # LiteDoorFactory,
    ]
    # This should be getting a random door factory from a random class so bring it back here.
    # door_probs = np.array([4, 2, 3, 3])
    # return np.random.choice(door_factories, p=door_probs / door_probs.sum())

    return PanelDoorFactory


class SimDoorFactory(AssetFactory):
    def __init__(self, factory_seed, coarse=False, constants=None):
        super(SimDoorFactory, self).__init__(factory_seed, coarse)
        with FixedSeed(self.factory_seed):
            self.base_factory = random_door_factory()(factory_seed, coarse, constants)

    @classmethod
    @gin.configurable(module="SimDoorFactory")
    def sample_joint_parameters(
        cls,
        door_hinge_stiffness_min: float = 0.0,
        door_hinge_stiffness_max: float = 0.0,
        door_hinge_damping_min: float = 0.0,
        door_hinge_damping_max: float = 10.0,
        door_handle_stiffness_min: float = 2.0,
        door_handle_stiffness_max: float = 7.0,
        door_handle_damping_min: float = 1.0,
        door_handle_damping_max: float = 3.0,
    ):
        return {
            "door_hinge": {
                "stiffness": uniform(
                    door_hinge_stiffness_min, door_hinge_stiffness_max
                ),
                "damping": uniform(door_hinge_damping_min, door_hinge_damping_max),
            },
            "door_handle": {
                "stiffness": uniform(
                    door_handle_stiffness_min, door_handle_stiffness_max
                ),
                "damping": uniform(door_handle_damping_min, door_handle_damping_max),
            },
        }

    def create_asset(self, **params) -> bpy.types.Object:
        # We are generating an articulated door, this means we should not spawn a new object, but rather make the passed-in door object articulated.
        if 'door' in params:
            door = params['door']
            return door
        return self.base_factory.create_asset(apply=False, **params)

    def finalize_assets(self, assets):
        self.base_factory.finalize_assets(assets)
