import numpy as np
import matplotlib.pyplot as plt
from src.pyre.Models.Exposure.exposure_curve_fitting import ExposureCurveFitter, select_best_curve
from src.pyre.Models.Exposure.exposure_curve_functions import ExposureCurveType, riebesell_curve, mixed_exponential_curve, mbbefd_curve

def test_riebesell_fitting():
    """Test fitting a Riebesell curve to synthetic data."""
    # Generate synthetic data from a Riebesell curve with z=2.0
    positions = np.linspace(0.1, 1.0, 20)
    true_z = 2.0
    values = [riebesell_curve(0, pos, true_z, 1.0) for pos in positions]
    
    # Add some noise
    np.random.seed(42)
    noisy_values = values + np.random.normal(0, 0.05, len(values))
    
    # Fit the curve
    fitter = ExposureCurveFitter(positions, noisy_values)
    z_value, r_squared = fitter.fit_riebesell()
    
    print(f"True z: {true_z}, Fitted z: {z_value}, R-squared: {r_squared}")
    
    # Plot the results
    plt.figure(figsize=(10, 6))
    plt.scatter(positions, noisy_values, color='black', label='Noisy Data')
    
    x = np.linspace(0, 1, 100)
    y_true = [riebesell_curve(0, pos, true_z, 1.0) for pos in x]
    y_fitted = [riebesell_curve(0, pos, z_value, 1.0) for pos in x]
    
    plt.plot(x, y_true, 'r--', label=f'True Riebesell (z={true_z})')
    plt.plot(x, y_fitted, 'b-', label=f'Fitted Riebesell (z={z_value:.3f}, R²={r_squared:.3f})')
    
    plt.xlabel('Position')
    plt.ylabel('Value')
    plt.title('Riebesell Curve Fitting Test')
    plt.legend()
    plt.grid(True)
    plt.savefig('riebesell_test.png')
    
    return z_value, r_squared

def test_mbbefd_fitting():
    """Test fitting an MBBEFD curve to synthetic data."""
    # Generate synthetic data from an MBBEFD curve with c=3.0
    positions = np.linspace(0.1, 1.0, 20)
    true_c = 3.0
    values = [mbbefd_curve(true_c, pos) for pos in positions]
    
    # Add some noise
    np.random.seed(42)
    noisy_values = values + np.random.normal(0, 0.05, len(values))
    
    # Fit the curve
    fitter = ExposureCurveFitter(positions, noisy_values)
    c_value, r_squared = fitter.fit_mbbefd()
    
    print(f"True c: {true_c}, Fitted c: {c_value}, R-squared: {r_squared}")
    
    # Plot the results
    plt.figure(figsize=(10, 6))
    plt.scatter(positions, noisy_values, color='black', label='Noisy Data')
    
    x = np.linspace(0, 1, 100)
    y_true = [mbbefd_curve(true_c, pos) for pos in x]
    y_fitted = [mbbefd_curve(c_value, pos) for pos in x]
    
    plt.plot(x, y_true, 'r--', label=f'True MBBEFD (c={true_c})')
    plt.plot(x, y_fitted, 'b-', label=f'Fitted MBBEFD (c={c_value:.3f}, R²={r_squared:.3f})')
    
    plt.xlabel('Position')
    plt.ylabel('Value')
    plt.title('MBBEFD Curve Fitting Test')
    plt.legend()
    plt.grid(True)
    plt.savefig('mbbefd_test.png')
    
    return c_value, r_squared

def test_mixed_exponential_fitting():
    """Test fitting a mixed exponential curve to synthetic data."""
    # Generate synthetic data from a mixed exponential curve
    positions = np.linspace(0.1, 1.0, 20)
    true_mus = [0.2, 0.5, 0.8]
    true_weights = [0.3, 0.4, 0.3]
    values = [mixed_exponential_curve(true_mus, true_weights, pos) for pos in positions]
    
    # Add some noise
    np.random.seed(42)
    noisy_values = values + np.random.normal(0, 0.05, len(values))
    
    # Fit the curve
    fitter = ExposureCurveFitter(positions, noisy_values)
    mus, weights, r_squared = fitter.fit_mixed_exponential(num_components=3)
    
    print(f"True mus: {true_mus}, Fitted mus: {mus}")
    print(f"True weights: {true_weights}, Fitted weights: {weights}")
    print(f"R-squared: {r_squared}")
    
    # Plot the results
    plt.figure(figsize=(10, 6))
    plt.scatter(positions, noisy_values, color='black', label='Noisy Data')
    
    x = np.linspace(0, 1, 100)
    y_true = [mixed_exponential_curve(true_mus, true_weights, pos) for pos in x]
    y_fitted = [mixed_exponential_curve(mus, weights, pos) for pos in x]
    
    plt.plot(x, y_true, 'r--', label='True Mixed Exponential')
    plt.plot(x, y_fitted, 'b-', label=f'Fitted Mixed Exponential (R²={r_squared:.3f})')
    
    plt.xlabel('Position')
    plt.ylabel('Value')
    plt.title('Mixed Exponential Curve Fitting Test')
    plt.legend()
    plt.grid(True)
    plt.savefig('mixed_expo_test.png')
    
    return mus, weights, r_squared

def test_select_best_curve():
    """Test selecting the best curve based on R-squared values."""
    # Generate synthetic data from an MBBEFD curve (which should be the best fit)
    positions = np.linspace(0.1, 1.0, 20)
    true_c = 3.0
    values = [mbbefd_curve(true_c, pos) for pos in positions]
    
    # Add some noise
    np.random.seed(42)
    noisy_values = values + np.random.normal(0, 0.05, len(values))
    
    # Select the best curve
    best_curve, params, r_squared = select_best_curve(positions, noisy_values)
    
    print(f"Best curve: {best_curve}")
    print(f"Parameters: {params}")
    print(f"R-squared: {r_squared}")
    
    # Plot all curves
    fitter = ExposureCurveFitter(positions, noisy_values)
    riebesell_params = fitter.fit_riebesell()
    mixed_expo_params = fitter.fit_mixed_exponential()
    mbbefd_params = fitter.fit_mbbefd()
    
    plt.figure(figsize=(10, 6))
    plt.scatter(positions, noisy_values, color='black', label='Data')
    
    x = np.linspace(0, 1, 100)
    
    # Plot all fitted curves
    fitter.plot_fits(riebesell_params, mixed_expo_params, mbbefd_params, title='Comparison of Fitted Curves')
    plt.savefig('best_curve_test.png')
    
    return best_curve, params, r_squared

if __name__ == "__main__":
    print("Testing Riebesell fitting...")
    test_riebesell_fitting()
    
    print("\nTesting MBBEFD fitting...")
    test_mbbefd_fitting()
    
    print("\nTesting Mixed Exponential fitting...")
    test_mixed_exponential_fitting()
    
    print("\nTesting best curve selection...")
    test_select_best_curve()
    
    print("\nAll tests completed.")