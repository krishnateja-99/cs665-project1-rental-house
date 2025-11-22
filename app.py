
import sqlite3
from flask import Flask, render_template, request, redirect, session, url_for

app = Flask(__name__)
app.secret_key = 'change_this_secret_key'

DB_PATH = r"C:\Users\krish\OneDrive\Desktop\cs665_project.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM Users WHERE email = ? AND password = ?", (email, password))
        user = cur.fetchone()
        conn.close()

        if user:
            session['user_id'] = user['user_id']
            session['user_name'] = user['first_name']
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid email or password'
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) AS cnt FROM Properties")
    property_count = cur.fetchone()['cnt']

    cur.execute("SELECT IFNULL(SUM(amount), 0) AS total FROM Payments WHERE status='completed'")
    total_rent_row = cur.fetchone()
    # SQLite on Windows via Python uses 'total' key
    total_rent = total_rent_row['total'] if total_rent_row['total'] is not None else 0

    cur.execute("SELECT COUNT(*) AS cnt FROM Payments")
    payment_count = cur.fetchone()['cnt']

    conn.close()

    return render_template(
        'dashboard.html',
        user_name=session.get('user_name'),
        property_count=property_count,
        total_rent=total_rent,
        payment_count=payment_count
    )


@app.route('/properties')
def property_list():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT p.property_id, p.name, p.address, p.city, "
        "u.first_name || ' ' || u.last_name AS owner_name "
        "FROM Properties p "
        "JOIN Users u ON p.owner_id = u.user_id"
    )
    properties = cur.fetchall()
    conn.close()
    return render_template('properties.html', properties=properties)


@app.route('/properties/add', methods=['GET', 'POST'])
def property_add():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id, first_name || ' ' || last_name AS name FROM Users WHERE role='landlord'")
    landlords = cur.fetchall()

    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        city = request.form['city']
        state = request.form['state']
        zip_code = request.form['zip']
        owner_id = request.form['owner_id']
        description = request.form['description']
        num_units = request.form['num_units']

        cur.execute(
            "INSERT INTO Properties (name, address, city, state, zip, owner_id, description, num_units, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, DATE('now'))",
            (name, address, city, state, zip_code, owner_id, description, num_units)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('property_list'))

    conn.close()
    return render_template('property_form.html', landlords=landlords, action='Add')


@app.route('/properties/<int:property_id>/edit', methods=['GET', 'POST'])
def property_edit(property_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM Properties WHERE property_id = ?", (property_id,))
    prop = cur.fetchone()

    if not prop:
        conn.close()
        return redirect(url_for('property_list'))

    cur.execute("SELECT user_id, first_name || ' ' || last_name AS name FROM Users WHERE role='landlord'")
    landlords = cur.fetchall()

    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        city = request.form['city']
        state = request.form['state']
        zip_code = request.form['zip']
        owner_id = request.form['owner_id']
        description = request.form['description']
        num_units = request.form['num_units']

        cur.execute(
            "UPDATE Properties SET name=?, address=?, city=?, state=?, zip=?, owner_id=?, "
            "description=?, num_units=? WHERE property_id=?",
            (name, address, city, state, zip_code, owner_id, description, num_units, property_id)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('property_list'))

    conn.close()
    return render_template('property_form.html', landlords=landlords, prop=prop, action='Edit')


@app.route('/properties/<int:property_id>/delete', methods=['GET', 'POST'])
def property_delete(property_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Properties WHERE property_id = ?", (property_id,))
    prop = cur.fetchone()

    if not prop:
        conn.close()
        return redirect(url_for('property_list'))

    if request.method == 'POST':
        cur.execute("DELETE FROM Properties WHERE property_id = ?", (property_id,))
        conn.commit()
        conn.close()
        return redirect(url_for('property_list'))

    conn.close()
    return render_template('property_confirm_delete.html', prop=prop)


@app.route('/payments_chart')
def payments_chart():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT substr(payment_date,1,7) AS month, SUM(amount) AS total "
        "FROM Payments "
        "WHERE status='completed' "
        "GROUP BY month "
        "ORDER BY month"
    )
    rows = cur.fetchall()
    conn.close()

    labels = [row['month'] for row in rows]
    data = [row['total'] for row in rows]

    return render_template('payments_chart.html', labels=labels, data=data)


if __name__ == '__main__':
    app.run(debug=True)
