from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
app = Flask(__name__)
CORS(app)
try:
    df = pd.read_excel("Books database.xlsx")
    books_db = df.to_dict('records')
    for i, book in enumerate(books_db):
        if 'id' not in book:
            book['id'] = i + 1

except FileNotFoundError:
    print("Error: 'your_library_database.xlsx' not found. Make sure the file is in the correct directory.")
    # If the file isn't found, we'll use an empty list to avoid crashing the app.
    books_db = []

@app.route('/')
def home():
    return "Welcome to the LIBBY BOT API! The server is running."


@app.route('/api/recommendations/globally-trending', methods=['GET'])
def get_globally_trending():
    """
    Returns a random list of books to simulate a "trending" list,
    since we don't have a trending_score column.
    """
    if not books_db:
        return jsonify({"error": "Database is empty"}), 500

    # Shuffle the list of books randomly.
    random.shuffle(books_db)
    # Return the first 10 books from the shuffled list.
    return jsonify(books_db[:10])

# --- Recommendation Strategy 2: Content-Based (Because you liked...) ---
# UPDATED to use Author instead of Genre.
@app.route('/api/recommendations/based-on-book/<int:book_id>', methods=['GET'])
def recommend_based_on_book(book_id):
    """
    Finds other books by the same Author as the provided book_id.
    This is a content-based recommendation using the Author field.
    """
    if not books_db:
        return jsonify({"error": "Database is empty"}), 500

    # Find the source book that the recommendations should be based on.
    source_book = next((book for book in books_db if book.get("id") == book_id), None)

    if not source_book:
        return jsonify({"error": "Source book not found"}), 404

    source_author = source_book.get("author")
    if not source_author or pd.isna(source_author):
        # If the author is missing or is a NaN value from pandas
        return jsonify({"error": "Source book has no author"}), 400

    # Find all other books by the same author, excluding the source book itself.
    recommendations = [
        book for book in books_db 
        if book.get("author") == source_author and book.get("id") != book_id
    ]

    return jsonify(recommendations)

# --- A simple endpoint to get a single book's details ---
@app.route('/api/books/<int:book_id>', methods=['GET'])
def get_book_by_id(book_id):
    book = next((book for book in books_db if book.get("id") == book_id), None)
    if book:
        return jsonify(book)
    else:
        return jsonify({"error": "Book not found"}), 404


# Step 5: Run the Flask Application
if __name__ == '__main__':
    app.run(debug=True)