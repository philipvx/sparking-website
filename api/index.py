from flask import Flask, render_template, send_from_directory

app = Flask(__name__, 
    template_folder='../templates',
    static_folder='../static'
)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    # Data demo lengkap sesuai template
    demo_user = "demo@example.com"
    demo_riwayat = [
        ("UIN Raden Fatah Kampus B", 2, "Motor", 7000, "2024-01-20 10:00", "2024-01-20 12:00", "completed", 1, "AB1234CD", "A1"),
        ("Palembang Trade Center", 3, "Mobil", 14000, "2024-01-20 14:00", None, "active", 2, "AB5678EF", "B2")
    ]
    demo_lokasi_data = [
        "UIN Raden Fatah Kampus B",
        "Palembang Trade Center", 
        "Mall Palembang Square",
        "Bandara Sultan Mahmud Badaruddin II"
    ]
    
    return render_template(
        'dashboard.html',
        user=demo_user,
        riwayat=demo_riwayat,
        saldo=50000,
        user_membership="Gold",
        user_points=1000,
        lokasi_data=demo_lokasi_data
    )

@app.route('/profile')
def profile():
    demo_user = {
        "email": "demo@example.com",
        "nama": "Demo User"
    }
    return render_template('profile.html', user=demo_user)

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/settings')
def settings():
    demo_user = {
        "email": "demo@example.com",
        "nama": "Demo User"
    }
    return render_template('settings.html', user=demo_user)

@app.route('/show_points')
def show_points():
    demo_user = {
        "email": "demo@example.com",
        "nama": "Demo User",
        "points": 1000
    }
    return render_template('show_points.html', user=demo_user)

@app.route('/all_reviews')
def all_reviews():
    return render_template('all_reviews.html')

@app.route('/logout')
def logout():
    return render_template('index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

if __name__ == '__main__':
    app.run()
