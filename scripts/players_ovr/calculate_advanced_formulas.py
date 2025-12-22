import csv
import os
import numpy as np
from sklearn.linear_model import Ridge, Lasso
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import Pipeline
import glob

def calculate_position_formula(position_file):
    with open(position_file, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    if not rows:
        return None
    
    position = os.path.basename(position_file).replace('.csv', '')
    
    attribute_names = [col for col in rows[0].keys() 
                      if col not in ['position', 'fullName', 'team', 'playerBestOvr']]
    
    X_data = []
    y_data = []
    
    for row in rows:
        try:
            ovr = float(row['playerBestOvr'])
            if ovr < 40:
                continue
            
            attributes = []
            skip_row = False
            for attr in attribute_names:
                val = row[attr]
                if val == '' or val is None:
                    val = 0
                try:
                    attributes.append(float(val))
                except ValueError:
                    skip_row = True
                    break
            
            if not skip_row and len(attributes) == len(attribute_names):
                X_data.append(attributes)
                y_data.append(ovr)
        except (ValueError, KeyError):
            continue
    
    if len(X_data) < 10:
        return None
    
    X = np.array(X_data)
    y = np.array(y_data)
    
    best_r2 = 0
    best_model = None
    best_config = None
    
    configs = [
        {'name': 'Ridge-0.5', 'poly_degree': 1, 'alpha': 0.5},
        {'name': 'Ridge-1.0', 'poly_degree': 1, 'alpha': 1.0},
        {'name': 'Ridge-5.0', 'poly_degree': 1, 'alpha': 5.0},
        {'name': 'Ridge-10.0', 'poly_degree': 1, 'alpha': 10.0},
        {'name': 'Ridge-50.0', 'poly_degree': 1, 'alpha': 50.0},
        {'name': 'Poly2-Ridge1', 'poly_degree': 2, 'alpha': 1.0},
        {'name': 'Poly2-Ridge5', 'poly_degree': 2, 'alpha': 5.0},
        {'name': 'Poly2-Ridge10', 'poly_degree': 2, 'alpha': 10.0},
        {'name': 'Poly2-Ridge50', 'poly_degree': 2, 'alpha': 50.0},
        {'name': 'Poly2-Ridge100', 'poly_degree': 2, 'alpha': 100.0},
    ]
    
    for config in configs:
        try:
            if config['poly_degree'] == 1:
                model = Ridge(alpha=config['alpha'])
                model.fit(X, y)
                feature_names = attribute_names
                coefficients = model.coef_
                intercept = model.intercept_
            else:
                poly = PolynomialFeatures(degree=config['poly_degree'], include_bias=False)
                X_poly = poly.fit_transform(X)
                model = Ridge(alpha=config['alpha'])
                model.fit(X_poly, y)
                feature_names = poly.get_feature_names_out(attribute_names)
                coefficients = model.coef_
                intercept = model.intercept_
                
                if config['poly_degree'] == 1:
                    X_test = X
                else:
                    X_test = X_poly
            
            r2 = model.score(X_poly if config['poly_degree'] > 1 else X, y)
            
            if r2 > best_r2 or (r2 > best_r2 - 0.002 and config['poly_degree'] < best_config['poly_degree'] if best_config else True):
                best_r2 = r2
                best_model = model
                best_config = config
                best_feature_names = feature_names
                best_coefficients = coefficients
                best_intercept = intercept
                best_X = X_poly if config['poly_degree'] > 1 else X
        except Exception as e:
            continue
    
    if best_model is None:
        return None
    
    y_pred = best_model.predict(best_X)
    residuals = y - y_pred
    mae = np.mean(np.abs(residuals))
    rmse = np.sqrt(np.mean(residuals**2))
    
    result = {
        'position': position,
        'sample_size': len(X_data),
        'r2_score': best_r2,
        'mae': mae,
        'rmse': rmse,
        'config': best_config['name'],
        'intercept': best_intercept,
        'attribute_names': attribute_names,
        'feature_names': list(best_feature_names),
        'coefficients': list(best_coefficients),
        'avg_ovr': np.mean(y),
        'min_ovr': np.min(y),
        'max_ovr': np.max(y)
    }
    
    return result

def main():
    positions_dir = '../../output/positions'
    output_file = '../../output/individual_position_formulas.txt'
    
    position_files = sorted(glob.glob(os.path.join(positions_dir, '*.csv')))
    
    results = []
    
    for position_file in position_files:
        position = os.path.basename(position_file).replace('.csv', '')
        print(f"\n{'='*80}")
        print(f"Analyzing: {position}")
        print(f"{'='*80}")
        
        result = calculate_position_formula(position_file)
        
        if result is None:
            print(f"Insufficient data for {position}")
            continue
        
        results.append(result)
        
        print(f"\nSample Size: {result['sample_size']}")
        print(f"OVR Range: {result['min_ovr']:.0f} - {result['max_ovr']:.0f} (Avg: {result['avg_ovr']:.1f})")
        print(f"Best Model: {result['config']}")
        print(f"R² Score: {result['r2_score']:.6f}")
        print(f"MAE: {result['mae']:.3f}")
        print(f"RMSE: {result['rmse']:.3f}")
        
        print(f"\nFormula:")
        print(f"OVR = {result['intercept']:.4f}", end="")
        
        if result['config'].startswith('Poly'):
            print(f"\n(Polynomial features included)")
            top_features = sorted(zip(result['feature_names'], result['coefficients']), 
                                key=lambda x: abs(x[1]), reverse=True)[:15]
            print(f"\nTop 15 Features:")
            for feat, coef in top_features:
                print(f"  {coef:+.6f} * {feat}")
        else:
            for attr, coef in zip(result['attribute_names'], result['coefficients']):
                print(f" {coef:+.6f}*{attr}", end="")
            print()
            
            sorted_coefs = sorted(zip(result['attribute_names'], result['coefficients']), 
                                key=lambda x: abs(x[1]), reverse=True)
            print(f"\nAttribute Importance:")
            print(f"{'Attribute':<30} {'Coefficient':>12} {'Impact':>12}")
            print("-" * 56)
            for attr, coef in sorted_coefs:
                if abs(coef) > 0.001:
                    impact = 1.0 / coef if coef != 0 else 0
                    print(f"{attr:<30} {coef:>12.6f} {impact:>12.2f}")
    
    with open(output_file, 'w') as f:
        f.write("="*80 + "\n")
        f.write("MADDEN OVR FORMULA ANALYSIS - INDIVIDUAL POSITIONS\n")
        f.write("="*80 + "\n\n")
        
        f.write(f"{'Position':<12} {'Samples':>8} {'R²':>10} {'MAE':>8} {'RMSE':>8} {'Model':<20}\n")
        f.write("-"*80 + "\n")
        
        for result in sorted(results, key=lambda x: -x['r2_score']):
            f.write(f"{result['position']:<12} {result['sample_size']:>8} "
                   f"{result['r2_score']:>10.6f} {result['mae']:>8.3f} "
                   f"{result['rmse']:>8.3f} {result['config']:<20}\n")
        
        f.write("\n\n")
        f.write("="*80 + "\n")
        f.write("DETAILED FORMULAS BY POSITION\n")
        f.write("="*80 + "\n\n")
        
        for result in sorted(results, key=lambda x: x['position']):
            f.write(f"\n{'='*80}\n")
            f.write(f"{result['position']} (R² = {result['r2_score']:.6f})\n")
            f.write(f"{'='*80}\n")
            f.write(f"Sample: {result['sample_size']} players | "
                   f"OVR: {result['min_ovr']:.0f}-{result['max_ovr']:.0f} (Avg: {result['avg_ovr']:.1f})\n")
            f.write(f"Model: {result['config']} | MAE: {result['mae']:.3f} | RMSE: {result['rmse']:.3f}\n\n")
            
            f.write(f"OVR = {result['intercept']:.6f}\n")
            
            if result['config'].startswith('Poly'):
                f.write("(Using polynomial features)\n\n")
                top_features = sorted(zip(result['feature_names'], result['coefficients']), 
                                    key=lambda x: abs(x[1]), reverse=True)[:20]
                f.write("Top 20 Features:\n")
                for feat, coef in top_features:
                    f.write(f"  {coef:+.8f} * {feat}\n")
            else:
                for attr, coef in zip(result['attribute_names'], result['coefficients']):
                    f.write(f"  {coef:+.8f} * {attr}\n")
            
            f.write("\n")
    
    print(f"\n\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"\nTotal Positions Analyzed: {len(results)}")
    print(f"Average R² Score: {np.mean([r['r2_score'] for r in results]):.6f}")
    print(f"Positions with R² > 0.99: {sum(1 for r in results if r['r2_score'] > 0.99)}")
    print(f"Positions with R² > 0.995: {sum(1 for r in results if r['r2_score'] > 0.995)}")
    print(f"\nResults saved to: {output_file}")

if __name__ == '__main__':
    main()
