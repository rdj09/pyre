from typing import Any, Dict
from .exposure_curve_functions import ExposureCurveType, calculate_curve
from ...exposures.exposures import Exposures
from ...treaty.contracts import RIContract

# citation https://www.casact.org/sites/default/files/presentation/reinsure_2009_handouts_cs1-rosin.pdf "STACKING"


class ExposureModel:
    def __init__(
        self,
        exposures: Exposures,
        ri_contract: RIContract,
        selected_curve: ExposureCurveType,
        curve_parameters: Dict,
    ):
        self._exposures = exposures
        self._ri_contract = ri_contract
        self._selected_curve = selected_curve
        self._curve_parameters = curve_parameters

    # selected_policy_limit = policy_limit_lower_Bound + band_mid_point * (
    #             policy_limit_upper_Bound - policy_limit_lower_Bound)
    # selected_policy_attachment = policy_lower_bound_attachment + band_mid_point * (
    #             policy_upper_bound_attachment - policy_lower_bound_attachment)
    # selected_total_insured_value = selected_policy_limit + selected_policy_attachment
    # seleceted_treaty_bottom = min(selected_policy_attachment + treaty_layer_attachment, selected_total_insured_value)
    #
    # if treaty_layer_limit + treaty_layer_attachment < selected_policy_limit:
    #     seleceted_treaty_top = selected_policy_attachment + treaty_layer_limit + treaty_layer_attachment
    # else:
    #     seleceted_treaty_top = selected_total_insured_value

    #        curve_position_policy_lower = mbbefd_curve(curve_parameter,selected_policy_attachment / selected_total_insured_value)
    #       curve_position_policy_higher = mbbefd_curve(curve_parameter,(selected_policy_limit + selected_policy_attachment) / selected_total_insured_value)
    #       curve_position_treaty_lower = mbbefd_curve(curve_parameter,seleceted_treaty_bottom / selected_total_insured_value)
    #       curve_position_treaty_higher = mbbefd_curve(curve_parameter,seleceted_treaty_top / selected_total_insured_value)
    #       return (curve_position_treaty_higher - curve_position_treaty_lower) / (curve_position_policy_higher - curve_position_policy_lower)

    # TODO should attach to this class. Think about ILF option nad adjustment to calculation
    def calculate_exposure_curve(
        self, curve_type: ExposureCurveType, parameters: Dict[str, Any], position: float
    ) -> float:
        """Calculate curve value based on curve type and parameters.

        Args:
            curve_type: Type of curve to use
            parameters: Dictionary containing curve-specific parameters
            position: Position on the curve

        Returns:
            float: Calculated curve value
        """
        return calculate_curve(curve_type, parameters, position)

    def _calculate_single_exposure_share(self, exposure):
        """
        Calculate the share of risk for a single exposure.

        Args:
            exposure (Exposure): The exposure to calculate the share for.

        Returns:
            float: The share of risk for the exposure.
        """
        # Extract policy values
        policy_attachment = exposure.exposure_values.attachment_point
        policy_limit = exposure.exposure_values.limit
        total_insured_value = policy_attachment + policy_limit

        # Extract treaty layer values (for each layer in the contract)
        shares_by_layer = {}

        for layer in self._ri_contract.layers:
            treaty_layer_attachment = layer.occurrence_attachment
            treaty_layer_limit = layer.occurrence_limit

            # Calculate treaty layer bottom and top
            treaty_bottom = min(policy_attachment + treaty_layer_attachment, total_insured_value)

            if treaty_layer_limit + treaty_layer_attachment < policy_limit:
                treaty_top = policy_attachment + treaty_layer_limit + treaty_layer_attachment
            else:
                treaty_top = total_insured_value

            # TODO: below is not general for all function very much mbbefd curve input expectations.
            curve_position_policy_lower = self.calculate_exposure_curve(
                self._selected_curve,
                self._curve_parameters,
                policy_attachment / total_insured_value,
            )
            curve_position_policy_higher = self.calculate_exposure_curve(
                self._selected_curve,
                self._curve_parameters,
                total_insured_value / total_insured_value,  # This equals 1.0
            )
            curve_position_treaty_lower = self.calculate_exposure_curve(
                self._selected_curve,
                self._curve_parameters,
                treaty_bottom / total_insured_value,
            )
            curve_position_treaty_higher = self.calculate_exposure_curve(
                self._selected_curve, self._curve_parameters, treaty_top / total_insured_value
            )

            share = (curve_position_treaty_higher - curve_position_treaty_lower) / (
                curve_position_policy_higher - curve_position_policy_lower
            )
            shares_by_layer[layer.layer_id] = share

        return shares_by_layer

    def calculate_all_shares(self) -> Dict[str, Dict[int, float]]:
        """Run _calculate_single_exposure_share for every exposure in self._exposures.

        Returns:
            Dict mapping exposure_id -> {layer_id: share}.

        Raises:
            ValueError: if two exposures share the same exposure_id -- a
                dict-comprehension keyed by exposure_id would otherwise let
                the later one silently overwrite the earlier one's result.
        """
        shares: Dict[str, Dict[int, float]] = {}
        for exposure in self._exposures:
            exposure_id = exposure.exposure_meta.exposure_id
            if exposure_id in shares:
                raise ValueError(f"duplicate exposure_id '{exposure_id}' in exposures collection")
            shares[exposure_id] = self._calculate_single_exposure_share(exposure)
        return shares
