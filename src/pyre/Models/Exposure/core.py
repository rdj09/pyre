from pyre.Models.Exposure.mbbefd import mbbefd_curve
from pyre.Models.Exposure.riebesell import riebesell_curve


def share_of_risk(curve_parameter, band_mid_point, policy_lower_bound_attachment, policy_upper_bound_attachment, policy_limit_lower_Bound, policy_limit_upper_Bound, treaty_layer_attachment, treaty_layer_limit):
    """_summary_

    Args:
        curve_parameter (_type_): _description_
        band_mid_point (_type_): _description_
        policy_lower_bound_attachment (_type_): _description_
        policy_upper_bound_attachment (_type_): _description_
        policy_limit_lower_Bound (_type_): _description_
        policy_limit_upper_Bound (_type_): _description_
        treaty_layer_attachment (_type_): _description_
        treaty_layer_limit (_type_): _description_
    """
    selected_policy_limit = policy_limit_lower_Bound + band_mid_point * (policy_limit_upper_Bound - policy_limit_lower_Bound)
    selected_policy_attachment = policy_lower_bound_attachment + band_mid_point * (policy_upper_bound_attachment - policy_lower_bound_attachment)
    selected_total_insured_value = selected_policy_limit + selected_policy_attachment
    seleceted_treaty_bottom = min(selected_policy_attachment + treaty_layer_attachment, selected_total_insured_value)

#TODO reconsider how logic applied

    if treaty_layer_limit + treaty_layer_attachment < selected_policy_limit:
        seleceted_treaty_top = selected_policy_attachment + treaty_layer_limit + treaty_layer_attachment
    else:
        seleceted_treaty_top = selected_total_insured_value
    
    policy_bottom = selected_policy_attachment / selected_total_insured_value
    policy_top = (selected_policy_limit + selected_policy_attachment) / selected_total_insured_value
    treaty_policy_bottom = seleceted_treaty_bottom / selected_total_insured_value
    treaty_policy_top = seleceted_treaty_top / selected_total_insured_value

#TODO generalise curve approach
    curve_position_policy_lower = mbbefd_curve(curve_parameter,policy_bottom) 
    curve_position_policy_higher = mbbefd_curve(curve_parameter,policy_top)
    curve_position_treaty_lower = mbbefd_curve(curve_parameter,treaty_policy_bottom)
    curve_position_treaty_higher = mbbefd_curve(curve_parameter,treaty_policy_top)
    return (curve_position_treaty_higher - curve_position_treaty_lower) / (curve_position_policy_higher - curve_position_policy_lower)