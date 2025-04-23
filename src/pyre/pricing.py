def calculate_premium(expected_loss, expense_ratio, profit_margin):
    return expected_loss * (1 + expense_ratio + profit_margin)

def calculate_risk_loading(std_dev_loss, confidence_level):
    return std_dev_loss * confidence_level  # Simplified

# insurekit/contracts.py
class QuotaShareContract:
    def __init__(self, share):
        self.share = share

    def ceded_amount(self, loss):
        return self.share * loss

class ExcessOfLossContract:
    def __init__(self, retention, limit):
        self.retention = retention
        self.limit = limit

    def ceded_amount(self, loss):
        if loss <= self.retention:
            return 0
        return min(loss - self.retention, self.limit)

class SurplusShareContract:
    def __init__(self, retention):
        self.retention = retention

    def ceded_amount(self, sum_insured, loss):
        if sum_insured <= self.retention:
            return 0
        surplus = sum_insured - self.retention
        share = surplus / sum_insured
        return share * loss

class AggregateStopLossContract:
    def __init__(self, attachment_point, limit):
        self.attachment_point = attachment_point
        self.limit = limit

    def ceded_amount(self, total_losses):
        if total_losses <= self.attachment_point:
            return 0
        return min(total_losses - self.attachment_point, self.limit)