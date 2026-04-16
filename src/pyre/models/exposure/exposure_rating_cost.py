from typing import Any, Dict
from .exposure_curve_functions import ExposureCurveType, exposure_curve_calculation
from ...exposures.exposures import Exposures
from ...treaty.contracts import RIContract

# citation https://www.casact.org/sites/default/files/presentation/reinsure_2009_handouts_cs1-rosin.pdf "STACKING"


class ExposureModel():
    def __init__(self, exposures: Exposures, ri_contract: RIContract, selected_curve: ExposureCurveType, curve_parameters: Dict):
        self._exposures = exposures
        self._ri_contract = ri_contract
        self._selected_curve = selected_curve
        self._curve_parameters = curve_parameters

    def calculate_exposure_curve(self, curve_type: ExposureCurveType, parameters: Dict[str, Any], position: float) -> float:
        """Calculate curve value based on curve type and parameters.

        Args:
            curve_type: Type of curve to use
            parameters: Dictionary containing curve-specific parameters
            position: Position on the curve

        Returns:
            float: Calculated curve value
        """
        if curve_type not in exposure_curve_calculation:
            raise ValueError(f"Unsupported curve type: {curve_type}")

        func = exposure_curve_calculation[curve_type]
        return func(**parameters, curve_position=position)

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
