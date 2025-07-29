from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import timedelta

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # important for session
app.permanent_session_lifetime = timedelta(days=7)  # for 'remember me'

DB_NAME = "notes.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        conn.commit()

# Home
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

# Signup
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        with get_db_connection() as conn:
            try:
                conn.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", 
                             (username, email, password))
                conn.commit()
                flash('Account created! Please log in.', 'success')
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                flash('Email already exists.', 'danger')

    return render_template('signup.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        remember = 'remember' in request.form

        with get_db_connection() as conn:
            user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            if user and check_password_hash(user['password'], password):
                session.permanent = remember
                session['user_id'] = user['id']
                session['username'] = user['username']
                flash('Welcome back!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid email or password.', 'danger')

    return render_template('login.html')

# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

# Dashboard / Notes List
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    with get_db_connection() as conn:
        notes = conn.execute("SELECT * FROM notes WHERE user_id = ? ORDER BY created_at DESC", 
                             (session['user_id'],)).fetchall()
    return render_template('dashboard.html', notes=notes)

# Add Note
@app.route('/add', methods=['GET', 'POST'])
def add_note():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        with get_db_connection() as conn:
            conn.execute("INSERT INTO notes (user_id, title, content) VALUES (?, ?, ?)",
                         (session['user_id'], title, content))
            conn.commit()
        flash('Note added!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('add_note.html')

# Delete Note
@app.route('/delete/<int:id>', methods=['POST'])
def delete_note(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    with get_db_connection() as conn:
        conn.execute("DELETE FROM notes WHERE id = ? AND user_id = ?", (id, session['user_id']))
        conn.commit()
    flash('Note deleted.', 'info')
    return redirect(url_for('dashboard'))

# Edit Note
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_note(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    with get_db_connection() as conn:
        note = conn.execute("SELECT * FROM notes WHERE id = ? AND user_id = ?", 
                            (id, session['user_id'])).fetchone()

        if not note:
            flash('Note not found.', 'warning')
            return redirect(url_for('dashboard'))

        if request.method == 'POST':
            title = request.form['title']
            content = request.form['content']
            conn.execute("UPDATE notes SET title = ?, content = ? WHERE id = ? AND user_id = ?",
                         (title, content, id, session['user_id']))
            conn.commit()
            flash('Note updated!', 'success')
            return redirect(url_for('dashboard'))

    return render_template('edit_note.html', note=note)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
