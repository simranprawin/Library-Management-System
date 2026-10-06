from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "library-management-secret-key"

DATABASE = "library.db"


# -----------------------------
# DATABASE CONNECTION
# -----------------------------

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# -----------------------------
# DATABASE INITIALIZATION
# -----------------------------

def init_database():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            isbn TEXT UNIQUE NOT NULL,
            category TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            available INTEGER NOT NULL DEFAULT 1
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS borrowings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            issue_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            return_date TEXT,
            fine REAL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'Issued',
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        )
    """)

    # Create default admin
    admin = cursor.execute(
        "SELECT id FROM users WHERE email = ?",
        ("admin@library.com",)
    ).fetchone()

    if not admin:
        cursor.execute("""
            INSERT INTO users (name, email, password, role)
            VALUES (?, ?, ?, ?)
        """, (
            "Library Admin",
            "admin@library.com",
            generate_password_hash("admin123"),
            "admin"
        ))

    # Add sample books
    book_count = cursor.execute(
        "SELECT COUNT(*) AS count FROM books"
    ).fetchone()["count"]

    if book_count == 0:
        sample_books = [
            (
                "Python Programming",
                "Mark Lutz",
                "978-0596007973",
                "Programming",
                5,
                5
            ),
            (
                "Clean Code",
                "Robert C. Martin",
                "978-0132350884",
                "Software Development",
                3,
                3
            ),
            (
                "Introduction to Algorithms",
                "Thomas H. Cormen",
                "978-0262046305",
                "Algorithms",
                4,
                4
            ),
            (
                "Artificial Intelligence",
                "Stuart Russell",
                "978-0134610993",
                "Artificial Intelligence",
                2,
                2
            ),
            (
                "Database System Concepts",
                "Abraham Silberschatz",
                "978-0078022159",
                "Database",
                3,
                3
            )
        ]

        cursor.executemany("""
            INSERT INTO books
            (title, author, isbn, category, quantity, available)
            VALUES (?, ?, ?, ?, ?, ?)
        """, sample_books)

    conn.commit()
    conn.close()


# -----------------------------
# LOGIN DECORATORS
# -----------------------------

def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "warning")
            return redirect(url_for("login"))
        return function(*args, **kwargs)

    return wrapper


def admin_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "warning")
            return redirect(url_for("login"))

        if session.get("role") != "admin":
            flash("Admin access required.", "danger")
            return redirect(url_for("index"))

        return function(*args, **kwargs)

    return wrapper


# -----------------------------
# HOME PAGE
# -----------------------------

@app.route("/")
def index():
    conn = get_db()

    books = conn.execute("""
        SELECT *
        FROM books
        ORDER BY id DESC
    """).fetchall()

    total_books = conn.execute(
        "SELECT COALESCE(SUM(quantity), 0) AS total FROM books"
    ).fetchone()["total"]

    available_books = conn.execute(
        "SELECT COALESCE(SUM(available), 0) AS total FROM books"
    ).fetchone()["total"]

    conn.close()

    return render_template(
        "index.html",
        books=books,
        total_books=total_books,
        available_books=available_books
    )


# -----------------------------
# REGISTER
# -----------------------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("Please fill in all fields.", "danger")
            return redirect(url_for("register"))

        if len(password) < 6:
            flash("Password must contain at least 6 characters.", "danger")
            return redirect(url_for("register"))

        conn = get_db()

        existing_user = conn.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if existing_user:
            conn.close()
            flash("An account with this email already exists.", "danger")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)

        conn.execute("""
            INSERT INTO users
            (name, email, password, role)
            VALUES (?, ?, ?, ?)
        """, (
            name,
            email,
            hashed_password,
            "student"
        ))

        conn.commit()
        conn.close()

        flash("Registration successful. Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


# -----------------------------
# LOGIN
# -----------------------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db()

        user = conn.execute("""
            SELECT *
            FROM users
            WHERE email = ?
        """, (email,)).fetchone()

        conn.close()

        if user and check_password_hash(user["password"], password):

            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]
            session["email"] = user["email"]

            flash("Login successful.", "success")

            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))

            return redirect(url_for("student_dashboard"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html")


# -----------------------------
# LOGOUT
# -----------------------------

@app.route("/logout")
def logout():

    session.clear()

    flash("You have been logged out.", "success")

    return redirect(url_for("index"))


# -----------------------------
# STUDENT DASHBOARD
# -----------------------------

@app.route("/student/dashboard")
@login_required
def student_dashboard():

    conn = get_db()

    user_id = session["user_id"]

    issued_books = conn.execute("""
        SELECT
            borrowings.*,
            books.title,
            books.author,
            books.isbn
        FROM borrowings
        JOIN books
            ON borrowings.book_id = books.id
        WHERE borrowings.user_id = ?
        AND borrowings.status = 'Issued'
        ORDER BY borrowings.id DESC
    """, (user_id,)).fetchall()

    history = conn.execute("""
        SELECT
            borrowings.*,
            books.title,
            books.author
        FROM borrowings
        JOIN books
            ON borrowings.book_id = books.id
        WHERE borrowings.user_id = ?
        ORDER BY borrowings.id DESC
    """, (user_id,)).fetchall()

    conn.close()

    return render_template(
        "student_dashboard.html",
        issued_books=issued_books,
        history=history
    )


# -----------------------------
# BOOK LIST
# -----------------------------

@app.route("/books")
def books():

    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()

    conn = get_db()

    query = "SELECT * FROM books WHERE 1=1"
    params = []

    if search:
        query += """
            AND (
                title LIKE ?
                OR author LIKE ?
                OR isbn LIKE ?
            )
        """

        search_value = f"%{search}%"

        params.extend([
            search_value,
            search_value,
            search_value
        ])

    if category:
        query += " AND category = ?"
        params.append(category)

    query += " ORDER BY title ASC"

    books_list = conn.execute(
        query,
        params
    ).fetchall()

    categories = conn.execute("""
        SELECT DISTINCT category
        FROM books
        ORDER BY category
    """).fetchall()

    conn.close()

    return render_template(
        "books.html",
        books=books_list,
        categories=categories,
        search=search,
        selected_category=category
    )


# -----------------------------
# ADD BOOK
# -----------------------------

@app.route("/admin/books/add", methods=["GET", "POST"])
@admin_required
def add_book():

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        isbn = request.form.get("isbn", "").strip()
        category = request.form.get("category", "").strip()

        try:
            quantity = int(request.form.get("quantity", 1))
        except ValueError:
            quantity = 0

        if not title or not author or not isbn or not category:
            flash("Please fill in all fields.", "danger")
            return redirect(url_for("add_book"))

        if quantity <= 0:
            flash("Quantity must be greater than zero.", "danger")
            return redirect(url_for("add_book"))

        conn = get_db()

        existing = conn.execute(
            "SELECT id FROM books WHERE isbn = ?",
            (isbn,)
        ).fetchone()

        if existing:
            conn.close()
            flash("A book with this ISBN already exists.", "danger")
            return redirect(url_for("add_book"))

        conn.execute("""
            INSERT INTO books
            (title, author, isbn, category, quantity, available)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            title,
            author,
            isbn,
            category,
            quantity,
            quantity
        ))

        conn.commit()
        conn.close()

        flash("Book added successfully.", "success")

        return redirect(url_for("books"))

    return render_template("add_book.html")


# -----------------------------
# EDIT BOOK
# -----------------------------

@app.route("/admin/books/edit/<int:book_id>", methods=["GET", "POST"])
@admin_required
def edit_book(book_id):

    conn = get_db()

    book = conn.execute(
        "SELECT * FROM books WHERE id = ?",
        (book_id,)
    ).fetchone()

    if not book:
        conn.close()
        flash("Book not found.", "danger")
        return redirect(url_for("books"))

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        isbn = request.form.get("isbn", "").strip()
        category = request.form.get("category", "").strip()

        try:
            new_quantity = int(request.form.get("quantity", 1))
        except ValueError:
            new_quantity = 0

        if not title or not author or not isbn or not category:
            conn.close()
            flash("Please fill in all fields.", "danger")
            return redirect(url_for("edit_book", book_id=book_id))

        if new_quantity <= 0:
            conn.close()
            flash("Quantity must be greater than zero.", "danger")
            return redirect(url_for("edit_book", book_id=book_id))

        issued_count = book["quantity"] - book["available"]

        if new_quantity < issued_count:
            conn.close()
            flash(
                "Quantity cannot be lower than the number of currently issued books.",
                "danger"
            )
            return redirect(url_for("edit_book", book_id=book_id))

        new_available = new_quantity - issued_count

        try:

            conn.execute("""
                UPDATE books
                SET title = ?,
                    author = ?,
                    isbn = ?,
                    category = ?,
                    quantity = ?,
                    available = ?
                WHERE id = ?
            """, (
                title,
                author,
                isbn,
                category,
                new_quantity,
                new_available,
                book_id
            ))

            conn.commit()

        except sqlite3.IntegrityError:

            conn.close()

            flash(
                "Another book already uses this ISBN.",
                "danger"
            )

            return redirect(
                url_for("edit_book", book_id=book_id)
            )

        conn.close()

        flash("Book updated successfully.", "success")

        return redirect(url_for("books"))

    conn.close()

    return render_template(
        "edit_book.html",
        book=book
    )


# -----------------------------
# DELETE BOOK
# -----------------------------

@app.route("/admin/books/delete/<int:book_id>", methods=["POST"])
@admin_required
def delete_book(book_id):

    conn = get_db()

    active_borrowing = conn.execute("""
        SELECT id
        FROM borrowings
        WHERE book_id = ?
        AND status = 'Issued'
    """, (book_id,)).fetchone()

    if active_borrowing:
        conn.close()

        flash(
            "This book cannot be deleted while it is issued.",
            "danger"
        )

        return redirect(url_for("books"))

    conn.execute(
        "DELETE FROM books WHERE id = ?",
        (book_id,)
    )

    conn.commit()
    conn.close()

    flash("Book deleted successfully.", "success")

    return redirect(url_for("books"))


# -----------------------------
# ISSUE BOOK
# -----------------------------

@app.route("/books/issue/<int:book_id>", methods=["GET", "POST"])
@login_required
def issue_book(book_id):

    conn = get_db()

    book = conn.execute(
        "SELECT * FROM books WHERE id = ?",
        (book_id,)
    ).fetchone()

    if not book:
        conn.close()
        flash("Book not found.", "danger")
        return redirect(url_for("books"))

    if book["available"] <= 0:
        conn.close()
        flash("This book is currently unavailable.", "warning")
        return redirect(url_for("books"))

    if request.method == "POST":

        user_id = session["user_id"]

        existing = conn.execute("""
            SELECT id
            FROM borrowings
            WHERE user_id = ?
            AND book_id = ?
            AND status = 'Issued'
        """, (
            user_id,
            book_id
        )).fetchone()

        if existing:
            conn.close()

            flash(
                "You already have this book issued.",
                "warning"
            )

            return redirect(url_for("books"))

        issue_date = datetime.now().date()
        due_date = issue_date + timedelta(days=14)

        conn.execute("""
            INSERT INTO borrowings
            (
                user_id,
                book_id,
                issue_date,
                due_date,
                status
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            user_id,
            book_id,
            issue_date.isoformat(),
            due_date.isoformat(),
            "Issued"
        ))

        conn.execute("""
            UPDATE books
            SET available = available - 1
            WHERE id = ?
            AND available > 0
        """, (book_id,))

        conn.commit()
        conn.close()

        flash(
            "Book issued successfully. Due in 14 days.",
            "success"
        )

        return redirect(url_for("student_dashboard"))

    conn.close()

    return render_template(
        "issue_book.html",
        book=book
    )


# -----------------------------
# RETURN BOOK
# -----------------------------

@app.route("/books/return/<int:borrowing_id>", methods=["POST"])
@login_required
def return_book(borrowing_id):

    conn = get_db()

    borrowing = conn.execute("""
        SELECT *
        FROM borrowings
        WHERE id = ?
    """, (borrowing_id,)).fetchone()

    if not borrowing:
        conn.close()

        flash(
            "Borrowing record not found.",
            "danger"
        )

        return redirect(url_for("student_dashboard"))

    if borrowing["status"] != "Issued":
        conn.close()

        flash(
            "This book has already been returned.",
            "warning"
        )

        return redirect(url_for("student_dashboard"))

    if borrowing["user_id"] != session["user_id"] and session.get("role") != "admin":
        conn.close()

        flash(
            "You are not authorized to return this book.",
            "danger"
        )

        return redirect(url_for("student_dashboard"))

    return_date = datetime.now().date()

    due_date = datetime.strptime(
        borrowing["due_date"],
        "%Y-%m-%d"
    ).date()

    late_days = max(
        0,
        (return_date - due_date).days
    )

    fine = late_days * 5

    conn.execute("""
        UPDATE borrowings
        SET return_date = ?,
            fine = ?,
            status = 'Returned'
        WHERE id = ?
    """, (
        return_date.isoformat(),
        fine,
        borrowing_id
    ))

    conn.execute("""
        UPDATE books
        SET available = available + 1
        WHERE id = ?
    """, (
        borrowing["book_id"],
    ))

    conn.commit()
    conn.close()

    if fine > 0:
        flash(
            f"Book returned. Late fine: ₹{fine:.2f}",
            "warning"
        )
    else:
        flash(
            "Book returned successfully.",
            "success"
        )

    if session.get("role") == "admin":
        return redirect(url_for("admin_dashboard"))

    return redirect(url_for("student_dashboard"))


# -----------------------------
# MY BOOKS
# -----------------------------

@app.route("/my-books")
@login_required
def my_books():

    conn = get_db()

    records = conn.execute("""
        SELECT
            borrowings.*,
            books.title,
            books.author,
            books.isbn
        FROM borrowings
        JOIN books
            ON borrowings.book_id = books.id
        WHERE borrowings.user_id = ?
        ORDER BY borrowings.id DESC
    """, (
        session["user_id"],
    )).fetchall()

    conn.close()

    return render_template(
        "my_books.html",
        records=records
    )


# -----------------------------
# HISTORY
# -----------------------------

@app.route("/history")
@login_required
def history():

    conn = get_db()

    if session.get("role") == "admin":

        records = conn.execute("""
            SELECT
                borrowings.*,
                users.name AS user_name,
                users.email,
                books.title,
                books.author
            FROM borrowings
            JOIN users
                ON borrowings.user_id = users.id
            JOIN books
                ON borrowings.book_id = books.id
            ORDER BY borrowings.id DESC
        """).fetchall()

    else:

        records = conn.execute("""
            SELECT
                borrowings.*,
                books.title,
                books.author
            FROM borrowings
            JOIN books
                ON borrowings.book_id = books.id
            WHERE borrowings.user_id = ?
            ORDER BY borrowings.id DESC
        """, (
            session["user_id"],
        )).fetchall()

    conn.close()

    return render_template(
        "history.html",
        records=records
    )


# -----------------------------
# ADMIN DASHBOARD
# -----------------------------

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():

    conn = get_db()

    total_users = conn.execute("""
        SELECT COUNT(*) AS count
        FROM users
        WHERE role = 'student'
    """).fetchone()["count"]

    total_book_titles = conn.execute("""
        SELECT COUNT(*) AS count
        FROM books
    """).fetchone()["count"]

    total_books = conn.execute("""
        SELECT COALESCE(SUM(quantity), 0) AS count
        FROM books
    """).fetchone()["count"]

    available_books = conn.execute("""
        SELECT COALESCE(SUM(available), 0) AS count
        FROM books
    """).fetchone()["count"]

    issued_books = conn.execute("""
        SELECT COUNT(*) AS count
        FROM borrowings
        WHERE status = 'Issued'
    """).fetchone()["count"]

    returned_books = conn.execute("""
        SELECT COUNT(*) AS count
        FROM borrowings
        WHERE status = 'Returned'
    """).fetchone()["count"]

    total_fines = conn.execute("""
        SELECT COALESCE(SUM(fine), 0) AS total
        FROM borrowings
    """).fetchone()["total"]

    recent_borrowings = conn.execute("""
        SELECT
            borrowings.*,
            users.name AS user_name,
            books.title
        FROM borrowings
        JOIN users
            ON borrowings.user_id = users.id
        JOIN books
            ON borrowings.book_id = books.id
        ORDER BY borrowings.id DESC
        LIMIT 10
    """).fetchall()

    conn.close()

    return render_template(
        "admin_dashboard.html",
        total_users=total_users,
        total_book_titles=total_book_titles,
        total_books=total_books,
        available_books=available_books,
        issued_books=issued_books,
        returned_books=returned_books,
        total_fines=total_fines,
        recent_borrowings=recent_borrowings
    )


# -----------------------------
# ADMIN USERS
# -----------------------------

@app.route("/admin/users")
@admin_required
def admin_users():

    conn = get_db()

    users = conn.execute("""
        SELECT id, name, email, role
        FROM users
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "history.html",
        records=[],
        users=users
    )


# -----------------------------
# ERROR HANDLERS
# -----------------------------

@app.errorhandler(404)
def page_not_found(error):
    return """
    <h1>404 - Page Not Found</h1>
    <p>The page you are looking for does not exist.</p>
    <a href="/">Go Home</a>
    """, 404


@app.errorhandler(500)
def internal_error(error):
    return """
    <h1>500 - Internal Server Error</h1>
    <p>Something went wrong.</p>
    <a href="/">Go Home</a>
    """, 500


# -----------------------------
# START APPLICATION
# -----------------------------

if __name__ == "__main__":
    init_database()
    app.run(debug=True)