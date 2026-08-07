from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import random
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app)

DATABASE = "tappay.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            student_id TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            amount REAL NOT NULL,
            transaction_id TEXT UNIQUE NOT NULL,
            status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Tap Pay Backend is Running!"
    })


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()

    if not data:
        return jsonify({
            "message": "Invalid request"
        }), 400

    name = data.get("name")
    student_id = data.get("student_id")
    email = data.get("email")
    password = data.get("password")

    if not name or not student_id or not email or not password:
        return jsonify({
            "message": "All fields are required"
        }), 400

    conn = get_db()
    cursor = conn.cursor()

    try:
        hashed_password = generate_password_hash(password)

        cursor.execute("""
            INSERT INTO students
            (name, student_id, email, password)
            VALUES (?, ?, ?, ?)
        """, (
            name,
            student_id,
            email,
            hashed_password
        ))

        conn.commit()

        return jsonify({
            "message": "Registration successful"
        }), 201

    except sqlite3.IntegrityError:
        return jsonify({
            "message": "Student ID or Email already exists"
        }), 409

    finally:
        conn.close()


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    if not data:
        return jsonify({
            "message": "Invalid request"
        }), 400

    student_id = data.get("student_id")
    password = data.get("password")

    if not student_id or not password:
        return jsonify({
            "message": "Student ID and Password are required"
        }), 400

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM students
        WHERE student_id = ?
    """, (student_id,))

    student = cursor.fetchone()
    conn.close()

    if student is None:
        return jsonify({
            "message": "Invalid Student ID or Password"
        }), 401

    if not check_password_hash(student["password"], password):
        return jsonify({
            "message": "Invalid Student ID or Password"
        }), 401

    return jsonify({
        "message": "Login successful",
        "student": {
            "name": student["name"],
            "student_id": student["student_id"],
            "email": student["email"]
        }
    }), 200


@app.route("/payment", methods=["POST"])
def payment():
    data = request.get_json()

    if not data:
        return jsonify({
            "message": "Invalid request"
        }), 400

    student_id = data.get("student_id")
    amount = data.get("amount")

    if not student_id or amount is None:
        return jsonify({
            "message": "Student ID and amount are required"
        }), 400

    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return jsonify({
            "message": "Invalid amount"
        }), 400

    if amount <= 0:
        return jsonify({
            "message": "Amount must be greater than zero"
        }), 400

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT student_id
        FROM students
        WHERE student_id = ?
    """, (student_id,))

    student = cursor.fetchone()

    if student is None:
        conn.close()
        return jsonify({
            "message": "Student not found"
        }), 404

    transaction_id = "TP-" + str(random.randint(100000, 999999))

    while True:
        cursor.execute("""
            SELECT id
            FROM transactions
            WHERE transaction_id = ?
        """, (transaction_id,))

        if cursor.fetchone() is None:
            break

        transaction_id = "TP-" + str(random.randint(100000, 999999))

    status = "Successful"

    cursor.execute("""
        INSERT INTO transactions
        (
            student_id,
            amount,
            transaction_id,
            status
        )
        VALUES (?, ?, ?, ?)
    """, (
        student_id,
        amount,
        transaction_id,
        status
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Payment successful",
        "transaction": {
            "student_id": student_id,
            "amount": amount,
            "transaction_id": transaction_id,
            "status": status
        }
    }), 201


@app.route("/transactions/<student_id>", methods=["GET"])
def get_transactions(student_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            amount,
            transaction_id,
            status,
            created_at
        FROM transactions
        WHERE student_id = ?
        ORDER BY id DESC
    """, (student_id,))

    rows = cursor.fetchall()
    conn.close()

    transactions = []

    for row in rows:
        transactions.append({
            "name": "Tap Pay Transaction",
            "amount": row["amount"],
            "id": row["transaction_id"],
            "status": row["status"],
            "created_at": row["created_at"]
        })

    return jsonify({
        "transactions": transactions
    }), 200


if __name__ == "__main__":
    init_db()
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )