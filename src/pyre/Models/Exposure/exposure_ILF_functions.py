


def pareto_limited_severity(x, alpha:float, x_m:float) -> float:
    if x <= 0:
        return 0.0
    else:
        return 1 - (alpha / (alpha + x)) ** (alpha -1)

def pareto_ilf(limit_1:float, limit_2:float, alpha:float, x_m:float) -> float:
    return  pareto_limited_severity(limit_2, alpha, x_m)/pareto_limited_severity(limit_1, alpha,x_m)


def power_ilf(limit: float, basic_limit: float, power_parameter: float) -> float:
    if limit is None:
        return 0.0
    else:
        return (limit / basic_limit) ** power_parameter