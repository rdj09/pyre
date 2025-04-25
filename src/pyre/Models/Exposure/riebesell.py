from math import log

def riebesell_curve(attachment, limit, z_value, base_limit):
    """_summary_

    Args:
        attachment (_type_): _description_
        limit (_type_): _description_
        z_value (_type_): _description_
        base_limit (_type_): _description_

    Returns:
        _type_: _description_
    """
    if limit is None:
        return ((attachment) / base_limit) ** log(1 + z_value, 2)
    else:
        return ((attachment + limit) / base_limit) ** log(1 + z_value, 2)