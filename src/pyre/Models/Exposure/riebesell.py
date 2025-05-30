from math import log

def riebesell_curve(attachment:float, limit:float, z_value:float, base_limit:float):
    """_summary_

    Args:
        attachment (float): _description_
        limit (float): _description_
        z_value (float): _description_
        base_limit (float): _description_

    Returns:
        _type_: _description_
    """
    if limit is None:
        return ((attachment) / base_limit) ** log(1 + z_value, 2)
    else:
        return ((attachment + limit) / base_limit) ** log(1 + z_value, 2)
    

def power_ilf(limit:float, basic_limit:float, power_parameter:float)->float:
    if limit is None:
        return 0.0
    else:
        return (limit / basic_limit) ** power_parameter
    