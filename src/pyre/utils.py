def validate_inputs(*args):
    for arg in args:
        if not isinstance(arg, (int, float)) or arg < 0:
            raise ValueError("All inputs must be non-negative numbers")