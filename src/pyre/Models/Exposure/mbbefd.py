from math import log, exp

def mbbefd_curve(curve_parameter, curve_position):
    b = exp(3.1 - 0.15 * (1 + curve_parameter) * curve_parameter)
    g = exp((0.78 + 0.12 * curve_parameter) * curve_parameter)
    return log(((g - 1) * b + (1 - b * g) * b ^ curve_position) / (1 - b)) / log(b * g)


def share_of_risk(Curve_Parameter, band_mid_point, Attach_lower_Bound, Attach_upper_Bound, Limit_lower_Bound, Limit_upper_Bound, Layer_attach, Layer_limit):
    Pol_Limit = Limit_lower_Bound + band_mid_point * (Limit_upper_Bound - Limit_lower_Bound)
    Pol_Attach = Attach_lower_Bound + band_mid_point * (Attach_upper_Bound - Attach_lower_Bound)
    selected_subject_TIV = Pol_Limit + Pol_Attach
    R_bottom = min(Pol_Attach + Layer_attach, selected_subject_TIV)

    if Layer_limit + Layer_attach < Pol_Limit:
        R_top = Pol_Attach + Layer_limit + Layer_attach
    else:
        R_top = selected_subject_TIV

    if selected_subject_TIV != 0:
        policy_bottom = Pol_Attach / selected_subject_TIV
        policy_top = (Pol_Limit + Pol_Attach) / selected_subject_TIV
        treaty_policy_bottom = R_bottom / selected_subject_TIV
        treaty_policy_top = R_top / selected_subject_TIV

        Curve_Pol_Bottom = mbbefd_curve(Curve_Parameter,policy_bottom)
        Curve_Pol_Top = mbbefd_curve(Curve_Parameter,policy_top)
        Curve_R_Bottom = mbbefd_curve(Curve_Parameter,treaty_policy_bottom)
        Curve_R_Top = mbbefd_curve(Curve_Parameter,treaty_policy_top)
        return (Curve_R_Top - Curve_R_Bottom) / (Curve_Pol_Top - Curve_Pol_Bottom)
