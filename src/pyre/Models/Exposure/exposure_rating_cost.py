from typing import Dict
from .exposure_curve_functions import ExposureCurveType
from ...exposures.exposures import Exposures
from ...treaty.contracts import RIContract


class ExposureModel():
    def __init__(self, exposures: Exposures, ri_contract: RIContract, selected_curve: ExposureCurveType, curve_parameters: Dict):
        self._exposures = exposures
        self._ri_contract = ri_contract
        self._selected_curve = selected_curve
        self._curve_parameters = curve_parameters


    def expousure_share_of_risk(self):
        #TODO loop each exposure return each exposures share of risk
        pass

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
