from flask import Flask, request, jsonify
import pyodbc
import os

app = Flask(__name__)

@app.route('/')
def index():
    return "Flask is running!"

# Azure SQL connection settings
server = os.environ['DB_SERVER']
database = os.environ['DB_NAME']
username = os.environ['DB_USER']
password = os.environ['DB_PASS']
driver = '{ODBC Driver 17 for SQL Server}'

def get_connection():
    return pyodbc.connect(
        f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;'
    )

@app.route('/products', methods=['GET'])
def get_products():
    category = request.args.get('category')
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ProductID, ProductName, ProductImage FROM Products WHERE ProductCategory = ?", (category,))
        rows = cursor.fetchall()
        conn.close()

        products = []
        for row in rows:
            products.append({
                'id': row.ProductID,
                'name': row.ProductName,
                'image': row.ProductImage
            })

        return jsonify(products)
    
    except Exception as e:
        print("ERROR:", str(e))
        return jsonify({"error": "Database connection failed", "details": str(e)}), 500


@app.route('/productdetails', methods=['GET'])
def get_product_details():
    product_id = request.args.get('id')
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT Product_Biodegradable, Product_GreenHouseGas, Product_WaterUse, Product_HumanHours, Product_MachineHours FROM ProductInformation WHERE ProductID = ?", (product_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({'error': 'Product not found'}), 404

    return jsonify({
        'biodegradable': row.Product_Biodegradable,
        'ghg': row.Product_GreenHouseGas,
        'water': row.Product_WaterUse,
        'humanHours': row.Product_HumanHours,
        'machineHours': row.Product_MachineHours
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
    
application = app
