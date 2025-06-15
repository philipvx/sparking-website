from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
import os
from datetime import datetime
import pytz
from functools import wraps

app = Flask(__name__, 
    template_folder='../templates',  # Penting: path ke templates
    static_folder='../static'        # Penting: path ke static files
)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'sparking-demo-2024')

# Data statis untuk demo
DEMO_DATA = {
    "user": {
        "email": "demo@example.com",
        "nama": "Demo User",
        "saldo": 50000,
        "membership_rank": "Gold",
        "points": 1000,
        "profile_pic": "/static/images/default-avatar.png"
    },
    "riwayat": [
        {
            "lokasi": "UIN Raden Fatah Kampus B",
            "waktu": 2,
            "kendaraan": "Motor",
            "biaya": 7000,
            "status": "completed",
            "check_in_time": "2024-01-20 10:00:00",
            "check_out_time": "2024-01-20 12:00:00"
        },
        {
            "lokasi": "Palembang Trade Center",
            "waktu": 3,
            "kendaraan": "Mobil",
            "biaya": 14000,
            "status": "active",
            "check_in_time": "2024-01-20 14:00:00",
            "check_out_time": None
        }
    ]
}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Set session untuk demo
        session['user'] = DEMO_DATA['user']
        flash('Login berhasil!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Anda telah logout', 'info')
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', 
                         user=session['user'],
                         riwayat=DEMO_DATA['riwayat'],
                         saldo=DEMO_DATA['user']['saldo'],
                         user_membership=DEMO_DATA['user']['membership_rank'],
                         user_points=DEMO_DATA['user']['points'])

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', 
                         user=session['user'])

@app.route('/admin')
@login_required
def admin():
    return render_template('admin.html',
                         bookings=DEMO_DATA['riwayat'],
                         user=session['user'])

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html',
                         user=session['user'])

@app.route('/show_points')
@login_required
def show_points():
    return render_template('show_points.html',
                         user=session['user'])

# Handler untuk static files
@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

if __name__ == '__main__':
    app.run(debug=True)
