from flask import Flask, jsonify, request
import pyodbc
import os
import decimal
from datetime import datetime, timedelta

app = Flask(__name__)

# ——— Database connection (uses your original env‑vars) ———
def get_db_connection():
    server   = os.environ['DB_SERVER']
    database = os.environ['DB_NAME']
    username = os.environ['DB_USER']
    password = os.environ['DB_PASS']
    driver   = '{ODBC Driver 18 for SQL Server}'
    conn_str = (
        f'DRIVER={driver};SERVER={server};DATABASE={database};'
        f'UID={username};PWD={password};Encrypt=yes;'
        "Encrypt=yes;"
+       "TrustServerCertificate=yes;"
+       "Connection Timeout=120;"
    )
    return pyodbc.connect(conn_str)

# ——— Helper to convert DECIMAL/bytes to JSON-friendly types ———
def to_serializable(val):
    if isinstance(val, decimal.Decimal):
        return float(val)
    if isinstance(val, bytes):
        return val.decode('utf-8')
    return val

# ——— Generic fetch and insert utilities ———
def fetch_all(table, columns):
    conn   = get_db_connection()
    cursor = conn.cursor()
    cols   = ", ".join(columns)
    cursor.execute(f"SELECT {cols} FROM {table};")
    rows   = cursor.fetchall()
    conn.close()

    results = []
    for row in rows:
        record = {}
        for col, val in zip(columns, row):
            record[col] = to_serializable(val)
        results.append(record)
    return results

def fetch_by_id(table, columns, id_field, id_value):
    conn   = get_db_connection()
    cursor = conn.cursor()
    cols   = ", ".join(columns)
    cursor.execute(f"SELECT {cols} FROM {table} WHERE {id_field} = ?;", (id_value,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return {col: to_serializable(val) for col, val in zip(columns, row)}

def insert_record(table, fields, values):
    conn         = get_db_connection()
    cursor       = conn.cursor()
    cols         = ", ".join(fields)
    placeholders = ", ".join("?" for _ in fields)
    cursor.execute(f"INSERT INTO {table} ({cols}) VALUES ({placeholders});", *values)
    conn.commit()
    conn.close()

# ——— Column definitions ———
product_cols = [
    'ProductID',
    'ProductName',
    'ProductCategory',
    'ProductImage'
]

product_info_cols = [
    'InformationID',
    'Product_Biodegradable',
    'Product_GreenHouseGas',
    'Product_WaterUse',
    'Product_HumanHours',
    'Product_MachineHours',
    'Product_Biodegradable_Detailed',
    'Product_GreenHouseGas_Detailed',
    'Product_WaterUse_Detailed',
    'Product_ProductionHours_Detailed',
    'ProductID'
]

alt_prod_cols = [
    'Alternate_Product_ID',
    'Alternate_Product_Name',
    'Alternate_Biodegradable',
    'Alternate_GreenHouseGas',
    'Alternate_WaterUse',
    'Alternate_HumanHours',
    'Alternate_MachineHours',
    'Alternate_Product_Image',
    'ProductID'
]

user_cols = ['userID', 'Username', 'User_FName', 'User_LName', 'Password']

# ——— Endpoints ———
@app.route('/')
def index():
    return "Flask is running!"

@app.route('/products', methods=['GET'])
def get_products():
    category = request.args.get('category')
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cols_sql = ", ".join(product_cols)
        cursor.execute(
            f"SELECT {cols_sql} FROM Products WHERE ProductCategory = ?;",
            (category,)
        )
        rows = cursor.fetchall()
    finally:
        conn.close()

    products = [
        { col: to_serializable(val) for col, val in zip(product_cols, row) }
        for row in rows
    ]
    return jsonify(products)

@app.route('/productdetails', methods=['GET'])
def get_product_details():
    product_id = request.args.get('id')
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cols_sql = ", ".join(product_info_cols)
        cursor.execute(
            f"SELECT {cols_sql} FROM ProductInformation WHERE ProductID = ?;",
            (product_id,)
        )
        row = cursor.fetchone()
    finally:
        conn.close()

    if not row:
        return jsonify({'error': 'Product not found'}), 404

    details = { col: to_serializable(val) for col, val in zip(product_info_cols, row) }
    return jsonify(details)

@app.route('/alternateproducts', methods=['GET'])
def get_alternate_products():
    return jsonify(fetch_all('AlternateProducts', alt_prod_cols))

@app.route('/alternateproducts/<int:alt_id>', methods=['GET'])
def get_alternate_product(alt_id):
    record = fetch_by_id('AlternateProducts', alt_prod_cols, 'Alternate_Product_ID', alt_id)
    if not record:
        return jsonify({'message': 'Not found'}), 404
    return jsonify(record)

@app.route('/alternateproducts', methods=['POST'])
def create_alternate_product():
    payload = request.get_json()
    fields  = alt_prod_cols[1:]  # skip primary key
    values  = [payload.get(f) for f in fields]
    insert_record('AlternateProducts', fields, values)
    return jsonify({'message': 'Alternate product created'}), 201

@app.route('/users', methods=['GET'])
def get_users():
    users = fetch_all('USERS', user_cols)
    # Optionally hide passwords:
    for u in users:
        u.pop('Password', None)
    return jsonify(users)

@app.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    u = fetch_by_id('USERS', user_cols, 'userID', user_id)
    if not u:
        return jsonify({'message': 'Not found'}), 404
    u.pop('Password', None)
    return jsonify(u)

@app.route('/users', methods=['POST'])
def create_user():
    payload = request.get_json()
    fields  = ['Username', 'User_FName', 'User_LName', 'Password']
    values  = [payload.get(f) for f in fields]
    insert_record('USERS', fields, values)
    return jsonify({'message': 'User created'}), 201

@app.route('/users/authenticate', methods=['POST'])
def authenticate_user():
    payload = request.get_json()
    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT userID FROM USERS WHERE Username = ? AND Password = ?;",
        (payload.get('Username'), payload.get('Password'))
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return jsonify({'userID': row[0], 'message': 'Authenticated'}), 200
    return jsonify({'message': 'Invalid credentials'}), 401
@app.route('/impact', methods=['POST'])
def add_impact():
    data = request.get_json()
    # expects { "userID":1, "ghg":7.98, "water":604.53 }
    fields = ['UserID','GHG','Water']
    values = [data['userID'], data['ghg'], data['water']]
    try:
        insert_record('UserImpact', fields, values)
        return jsonify({'status':'ok'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
@app.route('/impact/summary', methods=['GET'])
def impact_summary():
    user_id = request.args.get('userID', type=int)
    if not user_id:
        return jsonify({'error': 'userID required'}), 400

    since_time = datetime.utcnow() - timedelta(days=1)
    try:
        # ← use your real connection function
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute("""
            SELECT
                SUM(GHG)   AS totalGhg,
                SUM(Water) AS totalWater
            FROM UserImpact
            WHERE UserID = ? AND ImpactTime >= ?
        """, (user_id, since_time))
        row = cur.fetchone()
        conn.close()

        total_ghg   = float(row[0] or 0)
        total_water = float(row[1] or 0)
        return jsonify({
            'totalGhg': total_ghg,
            'totalWater': total_water
        })

    except Exception as e:
        app.logger.error(f"impact_summary error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

        
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# expose WSGI for Render deployments
application = app
