from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
import os
from datetime import datetime
import pytz

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        return jsonify({"message": "Demo mode - Login successful"}), 200
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html', 
                         user="demo@example.com",
                         riwayat=[],
                         saldo=50000,
                         user_membership="Gold",
                         user_points=1000)

# Tambahkan route lain yang diperlukan untuk demo
@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/profile')
def profile():
    return render_template('profile.html')

# Handler untuk static files
@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

if __name__ == '__main__':
    app.run(debug=True)
