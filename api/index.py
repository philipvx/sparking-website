from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__, 
    template_folder='../templates',
    static_folder='../static'
)

# Data statis untuk demo
DEMO_USER = {
    "email": "demo@example.com",
    "nama": "Demo User",
    "saldo": 50000,
    "membership_rank": "Gold",
    "points": 1000
}

DEMO_RIWAYAT = [
    {
        "lokasi": "UIN Raden Fatah Kampus B",
        "waktu": 2,
        "kendaraan": "Motor",
        "biaya": 7000,
        "status": "completed",
        "check_in_time": "2024-01-20 10:00",
        "check_out_time": "2024-01-20 12:00",
        "plat_nomor": "AB1234CD",
        "spot_number": "A1"
    }
]

DEMO_LOKASI = [
    "UIN Raden Fatah Kampus B",
    "Palembang Trade Center",
    "Mall Palembang Square",
    "Bandara SMB II"
]

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html',
        user=DEMO_USER,
        riwayat=DEMO_RIWAYAT,
        saldo=DEMO_USER['saldo'],
        user_membership=DEMO_USER['membership_rank'],
        user_points=DEMO_USER['points'],
        lokasi_data=DEMO_LOKASI
    )

@app.route('/profile')
def profile():
    return render_template('profile.html', user=DEMO_USER)

@app.route('/settings')
def settings():
    return render_template('settings.html', user=DEMO_USER)

@app.route('/show_points')
def show_points():
    return render_template('show_points.html', user=DEMO_USER)

@app.route('/logout')
def logout():
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run()
