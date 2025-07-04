"""
Extension template for creating custom effects in Prophetverse.

This template provides comprehensive examples and guidance for creating your own effects.
Effects are the building blocks of Prophetverse models, allowing you to incorporate
various components like trend, seasonality, and exogenous regressors.

Key Methods to Understand:
--------------------------
1. `_fit(self, y, X, scale)`: (Optional) Called once during the forecaster's `fit`.
   Use this to perform pre-computations or fit objects needed later.

2. `_transform(self, X, fh)`: (Optional) Called during both `fit` and `predict`.
   Converts pandas DataFrame to a format suitable for `_predict` (typically JAX arrays).
   The default implementation converts selected columns to JAX arrays. The
   shape for array data is (n_series, n_timepoints, n_features).

3. `_predict(self, data, predicted_effects, **kwargs)`: (Mandatory) Core effect logic.
   Receives data from `_transform` and returns the computed effect as a JAX array.
   Use `numpyro.sample` here to define prior distributions for parameters. The
   shape for array data is (n_series, n_timepoints, n_features) if capability
   if false for both `capability:panel` and `capability:multivariate_input`.,
   (n_timepoints, n_features) if  'capability:multivariate_input' is true, and
   (n_series, n_timepoints, 1) if `capability:panel` is true. The output should
   be a jax array of shapre (n_series, n_timepoints, 1) if `capability:panel` is true,
   and (n_timepoints, 1) otherwise.


Effect Tags (Control Behavior):
-------------------------------
- `capability:panel`: Can handle multiple time series at once.
- `capability:multivariate_input`: Can process multiple columns simultaneously.
- `requires_X`: Skip if no matching columns found in X.
- `applies_to`: Whether effect uses 'X' (exogenous) or 'y' (target) data.
- `filter_indexes_with_forecating_horizon_at_transform`: Pre-filter data to forecast horizon.
- `requires_fit_before_transform`: Require fit() before transform().
- `feature:panel_hyperpriors`: Uses hyperpriors for hierarchical modeling.

How Tags Modify Behavior:
-------------------------
Tags are metadata that control how Prophetverse handles your effect. Here's a
deeper dive into how they influence the `_fit`, `_transform`, and `_predict` methods:

- `capability:panel` (bool):
  - If `True`, your effect is expected to handle panel data (multiple time series) directly. `_fit` and `_transform` receive the full DataFrame with a MultiIndex.
  - If `False` (default), and panel data is provided, Prophetverse automatically broadcasts the effect, applying it to each time series individually.

- `capability:multivariate_input` (bool):
  - If `True`, your effect is expected to handle a DataFrame with multiple columns as input. `_fit` and `_transform` receive all matching columns at once.
  - If `False` (default), and a multi-column DataFrame is provided, Prophetverse broadcasts the effect, applying it to each column individually.

- `requires_X` (bool):
  - If `True` (default), the effect depends on exogenous variables (`X`).
  - If no columns in `X` match the effect's `regex`, the entire effect is
    skipped (`_transform` and `_predict` are not called).
  - If `False`, the effect runs even if `X` is empty or `None`.

- `applies_to` (str: 'X' or 'y'):
  - Determines the input data for your effect.
  - If `'X'` (default), the `data` passed to `_fit` and `_transform` is the
    exogenous variables DataFrame.
  - If `'y'`, the `data` is the target variable DataFrame.

- `filter_indexes_with_forecating_horizon_at_transform` (bool):
  - If `True` (default), during `predict`, the DataFrame passed to `_transform`
    is automatically filtered to only contain dates in the forecasting horizon (`fh`).
  - This is a convenience to avoid manual filtering inside `_transform`.
  - Set to `False` if your effect needs to see data outside the forecast horizon
    during prediction (e.g., for calculating lags).

- `requires_fit_before_transform` (bool):
  - If `True`, Prophetverse ensures that `_fit` has been called before `_transform`.
  - This is crucial if `_transform` relies on state computed in `_fit` (e.g.,
    means, scaling factors).
  - If `False` (default), `_transform` can be called without `_fit`, which is
    typical for stateless effects.

- `feature:panel_hyperpriors` (bool):
  - If `True`, signals that your effect defines hyperpriors for hierarchical
    models, allowing parameters to be shared and learned across different
    time series in a panel dataset. This is an advanced feature for
    implementing hierarchical Bayesian models.
"""

from typing import Any, Dict, Optional

import pandas as pd
import jax.numpy as jnp
import numpyro
import numpyro.distributions as dist

from prophetverse.effects.base import BaseEffect
from prophetverse.utils.frame_to_array import series_to_tensor_or_array


class MySimpleEffect(BaseEffect):
    """
    A simple custom effect example that only overrides `_predict`.

    This template is suitable when no fitting or parameter sampling is required,
    and the effect is a direct transformation of the input data.

    Parameters
    ----------
    scale_factor : float
        A scaling factor applied to the input data.
    bias : float
        A constant bias added to the scaled input.
    """

    _tags = {
        "capability:panel": False,
        "capability:multivariate_input": False,
        "requires_X": True,
        "applies_to": "X",
        "filter_indexes_with_forecating_horizon_at_transform": True,
        "requires_fit_before_transform": False,
    }

    def __init__(self, scale_factor: float = 1.0, bias: float = 0.0):
        # Init hyperparameters before BaseEffect init
        # Do not change them!
        self.scale_factor = scale_factor
        self.bias = bias
        super().__init__()

        # Now, do parameter handling

    def _predict(
        self,
        data: jnp.ndarray,
        predicted_effects: Dict[str, jnp.ndarray],
        *args,
        **kwargs,
    ) -> jnp.ndarray:
        """
        Compute the custom effect by scaling `data` and adding a bias.

        Parameters
        ----------
        data : jnp.ndarray
            Transformed exogenous data from the base `_transform` method.
        predicted_effects : dict
            A dictionary of already computed effects in the model (unused here).

        Returns
        -------
        jnp.ndarray
            The computed effect, a JAX array.
        """
        variable = numpyro.sample("variable", dist.Normal(0.0, 1.0))
        return data * self.scale_factor + self.bias + variable


class MyCustomEffect(BaseEffect):
    """
    A full-featured custom effect example.

    This demonstrates how to implement `_fit`, `_transform`, and `_predict`,
    and how to use tags to control the effect's behavior.

    Steps to implement a new effect:
      1. Override `_fit` (optional) to compute static quantities from `y` and `X`.
      2. Override `_transform` (optional) to prepare `X` as JAX arrays.
      3. Within `_predict`, sample any parameters via `numpyro.sample`.
      4. Implement `_predict` (required) using `data`, `predicted_effects`, and samples.

    Parameters
    ----------
    multiplier : float
        A multiplier applied in `_predict`.
    prior_scale : float
        Scale of the Normal prior for sampling a coefficient.
    """

    _tags = {
        "capability:panel": False,
        "capability:multivariate_input": False,
        "requires_X": True,
        "applies_to": "X",
        "filter_indexes_with_forecating_horizon_at_transform": True,
        "requires_fit_before_transform": True,  # We need fit to learn the mean
    }

    def __init__(self, multiplier: float = 1.0, prior=None):
        # Init hyperparameters before BaseEffect init
        # Do not change them!
        self.multiplier = multiplier
        self.prior = prior
        super().__init__()
        # It's good practice to define priors in __init__
        self._prior = prior if prior is not None else dist.Normal(0.0, 1.0)

    def _fit(self, y: pd.DataFrame, X: Optional[pd.DataFrame], scale: float = 1.0):
        """
        (Optional) Fit phase: called once during forecaster.fit().

        This example learns the column means from the training data `X` for centering.
        """
        if X is not None:
            # Compute and store column means of X for centering in _transform
            self._X_mean = X.mean()
        else:
            self._X_mean = 0.0
        super()._fit(y, X, scale)

    def _transform(self, X: pd.DataFrame, fh: pd.Index) -> Any:
        """
        (Optional) Transform phase: prepares data for `_predict`.

        This example implementation subtracts the stored mean and then converts
        the data to a JAX array.

        The `_transform` method can return one of the following structures:
        - A single `jnp.ndarray`: The simplest and most common case.
        - A `tuple`: Useful for passing multiple arrays or mixed data types.
          The first element is typically the main data array.
        - A `dict`: Flexible for passing named arrays and other metadata.
          Must contain a 'data' key holding the main `jnp.ndarray`.
        """
        # Center the data using the mean learned in _fit
        X_proc = X - self._X_mean
        # Convert to JAX tensor/array
        return series_to_tensor_or_array(X_proc)

    def _predict(
        self,
        data: Any,
        predicted_effects: Dict[str, jnp.ndarray],
        *args,
        **kwargs,
    ) -> jnp.ndarray:
        """
        (Mandatory) Prediction phase: core effect computation.

        This is where the main effect logic happens. Use numpyro.sample()
        to define Bayesian priors for parameters.

        The `data` argument receives the output of `_transform`. Your implementation
        should handle the structure you defined:
        - If `_transform` returns a `jnp.ndarray`, `data` will be that array.
        - If `_transform` returns a `tuple`, `data` will be that tuple.
        - If `_transform` returns a `dict`, `data` will be that dictionary.
        """
        # Sample a coefficient from the prior defined in __init__
        coef = numpyro.sample("my_custom_coef", self._prior)

        # The effect's computation.
        # This example creates a linear effect with the centered data.
        effect = data * coef * self.multiplier

        return effect

    @classmethod
    def get_test_params(cls, parameter_set: str = "default"):
        """
        (Optional) Provide test parameters for Prophetverse's testing framework.
        """
        return [{"multiplier": 2.0, "prior_scale": 1.0}]


# --- Advanced: Additive vs Multiplicative Effects ---
#
# For effects that can switch between additive and multiplicative modes,
# inherit from BaseAdditiveOrMultiplicativeEffect instead of BaseEffect.
#
# Example:
# from prophetverse.effects.base import BaseAdditiveOrMultiplicativeEffect
#
# class AdstockEffect(BaseAdditiveOrMultiplicativeEffect):
#     def __init__(self, effect_mode="multiplicative", **kwargs):
#         super().__init__(effect_mode=effect_mode, **kwargs)
#
#     def _predict(self, data, predicted_effects, **kwargs):
#         # Your core logic here
#         adstock_rate = numpyro.sample("adstock", dist.Beta(1, 1))
#         # The base class handles additive vs multiplicative application
#         return apply_adstock(data, adstock_rate)

# --- Tips for Creating Custom Effects ---
#
# 1. Start with MySimpleEffect template for basic transformations.
# 2. Use MyCustomEffect template when you need parameter fitting.
# 3. Check existing effects in prophetverse.effects for inspiration:
#    - LinearEffect: Simple linear regression
#    - HillEffect: Hill saturation transformation
#    - GeometricAdstockEffect: Media adstock modeling
# 4. Use descriptive parameter names in numpyro.sample().
# 5. Test your effect with get_test_params() method.
# 6. Consider panel data capabilities if working with multiple time series.
