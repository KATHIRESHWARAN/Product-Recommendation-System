from flask import Flask, jsonify, request, render_template, send_from_directory
import pandas as pd
import difflib
import os
import csv

app = Flask(__name__, static_folder='static', template_folder='templates')

# Create sample data if it doesn't exist
def create_sample_data():
    """Create a sample dataset for testing if none exists"""
    sample_data = [
        ['Subcategory', 'Category'],
        ['iphone 13', 'Smartphones'],
        ['samsung galaxy s21', 'Smartphones'],
        ['google pixel 6', 'Smartphones'],
        ['oneplus 9', 'Smartphones'],
        ['xiaomi mi 11', 'Smartphones'],
        ['sony xperia 1', 'Smartphones'],
        ['macbook pro', 'Laptops'],
        ['dell xps 13', 'Laptops'],
        ['hp spectre x360', 'Laptops'],
        ['lenovo thinkpad x1', 'Laptops'],
        ['asus zenbook', 'Laptops'],
        ['acer swift', 'Laptops'],
        ['nike air max', 'Shoes'],
        ['adidas ultraboost', 'Shoes'],
        ['puma suede', 'Shoes'],
        ['reebok classic', 'Shoes'],
        ['converse all star', 'Shoes'],
        ['vans old skool', 'Shoes']
    ]
    
    file_path = os.path.join(os.path.dirname(__file__), 'product_recommendation_data.csv')
    if not os.path.exists(file_path):
        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            for row in sample_data:
                writer.writerow(row)
        print(f"Created sample data at {file_path}")

def load_data():
    try:
        # Create sample data if it doesn't exist
        create_sample_data()
        
        # Try multiple possible file locations
        possible_paths = [
            os.path.join(os.path.dirname(__file__), 'product_recommendation_data.csv'),
            'product_recommendation_data.csv',
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'product_recommendation_data.csv')
        ]
        
        for file_path in possible_paths:
            if os.path.exists(file_path):
                product_data = pd.read_csv(file_path)
                print(f"Loaded data from {file_path}")
                break
        else:
            raise FileNotFoundError("Could not find product_recommendation_data.csv in any of the searched locations")
        
        # Clean and prepare data
        product_data.columns = product_data.columns.str.strip()
        product_data['Subcategory'] = product_data['Subcategory'].astype(str).str.strip().str.lower()
        
        # Ensure required columns exist
        required_columns = ['Subcategory', 'Category']
        for col in required_columns:
            if col not in product_data.columns:
                closest = difflib.get_close_matches(col, product_data.columns, n=1, cutoff=0.6)
                if closest:
                    product_data.rename(columns={closest[0]: col}, inplace=True)
                else:
                    raise ValueError(f"Required column '{col}' not found in dataset")
        
        return product_data
    
    except Exception as e:
        raise RuntimeError(f"Error loading data: {str(e)}")

# Load data when app starts
try:
    product_data = load_data()
except Exception as e:
    print(f"Failed to load data: {e}")
    product_data = None

@app.route('/')
def home():
    return render_template('main.html')

@app.route('/recommend', methods=['POST'])
def recommend():
    if product_data is None:
        return jsonify({'error': 'Dataset not loaded'}), 500
    
    try:
        data = request.get_json()
        if not data or 'product_name' not in data:
            return jsonify({'error': 'Missing product_name in request'}), 400
            
        product_name = str(data['product_name']).strip().lower()
        if not product_name:
            return jsonify({'error': 'Empty product name'}), 400
        
        # Find close matches
        subcategories = product_data['Subcategory'].unique()
        matches = difflib.get_close_matches(product_name, subcategories, n=1, cutoff=0.6)
        
        if not matches:
            return jsonify({'error': 'Product not found'}), 404
            
        matched_subcategory = matches[0]
        
        # Get category of matched product
        category_matches = product_data[product_data['Subcategory'] == matched_subcategory]['Category'].unique()
        if len(category_matches) == 0:
            return jsonify({'error': 'Category not found for product'}), 404
            
        category = category_matches[0]
        
        # Get recommendations (5 products from same category, excluding the matched one)
        same_category = product_data[
            (product_data['Category'] == category) & 
            (product_data['Subcategory'] != matched_subcategory)
        ]
        
        if len(same_category) == 0:
            recommendations = []
        else:
            # Get up to 5 unique recommendations
            unique_recommendations = same_category['Subcategory'].unique()
            n = min(5, len(unique_recommendations))
            recommendations = pd.Series(unique_recommendations).sample(n=n, random_state=42).tolist()
        
        return jsonify({
            'product': matched_subcategory,
            'category': category,
            'recommendations': recommendations
        })
        
    except Exception as e:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)