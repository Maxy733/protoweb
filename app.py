# app.py
# A simplified version of the Flask API that reads all data from a local CSV file.
# This version does not include user authentication or database connections.

# Step 1: Import the necessary libraries
from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import random
import re

# Step 2: Create an instance of the Flask application
app = Flask(__name__)
CORS(app)

# Step 3: Load Data from Your CSV File
try:
    # Read from the cleaned CSV file.
    df = pd.read_csv("cleaned_books.csv")

    # Clean all column names (strip whitespace, make lowercase, remove special chars)
    df.columns = [re.sub(r'[^a-zA-Z0-9]', '', col).lower() for col in df.columns]
    
    # --- DEBUGGING STEP ---
    print("Cleaned DataFrame columns are:", list(df.columns))

    # Rename 'itemno' to 'id' for consistency.
    if 'itemno' in df.columns:
        df.rename(columns={'itemno': 'id'}, inplace=True)
    else:
        raise KeyError("Could not find a column named 'itemno' after cleaning.")

    # Ensure 'title' and 'author' columns exist and are strings
    if 'title' not in df.columns or 'author' not in df.columns:
        raise KeyError("The CSV file must contain 'title' and 'author' columns.")
    
    df['title'] = df['title'].astype(str)
    df['author'] = df['author'].astype(str)
    
    # Sanitize data to make it JSON-safe (replaces NaN with None)
    df = df.where(pd.notna(df), None)
    
    # The DataFrame is now clean and ready.
    books_db = df.to_dict('records')

except FileNotFoundError:
    print("Error: 'cleaned_books.csv' not found. Make sure the file is in the correct directory.")
    books_db = []
except KeyError as e:
    print(f"CRITICAL ERROR: {e}")
    books_db = []


# Step 4: Define API Routes

@app.route('/')
def home():
    return "Welcome to the LIBBY BOT Recommender Engine API!"

# --- Search Endpoint ---
@app.route('/api/search', methods=['GET'])
def search_books():
    query = request.args.get('q', '')
    if not query:
        return jsonify({"error": "A search query 'q' is required."}), 400
    if not books_db:
        return jsonify({"error": "Database is empty or failed to load. Check server logs."}), 500

    title_matches = df[df['title'].str.contains(query, case=False, na=False)]
    author_matches = df[df['author'].str.contains(query, case=False, na=False)]

    combined_results = pd.concat([title_matches, author_matches]).drop_duplicates(subset=['id']).to_dict('records')
    return jsonify(combined_results)


# --- Recommendation Strategy 1: Globally Trending ---
@app.route('/api/recommendations/globally-trending', methods=['GET'])
def get_globally_trending():
    if not books_db:
        return jsonify({"error": "Database is empty or failed to load."}), 500
    random.shuffle(books_db)
    return jsonify(books_db[:10])

# --- Recommendation Strategy 2: Content-Based (by Author/Genre if available) ---
@app.route('/api/recommendations/based-on-book/<int:book_id>', methods=['GET'])
def recommend_based_on_book(book_id):
    if not books_db:
        return jsonify({"error": "Database is empty or failed to load."}), 500
        
    source_book = next((book for book in books_db if book.get("id") == book_id), None)
    if not source_book:
        return jsonify({"error": "Source book not found"}), 404

    # Prioritize recommending by genre if it exists
    source_genre = source_book.get("genre")
    if source_genre:
        recommendations = [book for book in books_db if book.get("genre") == source_genre and book.get("id") != book_id]
        random.shuffle(recommendations)
        return jsonify(recommendations[:10])

    # Fallback to recommending by author if no genre
    source_author = source_book.get("author")
    if source_author:
        recommendations = [book for book in books_db if book.get("author") == source_author and book.get("id") != book_id]
        return jsonify(recommendations[:10])

    return jsonify({"error": "Source book has no genre or author to base recommendations on."}), 400


# Step 5: Run the Flask Application
if __name__ == '__main__':
    app.run(debug=True)
