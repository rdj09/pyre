from typing import Any

from ...exposures.exposures import Exposures
from ...treaty.contracts import RIContract
from .exposure_curve_functions import ExposureCurveType

# citation https://www.casact.org/sites/default/files/presentation/reinsure_2009_handouts_cs1-rosin.pdf "STACKING"


class ExposureModel:
    def __init__(self, exposures: Exposures, ri_contract: RIContract, selected_curve: ExposureCurveType, curve_parameters: dict):
        self._exposures = exposures
        self._ri_contract = ri_contract
        self._selected_curve = selected_curve
        self._curve_parameters = curve_parameters

    def calculate_exposure_curve(self, curve_type: ExposureCurveType, parameters: dict[str, Any], position: float) -> float:
        """Calculate curve value based on curve type and parameters.

        Args:
            curve_type: Type of curve to use
            parameters: Dictionary containing curve-specific parameters
            position: Position on the curve

        Returns:
            float: Calculated curve value
        """
        from ...models.exposure.exposure_curve_functions import calculate_curve
        return calculate_curve(curve_type, parameters, position)

    def _calculate_single_exposure_share(self, exposure) -> dict:
        """
        Calculate the share of risk ceded to each treaty layer for a single exposure.

        Args:
            exposure: An Exposure object.

        Returns:
            Dict mapping layer_id to share of risk (float between 0 and 1).
        """
        policy_attachment = exposure.exposure_values.attachment_point
        policy_limit = exposure.exposure_values.limit
        total_insured_value = policy_attachment + policy_limit

        shares_by_layer: dict = {}

        for layer in self._ri_contract.layers:
            treaty_attachment = layer.occurrence_attachment
            treaty_limit = layer.occurrence_limit

            treaty_bottom = min(policy_attachment + treaty_attachment, total_insured_value)

            if treaty_limit + treaty_attachment < policy_limit:
                treaty_top = policy_attachment + treaty_limit + treaty_attachment
            else:
                treaty_top = total_insured_value

            # Avoid division by zero
            if total_insured_value == 0:
                shares_by_layer[layer.layer_id] = 0.0
                continue

            curve_pos_policy_lower = self.calculate_exposure_curve(
                self._selected_curve,
                self._curve_parameters,
                policy_attachment / total_insured_value,
            )
            curve_pos_policy_upper = self.calculate_exposure_curve(
                self._selected_curve,
                self._curve_parameters,
                total_insured_value / total_insured_value,  # = 1.0
            )
            curve_pos_treaty_lower = self.calculate_exposure_curve(
                self._selected_curve,
                self._curve_parameters,
                treaty_bottom / total_insured_value,
            )
            curve_pos_treaty_upper = self.calculate_exposure_curve(
                self._selected_curve,
                self._curve_parameters,
                treaty_top / total_insured_value,
            )

            policy_span = curve_pos_policy_upper - curve_pos_policy_lower
            if policy_span == 0:
                shares_by_layer[layer.layer_id] = 0.0
            else:
                share = (curve_pos_treaty_upper - curve_pos_treaty_lower) / policy_span
                shares_by_layer[layer.layer_id] = share

        return shares_by_layer

    def calculate_exposure_rate(self, analysis_date) -> dict:
        """Exposure-rated burning cost per unit of earned exposure per layer.

        For each layer: sum(exposure_value * share_of_risk) / total_earned_exposure.

        Args:
            analysis_date: The date used to calculate earned exposure values.

        Returns:
            Dict mapping layer_id to exposure rate.
        """
        total_earned = sum(
            exp.earned_exposure_value(analysis_date) for exp in self._exposures
        )
        if total_earned == 0:
            return {layer.layer_id: 0.0 for layer in self._ri_contract.layers}

        layer_weighted_sums: dict = {layer.layer_id: 0.0 for layer in self._ri_contract.layers}
        for exposure in self._exposures:
            shares = self._calculate_single_exposure_share(exposure)
            ev = exposure.earned_exposure_value(analysis_date)
            for layer_id, share in shares.items():
                layer_weighted_sums[layer_id] += ev * share

        return {lid: val / total_earned for lid, val in layer_weighted_sums.items()}

    def calculate_ilf_adjusted_rate(self, ilf_function, analysis_date) -> dict:
        """ILF-adjusted exposure rate per layer.

        Multiplies each exposure's contribution by an Increased Limit Factor
        evaluated at the policy limit, then aggregates.

        Args:
            ilf_function: Callable(limit: float) -> float.
            analysis_date: Date used to calculate earned exposure.

        Returns:
            Dict mapping layer_id to ILF-adjusted exposure rate.
        """
        total_earned = sum(
            exp.earned_exposure_value(analysis_date) for exp in self._exposures
        )
        if total_earned == 0:
            return {layer.layer_id: 0.0 for layer in self._ri_contract.layers}

        layer_weighted_sums: dict = {layer.layer_id: 0.0 for layer in self._ri_contract.layers}
        for exposure in self._exposures:
            shares = self._calculate_single_exposure_share(exposure)
            ev = exposure.earned_exposure_value(analysis_date)
            ilf = ilf_function(exposure.exposure_values.limit)
            for layer_id, share in shares.items():
                layer_weighted_sums[layer_id] += ev * share * ilf

        return {lid: val / total_earned for lid, val in layer_weighted_sums.items()}
