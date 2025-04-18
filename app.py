from flask import Flask, jsonify, request
import pyodbc
import os

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

# ——— Helper functions ———
def fetch_all(table, columns):
    conn   = get_db_connection()
    cursor = conn.cursor()
    cols   = ", ".join(columns)
    cursor.execute(f"SELECT {cols} FROM {table};")
    rows   = cursor.fetchall()
    conn.close()
    return [dict(zip(columns, row)) for row in rows]

def fetch_by_id(table, columns, id_field, id_value):
    conn   = get_db_connection()
    cursor = conn.cursor()
    cols   = ", ".join(columns)
    cursor.execute(f"SELECT {cols} FROM {table} WHERE {id_field} = ?;", (id_value,))
    row    = cursor.fetchone()
    conn.close()
    return dict(zip(columns, row)) if row else None

def insert_record(table, fields, values):
    conn        = get_db_connection()
    cursor      = conn.cursor()
    cols        = ", ".join(fields)
    placeholders = ", ".join("?" for _ in fields)
    cursor.execute(
        f"INSERT INTO {table} ({cols}) VALUES ({placeholders});",
        *values
    )
    conn.commit()
    conn.close()

# ——— AlternateProducts endpoints ———
alt_prod_cols = [
    'InformationID', 'Product_Biodegradable', 'Product_GreenHouseGas',
    'Product_WaterUse', 'Product_HumanHours', 'Product_MachineHours',
    'Product_Biodegradable_Detailed', 'Product_GreenHouseGas_Detailed',
    'Product_WaterUse_Detailed', 'Product_ProductionHours_Detailed', 'ProductID'
]

@app.route('/alternateproducts', methods=['GET'])
def get_alternate_products():
    return jsonify(fetch_all('AlternateProducts', alt_prod_cols))

@app.route('/alternateproducts/<int:info_id>', methods=['GET'])
def get_alternate_product(info_id):
    record = fetch_by_id('AlternateProducts', alt_prod_cols, 'InformationID', info_id)
    if not record:
        return jsonify({'message': 'Not found'}), 404
    return jsonify(record)

@app.route('/alternateproducts', methods=['POST'])
def create_alternate_product():
    payload = request.get_json()
    fields  = alt_prod_cols[1:]  # skip auto‑gen InformationID
    values  = [payload.get(col) for col in fields]
    insert_record('AlternateProducts', fields, values)
    return jsonify({'message': 'Alternate product created'}), 201

# ——— USERS endpoints ———
user_cols = ['userID', 'Username', 'Password']

@app.route('/users', methods=['GET'])
def get_users():
    users = fetch_all('USERS', user_cols)
    for u in users:
        u.pop('Password', None)   # don’t expose passwords
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
    conn    = get_db_connection()
    cursor  = conn.cursor()
    cursor.execute(
        "SELECT userID FROM USERS WHERE Username = ? AND Password = ?;",
        payload.get('Username'), payload.get('Password')
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return jsonify({'userID': row[0], 'message': 'Authenticated'}), 200
    return jsonify({'message': 'Invalid credentials'}), 401

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

# expose WSGI variable if needed
application = app
