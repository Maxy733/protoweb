# app.py
# FINAL VERSION: This API is fully powered by the PostgreSQL database.
# It no longer reads from any local CSV files.

# Step 1: Import the necessary libraries
from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2 
import os
from werkzeug.security import generate_password_hash, check_password_hash
# psycopg2.extras allows us to get query results as dictionaries
from psycopg2.extras import RealDictCursor

# Step 2: Create an instance of the Flask application
app = Flask(__name__)
CORS(app)

# --- PostgreSQL Database Connection ---
def get_db_connection():
    """A function to connect to the PostgreSQL database using the DATABASE_URL from Railway."""
    try:
        conn = psycopg2.connect(
            os.environ.get("DATABASE_URL"),
            # We use RealDictCursor to get results as dictionaries instead of tuples
            cursor_factory=RealDictCursor 
        )
        return conn
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {e}")
        return None

# --- User Authentication Endpoints (No changes needed) ---
@app.route('/api/register', methods=['POST'])
def register_user():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({"error": "Email and password are required."}), 400
    email = data['email']
    password_hash = generate_password_hash(data['password'])
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed."}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (email, password_hash) VALUES (%s, %s)", (email, password_hash))
        conn.commit()
    except psycopg2.IntegrityError:
        return jsonify({"error": "This email address is already registered."}), 409
    finally:
        cursor.close()
        conn.close()
    return jsonify({"message": "User registered successfully!"}), 201

@app.route('/api/login', methods=['POST'])
def login_user():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({"error": "Email and password are required."}), 400
    email = data['email']
    password = data['password']
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed."}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        if user and check_password_hash(user["password_hash"], password):
            return jsonify({"message": "Login successful!"}), 200
        else:
            return jsonify({"error": "Invalid email or password."}), 401
    finally:
        cursor.close()
        conn.close()

# --- Book-related Endpoints (Now powered by PostgreSQL) ---

@app.route('/api/search', methods=['GET'])
def search_books():
    """Searches the 'books' table in the database."""
    query = request.args.get('q', '')
    if not query: return jsonify({"error": "Query required"}), 400
    
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed."}), 500
    
    try:
        cursor = conn.cursor()
        # Use ILIKE for case-insensitive search in PostgreSQL
        search_query = f"%{query}%"
        cursor.execute(
            "SELECT * FROM books WHERE title ILIKE %s OR author ILIKE %s",
            (search_query, search_query)
        )
        results = cursor.fetchall()
        return jsonify(results)
    finally:
        cursor.close()
        conn.close()

@app.route('/api/recommendations/globally-trending', methods=['GET'])
def get_globally_trending():
    """Gets the top 10 books with the highest rating."""
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed."}), 500
    
    try:
        cursor = conn.cursor()
        # A better trending logic: order by rating and get the top 10
        cursor.execute("SELECT * FROM books WHERE rating IS NOT NULL ORDER BY rating DESC LIMIT 10")
        results = cursor.fetchall()
        return jsonify(results)
    finally:
        cursor.close()
        conn.close()

@app.route('/api/recommendations/based-on-book/<int:book_id>', methods=['GET'])
def recommend_based_on_book(book_id):
    """Recommends other books from the same genre."""
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed."}), 500
    
    try:
        cursor = conn.cursor()
        # First, find the genre of the source book
        cursor.execute("SELECT genre FROM books WHERE id = %s", (book_id,))
        source_book = cursor.fetchone()
        
        if not source_book or not source_book['genre']:
            return jsonify({"error": "Source book not found or has no genre."}), 404
        
        source_genre = source_book['genre']
        
        # Now, find other books with the same genre, excluding the source book itself
        cursor.execute(
            "SELECT * FROM books WHERE genre = %s AND id != %s ORDER BY RANDOM() LIMIT 10",
            (source_genre, book_id)
        )
        recommendations = cursor.fetchall()
        return jsonify(recommendations)
    finally:
        cursor.close()
        conn.close()

# Step 5: Run the Flask Application
if __name__ == '__main__':
    app.run(debug=True)
