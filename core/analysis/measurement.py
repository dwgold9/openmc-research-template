from pathlib import Path
import openmc4d as mc
import xarray as xr

from enum import Enum, auto

class Scope(Enum):
    MEMBER = auto()
    CASE = auto()
    STUDY = auto()

class Measurement:
    """
    Represents a single extracted measurement.

    Wraps an xarray.Dataset that follows the canonical schema:
        - data_vars:
            mean     (required)
            std_dev  (optional)
    """

    def __init__(self, dataset: xr.Dataset, tags=None):

        if not isinstance(dataset, xr.Dataset):
            raise TypeError(
                f"Measurement expects xr.Dataset, got {type(dataset)}"
            )

        if "mean" not in dataset.data_vars:
            raise ValueError(
                "Measurement dataset must contain 'mean' variable."
            )

        self._ds = dataset
        self.tags = tags or {}

    # ------------------------------------------------------------------
    # Core Data Access
    # ------------------------------------------------------------------
    @property
    def dataset(self) -> xr.Dataset:
        """
        Full underlying Dataset.
        """
        return self._ds

    @property
    def mean(self) -> xr.DataArray:
        """
        Primary data variable.
        """
        return self._ds["mean"]

    @property
    def std(self) -> xr.DataArray | None:
        """
        Optional uncertainty.
        """
        if "std_dev" in self._ds.data_vars:
            return self._ds["std_dev"]
        return None

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------
    def stack(self, dim="measurement"):
        """
        For symmetry with AggregateMeasurement.
        Returns mean expanded along a new dimension.
        """
        return self.mean.expand_dims({dim: [0]})

    def mean_value(self):
        """
        Return scalar value if measurement is 0-D.
        """
        if self.mean.ndim != 0:
            raise ValueError("Measurement is not scalar.")
        return float(self.mean.values)
    
    def copy(self):
        return Measurement(
            self._ds.copy(deep=True),
            tags=self.tags.copy()
        )

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------
    def __repr__(self):
        dims = dict(self.mean.sizes)
        return (
            f"{self.__class__.__name__}"
            f"(dims={dims})"
        )


class AggregateMeasurement:
    """
    Represents a hierarchical collection of Measurement
    or AggregateMeasurement objects.

    Does NOT flatten by default.
    """

    def __init__(self, children):
        """
        Parameters
        ----------
        children : list[Measurement | AggregateMeasurement]
        """
        if not isinstance(children, list):
            raise TypeError("children must be a list")

        self.children = children

    def __iter__(self):
        return iter(self.children)

    def __len__(self):
        return len(self.children)

    def flatten(self):
        """
        Recursively return all leaf Measurement objects.
        """
        flat = []

        for child in self.children:
            if isinstance(child, AggregateMeasurement):
                flat.extend(child.flatten())
            else:
                flat.append(child)

        return flat
    
    def select(self, **criteria):
        """
        Select leaf measurements matching tag criteria.
        Example:
            select(velocity=10)
        """
        selected = []

        for m in self.flatten():
            match = all(m.tags.get(k) == v for k, v in criteria.items())

            if match:
                selected.append(m)

        return AggregateMeasurement(selected)
    
    def to_xarray(self, *dims_from_tags):

        leaves = self.flatten()

        mean_arrays = []
        std_arrays = []
        coords = {dim: [] for dim in dims_from_tags}

        for m in leaves:
            
            mean_arrays.append(m.mean)
            std_arrays.append(m.std)

            for dim in dims_from_tags:
                coords[dim].append(m.tags.get(dim))

        if not mean_arrays:
            raise ValueError("No measurements available.")

        mean_stacked = xr.concat(mean_arrays, dim="__stack__")
        std_stacked  = xr.concat(std_arrays,  dim="__stack__")

        for dim in dims_from_tags:
            mean_stacked = mean_stacked.assign_coords(
                {dim: ("__stack__", coords[dim])}
            )
            std_stacked = std_stacked.assign_coords(
                {dim: ("__stack__", coords[dim])}
            )

        # Single dimension
        if len(dims_from_tags) == 1:
            dim = dims_from_tags[0]
            mean_da = mean_stacked.swap_dims({"__stack__": dim})
            std_da  = std_stacked.swap_dims({"__stack__": dim})
        else:
            mean_stacked = mean_stacked.set_index(__stack__=dims_from_tags)
            std_stacked  = std_stacked.set_index(__stack__=dims_from_tags)

            mean_da = mean_stacked.unstack("__stack__")
            std_da  = std_stacked.unstack("__stack__")

        # Ordering
        for dim in dims_from_tags:
            if dim in mean_da.dims:
                mean_da = mean_da.sortby(dim)
                std_da  = std_da.sortby(dim)

        return xr.Dataset({
            "mean": mean_da,
            "std_dev": std_da
        })

    def means(self):
        """
        Return means of immediate children.

        - If child is Measurement → child.mean
        - If child is AggregateMeasurement → child.mean()
        """
        results = []

        for child in self.children:
            if isinstance(child, AggregateMeasurement):
                results.append(child.mean())
            else:
                results.append(child.mean)

        return results

    def leaf_means(self):
        """
        Return mean DataArrays for all leaf Measurements.
        """
        return [m.mean for m in self.flatten()]

    def stack(self, dim="aggregate", flatten=True):
        """
        Concatenate means along a new dimension.

        Parameters
        ----------
        dim : str
            Name of new stacking dimension.
        flatten : bool
            If True → use all leaf measurements.
            If False → use only immediate children.
        """
        if flatten:
            arrays = self.leaf_means()
        else:
            arrays = self.means()

        if not arrays:
            raise ValueError("No measurements to stack.")

        return xr.concat(arrays, dim=dim)

    def mean(self, dim="aggregate", flatten=True):
        """
        Compute mean across stacked measurements.

        Parameters
        ----------
        dim : str
            Name of aggregation dimension.
        flatten : bool
            Control whether hierarchy is flattened.
        """
        stacked = self.stack(dim=dim, flatten=flatten)
        return stacked.mean(dim=dim)

    def __repr__(self):
        return (
            f"{self.__class__.__name__}"
            f"(n_children={len(self.children)})"
        )