def pareto_limited_severity(x: float, alpha: float) -> float:
    if x <= 0:
        return 0.0
    else:
        return float(1 - (alpha / (alpha + x)) ** (alpha - 1))


def pareto_ilf(limit_1: float, limit_2: float, alpha: float) -> float:
    return pareto_limited_severity(limit_2, alpha) / pareto_limited_severity(
        limit_1, alpha
    )


def power_ilf(limit: float | None, basic_limit: float, power_parameter: float) -> float:
    if limit is None:
        return 0.0
    else:
        return float((limit / basic_limit) ** power_parameter)
