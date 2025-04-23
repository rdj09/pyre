def calculate_premium(expected_loss, expense_ratio, profit_margin):
    return expected_loss * (1 + expense_ratio + profit_margin)

def calculate_risk_loading(std_dev_loss, confidence_level):
    return std_dev_loss * confidence_level  # Simplified

