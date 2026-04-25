import openmc4d as mc
from .registry import register_tally, OpenMCTally


@register_tally("global-score")
class GlobalScore(OpenMCTally):

    name = "global-score"

    default_config = {
        "score": "flux",
        "cells": None,
        "materials": None
    }

    def build(self):

        cfg = self.cfg
        score = cfg["score"]
        cell_bins = cfg.get("cells")
        material_inputs = cfg.get("materials")

        filters = []

        if cell_bins is not None:
            filters.append(mc.CellFilter(cell_bins))

        if material_inputs is not None:

            if not isinstance(material_inputs, list):
                material_inputs = [material_inputs]

            materials = list(self.model.materials)

            id_map = {m.id: m for m in materials}
            name_map = {m.name: m for m in materials}

            selected_materials = []

            for m in material_inputs:

                # -------------------------
                # Resolve model parameter
                # -------------------------

                if isinstance(m, str) and m in self.model.parameters:
                    m = self.model.parameters[m]

                # -------------------------
                # Resolve material id
                # -------------------------

                if isinstance(m, int):

                    if m not in id_map:
                        raise ValueError(
                            f"Material id {m} not found. "
                            f"Available ids: {list(id_map.keys())}"
                        )

                    selected_materials.append(id_map[m])
                    continue

                # -------------------------
                # Resolve material name
                # -------------------------

                if isinstance(m, str):

                    if m not in name_map:
                        raise ValueError(
                            f"Material '{m}' not found. "
                            f"Available names: {list(name_map.keys())}"
                        )

                    selected_materials.append(name_map[m])
                    continue

                raise TypeError(
                    f"Material specifier must resolve to name or id, got {type(m)}"
                )

            filters.append(mc.MaterialFilter(selected_materials))

        t = mc.Tally(name=self.name)
        t.scores = [score]

        if filters:
            t.filters = filters

        return [t]

    def _extract(self, statepoint):

        tally = statepoint.get_tally(name=self.name)
        ds = self._to_xarray(tally)
        return ds