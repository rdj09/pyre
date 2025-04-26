from pyre.Models.Exposure.mbbefd import mbbefd_curve
from pyre.Models.Exposure.riebesell import riebesell_curve
from pyre.Models.Exposure.mixed_exponential import mixed_exponential_curve

def share_of_risk(curve_parameter: float, band_mid_point: float, policy_lower_bound_attachment: float, policy_upper_bound_attachment:float, policy_limit_lower_Bound:float, policy_limit_upper_Bound:float, treaty_layer_attachment:float, treaty_layer_limit:float)->float:
    """_summary_

    Args:
        curve_parameter (float): _description_
        band_mid_point (float): _description_
        policy_lower_bound_attachment (float): _description_
        policy_upper_bound_attachment (float): _description_
        policy_limit_lower_Bound (float): _description_
        policy_limit_upper_Bound (float): _description_
        treaty_layer_attachment (float): _description_
        treaty_layer_limit (float): _description_

    Returns:
        float: _description_
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
    
    policy_bottom_pct = selected_policy_attachment / selected_total_insured_value
    policy_top_pct = (selected_policy_limit + selected_policy_attachment) / selected_total_insured_value
    treaty_policy_bottom_pct = seleceted_treaty_bottom / selected_total_insured_value
    treaty_policy_top_pct = seleceted_treaty_top / selected_total_insured_value

#TODO generalise curve approach -> mbbefd method with share of SI below but riebesell and mixed expo expect value not pct.
    curve_position_policy_lower = mbbefd_curve(curve_parameter,policy_bottom_pct) 
    curve_position_policy_higher = mbbefd_curve(curve_parameter,policy_top_pct)
    curve_position_treaty_lower = mbbefd_curve(curve_parameter,treaty_policy_bottom_pct)
    curve_position_treaty_higher = mbbefd_curve(curve_parameter,treaty_policy_top_pct)
    return (curve_position_treaty_higher - curve_position_treaty_lower) / (curve_position_policy_higher - curve_position_policy_lower)