from typing import Dict
from .exposure_preparer import ExposureModelData
from .exposure_rating_functions import ExposureCurveType #worry about next


def share_of_risk(band_mid_point: float, policy_lower_bound_attachment: float, policy_upper_bound_attachment:float, policy_limit_lower_Bound:float, policy_limit_upper_Bound:float, treaty_layer_attachment:float, treaty_layer_limit:float)->float:
    selected_policy_limit = policy_limit_lower_Bound + band_mid_point * (policy_limit_upper_Bound - policy_limit_lower_Bound)
    selected_policy_attachment = policy_lower_bound_attachment + band_mid_point * (policy_upper_bound_attachment - policy_lower_bound_attachment)
    selected_total_insured_value = selected_policy_limit + selected_policy_attachment
    seleceted_treaty_bottom = min(selected_policy_attachment + treaty_layer_attachment, selected_total_insured_value)

    if treaty_layer_limit + treaty_layer_attachment < selected_policy_limit:
        seleceted_treaty_top = selected_policy_attachment + treaty_layer_limit + treaty_layer_attachment
    else:
        seleceted_treaty_top = selected_total_insured_value

    policy_bottom_pct = selected_policy_attachment / selected_total_insured_value
    policy_top_pct = (selected_policy_limit + selected_policy_attachment) / selected_total_insured_value
    treaty_policy_bottom_pct = seleceted_treaty_bottom / selected_total_insured_value
    treaty_policy_top_pct = seleceted_treaty_top / selected_total_insured_value




class ExposureModel():
    def __init__(self, exposure_model_data: ExposureModelData, selected_curve: ExposureCurveType, curve_parameters: Dict):
        self._exposure_model_data = exposure_model_data
        self._selected_curve = selected_curve
        self._curve_parameters = curve_parameters


# #TODO generalise curve approach -> mbbefd method with share of SI below but riebesell and mixed expo expect value not pct.
#     curve_position_policy_lower = mbbefd_curve(curve_parameter,policy_bottom_pct)
#     curve_position_policy_higher = mbbefd_curve(curve_parameter,policy_top_pct)
#     curve_position_treaty_lower = mbbefd_curve(curve_parameter,treaty_policy_bottom_pct)
#     curve_position_treaty_higher = mbbefd_curve(curve_parameter,treaty_policy_top_pct)
#     return (curve_position_treaty_higher - curve_position_treaty_lower) / (curve_position_policy_higher - curve_position_policy_lower)
