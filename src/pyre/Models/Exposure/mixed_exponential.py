from math import exp

def sumproduct_formula(B4_B18, B19_B33, A39):
    total = 0
    for b4, b19 in zip(B4_B18, B19_B33):
        if b4 != 0:  # to avoid division by zero
            part = (1 - exp((-1 / b4) * A39)) * b4
            total += part * b19
    return total


B4_B18 = [4842.00,19468.00,89377.00,341700.00,1472254.00,4377638.00,10334925.00,22197311.00,100000000.00,1.00,1.00,1.00,1.00,1.00,1.00]  # 15 elements
B19_B33 = [0.566532,0.321014,0.087811,0.019433,0.004017,0.000851,0.000199,0.000108,0.000035,0.0,0.0,0.0,0.0,0.0,0.0]  # 15 elements
A39 = 100000

A39_2 = 50000

result = sumproduct_formula(B4_B18, B19_B33, A39)
result_2 = sumproduct_formula(B4_B18, B19_B33, A39_2)
print(result_2/result)