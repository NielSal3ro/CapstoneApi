from flask import Flask, jsonify, request
import pyodbc
import os
import decimal

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
        'TrustServerCertificate=no;Connection Timeout=30;'
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

# ——— Base endpoints ———
@app.route('/')
def index():
    return "Flask is running!"

@app.route('/products', methods=['GET'])
def get_products():
    category = request.args.get('category')
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT ProductID, ProductName, ProductImage FROM Products WHERE ProductCategory = ?;",
            (category,)
        )
        rows = cursor.fetchall()
        conn.close()

        products = []
        for row in rows:
            products.append({
                'id':    row.ProductID,
                'name':  row.ProductName,
                'image': to_serializable(row.ProductImage)
            })
        return jsonify(products)
    except Exception as e:
        print("ERROR:", e)
        return jsonify({
            "error":   "Database connection failed",
            "details": str(e)
        }), 500

@app.route('/productdetails', methods=['GET'])
def get_product_details():
    product_id = request.args.get('id')
    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT Product_Biodegradable, Product_GreenHouseGas, Product_WaterUse, "
        "Product_HumanHours, Product_MachineHours "
        "FROM ProductInformation WHERE ProductID = ?;",
        (product_id,)
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({'error': 'Product not found'}), 404

    biodegradable, ghg, water, human_hours, machine_hours = row
    return jsonify({
        'biodegradable': to_serializable(biodegradable),
        'ghg':           to_serializable(ghg),
        'water':         to_serializable(water),
        'humanHours':    human_hours,
        'machineHours':  machine_hours
    })

# ——— AlternateProducts endpoints ———
alt_prod_cols = [
    'Alternate_Product_ID',
    'Alternate_Product_Name',
    'Alternate_Biodegradable',
    'Alternate_GreenHouseGas',
    'Alternate_WaterUse',
    'Alternate_HumanHours',
    'Alternate_MachineHours',
    'ProductID'
]

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
    fields  = [
        'Alternate_Product_Name',
        'Alternate_Biodegradable',
        'Alternate_GreenHouseGas',
        'Alternate_WaterUse',
        'Alternate_HumanHours',
        'Alternate_MachineHours',
        'ProductID'
    ]
    values = [payload.get(f) for f in fields]
    insert_record('AlternateProducts', fields, values)
    return jsonify({'message': 'Alternate product created'}), 201

# ——— USERS endpoints ———
user_cols = ['userID', 'Username', 'Password']

@app.route('/users', methods=['GET'])
def get_users():
    users = fetch_all('USERS', user_cols)
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
    fields  = ['Username', 'Password']
    values  = [payload.get('Username'), payload.get('Password')]
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)


# expose WSGI for deployments
application = app
