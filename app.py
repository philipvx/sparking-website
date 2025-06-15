
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
import sys
import logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, force=True)

import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import pytz
import os

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['SECRET_KEY'] = 'secret_key_here'

# Konfigurasi upload folder
UPLOAD_FOLDER = 'static/images/profile'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Pastikan folder upload ada
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def enable_wal_mode():
    conn = sqlite3.connect('sparking.db')
    c = conn.cursor()
    c.execute('PRAGMA journal_mode=WAL;')
    wal_mode = c.fetchone()
    c.execute('PRAGMA journal_mode;')
    current_mode = c.fetchone()
    conn.close()
    print(f"SQLite WAL mode set: {wal_mode}, current mode: {current_mode}")

enable_wal_mode()

app.jinja_env.globals.update(enumerate=enumerate)

logged_in_user = None

# Konstanta harga parkir
HARGA_PARKIR = {
    'Motor': {'dasar': 3000, 'per_jam': 2000},  # Rp 3.000 + Rp 2.000/jam
    'Mobil': {'dasar': 5000, 'per_jam': 3000}   # Rp 5.000 + Rp 3.000/jam
}

def hitung_biaya(waktu, kendaraan):
    """Hitung biaya parkir berdasarkan durasi dan jenis kendaraan"""
    tarif = HARGA_PARKIR[kendaraan]
    if waktu <= 1:
        return tarif['dasar']
    return tarif['dasar'] + (waktu - 1) * tarif['per_jam']

def get_user_saldo(email):
    """Dapatkan saldo user"""
    conn = sqlite3.connect('sparking.db')
    c = conn.cursor()
    c.execute("SELECT saldo FROM users WHERE email=?", (email,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def is_admin(email):
    """Cek apakah user adalah admin"""
    conn = sqlite3.connect('sparking.db')
    c = conn.cursor()
    c.execute("SELECT is_admin FROM users WHERE email=?", (email,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def get_all_users():
    """Dapatkan daftar semua user untuk halaman admin"""
    with sqlite3.connect('sparking.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute("SELECT email, saldo, is_admin, membership_rank, points FROM users")
        users = []
        for row in c.fetchall():
            users.append({
                'email': row[0],
                'saldo': row[1],
                'is_admin': row[2],
                'membership_rank': row[3] if len(row) > 3 else 'Bronze',
                'points': row[4] if len(row) > 4 else 0
            })
    return users

def get_all_bookings():
    """Dapatkan semua riwayat pemesanan untuk halaman admin"""
    with sqlite3.connect('sparking.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute("""
            SELECT user_email, lokasi, kendaraan, waktu, biaya, check_in_time, check_out_time, status, id, metode_pembayaran, payment_status, plat_nomor, spot_number
            FROM pesan_parkir 
            ORDER BY check_in_time DESC""")
        bookings = []
        for row in c.fetchall():
            bookings.append({
                'user_email': row[0],
                'lokasi': row[1],
                'kendaraan': row[2],
                'waktu': row[3],
                'biaya': row[4],
                'check_in_time': row[5],
                'check_out_time': row[6],
                'status': row[7],
                'id': row[8],
                'metode_pembayaran': row[9],
                'payment_status': row[10],
                'plat_nomor': row[11],
                'spot_number': row[12]
            })
    return bookings

def topup_saldo(user_email, amount):
    """Top up saldo user"""
    with sqlite3.connect('sparking.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET saldo = saldo + ? WHERE email=?", (amount, user_email))
        conn.commit()

def determine_membership_rank(points):
    if points >= 100000:
        return 'Mythical'
    elif points >= 15000 and points < 100000:
        return 'Gold'
    elif points >= 5000 and points < 15000:
        return 'Silver'
    else:
        return 'Bronze'

def simpan_pesan(lokasi, waktu, user_email, kendaraan, metode_pembayaran, plat_nomor):
    # Validasi input
    valid_kendaraan = ['Motor', 'Mobil']
    valid_metode = ['saldo', 'tunai', 'e-wallet', 'QRIS']
    if kendaraan not in valid_kendaraan:
        return None, None, "Jenis kendaraan tidak valid"
    if metode_pembayaran not in valid_metode:
        return None, None, "Metode pembayaran tidak valid"
    if not isinstance(waktu, int) and not (isinstance(waktu, str) and waktu.isdigit()):
        return None, None, "Waktu harus berupa angka"
    if not plat_nomor or len(plat_nomor.strip()) < 3:
        return None, None, "Plat nomor tidak valid"

    waktu_int = int(waktu)
    biaya = hitung_biaya(waktu_int, kendaraan)
    conn = sqlite3.connect('sparking.db')
    c = conn.cursor()

    try:
        # Cek saldo jika metode saldo
        if metode_pembayaran == 'saldo':
            c.execute("SELECT saldo FROM users WHERE email=?", (user_email,))
            result = c.fetchone()
            saldo = result[0] if result else 0
            if saldo < biaya:
                conn.close()
                return None, "Saldo tidak mencukupi"
            c.execute("UPDATE users SET saldo = saldo - ? WHERE email=?", (biaya, user_email))

        # Hitung poin dan membership
        c.execute("SELECT membership_rank, points FROM users WHERE email=?", (user_email,))
        user_data = c.fetchone()
        membership_rank = user_data[0] if user_data else 'Bronze'
        current_points = user_data[1] if user_data else 0

        multiplier_map = {
            'Bronze': 1.0,
            'Silver': 1.5,
            'Gold': 2.0,
            'Mythical': 2.5
        }
        multiplier = multiplier_map.get(membership_rank, 1.0)
        points_earned = int((biaya / 1000) * 50 * multiplier)

        logging.debug(f"User: {user_email}, Membership: {membership_rank}, Current Points: {current_points}, Points Earned: {points_earned}")

        if points_earned > 0:
            try:
                new_points = current_points + points_earned
                c.execute("UPDATE users SET points = ? WHERE email=?", (new_points, user_email))
                logging.debug(f"Updated points to {new_points} for user {user_email}")
                new_rank = determine_membership_rank(new_points)
                if new_rank != membership_rank:
                    c.execute("UPDATE users SET membership_rank = ? WHERE email=?", (new_rank, user_email))
                    logging.debug(f"Updated membership rank to {new_rank} for user {user_email}")
                else:
                    logging.debug(f"Membership rank remains {membership_rank} for user {user_email}")
            except Exception as e:
                logging.error(f"Failed to update points or membership rank for user {user_email}: {e}")

        # Assign a random available parking spot for the location
        c.execute("SELECT spot_number FROM parking_spots WHERE lokasi=? AND is_occupied=0", (lokasi,))
        available_spots = [row[0] for row in c.fetchall()]
        if not available_spots:
            conn.close()
            return None, "Tempat parkir penuh di lokasi ini"
        import random
        assigned_spot = random.choice(available_spots)

        # Mark the spot as occupied
        c.execute("UPDATE parking_spots SET is_occupied=1 WHERE lokasi=? AND spot_number=?", (lokasi, assigned_spot))

        import pytz
        local_tz = pytz.timezone('Asia/Jakarta')
        now_local = datetime.now(local_tz)
        now_local_str = now_local.strftime('%Y-%m-%d %H:%M:%S')
        logging.debug(f"Local time for check_in_time: {now_local_str}")

        c.execute("""
            INSERT INTO pesan_parkir 
            (lokasi, waktu, user_email, kendaraan, biaya, check_in_time, status, metode_pembayaran, payment_status, plat_nomor, spot_number) 
            VALUES (?, ?, ?, ?, ?, ?, 'active', ?, 'completed', ?, ?)""", 
            (lokasi, waktu_int, user_email, kendaraan, biaya, now_local_str, metode_pembayaran, plat_nomor, assigned_spot))
        conn.commit()
    except Exception as e:
        logging.error(f"Error in simpan_pesan: {e}", exc_info=True)
        conn.close()
        return None, f"Error saat menyimpan pesanan: {e}"
    conn.close()
    return biaya, assigned_spot, "Pesanan berhasil"

def create_user_table():
    conn = sqlite3.connect('sparking.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users
        (email TEXT PRIMARY KEY, password TEXT)
    ''')
    conn.commit()
    conn.close()

create_user_table()

def create_pesan_table():
    conn = sqlite3.connect('sparking.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS pesan_parkir (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lokasi TEXT NOT NULL,
            waktu INTEGER NOT NULL,
            user_email TEXT NOT NULL,
            kendaraan TEXT NOT NULL,
            biaya INTEGER NOT NULL,
            FOREIGN KEY(user_email) REFERENCES users(email)
        )
    ''')
    conn.commit()
    conn.close()

create_pesan_table()

def ambil_riwayat(user_email):
    conn = sqlite3.connect('sparking.db')
    c = conn.cursor()
    c.execute("""
        SELECT lokasi, waktu, kendaraan, biaya, check_in_time, check_out_time, status, id, plat_nomor, spot_number
        FROM pesan_parkir 
        WHERE user_email=? 
        ORDER BY check_in_time DESC""", (user_email,))
    data = c.fetchall()
    conn.close()
    return data

def checkout_parkir(parkir_id):
    """Proses checkout parkir"""
    import pytz
    local_tz = pytz.timezone('Asia/Jakarta')
    now_local = datetime.now(local_tz)
    now_local_str = now_local.strftime('%Y-%m-%d %H:%M:%S')
    with sqlite3.connect('sparking.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute("""
            UPDATE pesan_parkir 
            SET status='completed', check_out_time=? 
            WHERE id=? AND status='active'""", (now_local_str, parkir_id))
        success = c.rowcount > 0
        conn.commit()
    return success

def daftar_user(email, password):
    conn = sqlite3.connect('sparking.db')
    c = conn.cursor()
    c.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, generate_password_hash(password)))
    conn.commit()
    conn.close()

def cek_login(email, password):
    conn = sqlite3.connect('sparking.db')
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE email=?", (email,))
    hashed_password = c.fetchone()
    if hashed_password and check_password_hash(hashed_password[0], password):
        return True
    return False

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/home')
def landing():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    if cek_login(email, password):
        session['user'] = email  # Simpan user ke session
        # Cek apakah user adalah admin
        if is_admin(email):
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('dashboard'))
    else:
        flash('Login gagal. Coba lagi.')
        return redirect(url_for('home'))

@app.route('/daftar', methods=['POST'])
def daftar():
    email = request.form['email']
    password = request.form['password']
    daftar_user(email, password)
    flash('Pendaftaran berhasil!')
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    import pytz
    from datetime import datetime

    if 'user' in session:
        riwayat = ambil_riwayat(session['user'])
        saldo = get_user_saldo(session['user'])
        lokasi_data = [
            "UIN Raden Fatah Kampus B Jakabaring",
            "Rumah Sakit Charitas",
            "Universitas Sriwijaya Indralaya",
            "PTC(Palembang Trade Center)Mall",
            "PIM(Palembang Indah Mall)",
            "Hotel Harper",
            "Hotel The Zuri",
            "Transmart Palembang",
            "PS(Palembang Square)",
            "RSUD Mohammad Husein"
        ]
        # Convert check_out_time string to Jakarta timezone datetime object
        jakarta_tz = pytz.timezone('Asia/Jakarta')
        riwayat_converted = []
        for record in riwayat:
            check_out_str = record[5]
            if check_out_str:
                try:
                    # Parse string to datetime assuming UTC
                    dt_utc = datetime.strptime(check_out_str, '%Y-%m-%d %H:%M:%S')
                    dt_utc = pytz.utc.localize(dt_utc)
                    dt_local = dt_utc.astimezone(jakarta_tz)
                    check_out_local_str = dt_local.strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    check_out_local_str = check_out_str
            else:
                check_out_local_str = None
            # Replace check_out_time with converted string
            record_list = list(record)
            record_list[5] = check_out_local_str
            # Ensure spot_number is preserved correctly (index 9)
            if len(record_list) < 10:
                record_list.append(None)
            riwayat_converted.append(tuple(record_list))

        # Fetch membership rank and points for current user
        conn = sqlite3.connect('sparking.db')
        c = conn.cursor()
        c.execute("SELECT membership_rank, points FROM users WHERE email=?", (session['user'],))
        user_data = c.fetchone()
        conn.close()
        user_membership = user_data[0] if user_data else 'Bronze'
        user_points = user_data[1] if user_data else 0

        # Debug log riwayat_converted with spot_number
        for rec in riwayat_converted:
            logging.debug(f"Riwayat record: lokasi={rec[0]}, waktu={rec[1]}, kendaraan={rec[2]}, biaya={rec[3]}, check_in={rec[4]}, check_out={rec[5]}, status={rec[6]}, id={rec[7]}, plat_nomor={rec[8]}, spot_number={rec[9] if len(rec) > 9 else 'N/A'}")

        return render_template(
            'dashboard.html',
            user=session['user'],
            riwayat=riwayat_converted,
            lokasi_data=lokasi_data,
            saldo=saldo,
            user_membership=user_membership,
            user_points=user_points
        )
    else:
        return redirect(url_for('home'))


@app.route('/hapus_riwayat', methods=['POST'])
def hapus_riwayat():
    if 'user' not in session:
        return redirect(url_for('home'))
    
    user_email = session['user']
    conn = sqlite3.connect('sparking.db')
    c = conn.cursor()
    c.execute("DELETE FROM pesan_parkir WHERE user_email=?", (user_email,))
    conn.commit()
    conn.close()
    
    flash('Riwayat pesanan berhasil dihapus.')
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.pop('user', None)  # Hapus data login dari session
    return redirect(url_for('home'))

@app.route('/pesan', methods=['POST'])
def pesan():
    try:
        if 'user' not in session:
            return redirect(url_for('home'))

        lokasi = request.form['lokasi']
        waktu = request.form['waktu']
        kendaraan = request.form['kendaraan']
        metode_pembayaran = request.form['metode_pembayaran']
        plat_nomor = request.form['plat_nomor']
        user_email = session['user']

        logging.debug(f"Received booking request: lokasi={lokasi}, waktu={waktu}, kendaraan={kendaraan}, metode_pembayaran={metode_pembayaran}, plat_nomor={plat_nomor}, user_email={user_email}")
        
        result = simpan_pesan(lokasi, waktu, user_email, kendaraan, metode_pembayaran, plat_nomor)
        
        if result[0] is None:  # Saldo tidak mencukupi or other failure
            logging.error(f"Booking failed: {result[2]}")
            flash(result[2])
            return redirect(url_for('dashboard'))
        
        biaya = result[0]
        spot_number = result[1]
        return render_template('sukses.html', lokasi=lokasi, waktu=waktu, kendaraan=kendaraan, biaya=biaya, metode_pembayaran=metode_pembayaran, plat_nomor=plat_nomor, spot_number=spot_number)
    except Exception as e:
        logging.error(f"Unhandled exception in /pesan: {e}", exc_info=True)
        logging.debug(f"Request form data: {request.form}")
        flash("Terjadi kesalahan pada server saat memproses pesanan.")
        return redirect(url_for('dashboard'))

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/admin')
def admin_dashboard():
    if 'user' not in session:
        return redirect(url_for('home'))
    
    if not is_admin(session['user']):
        flash('Akses ditolak. Anda bukan admin.')
        return redirect(url_for('dashboard'))
    
    users = get_all_users()
    bookings = get_all_bookings()

    # Fetch user feedbacks
    conn = sqlite3.connect('sparking.db')
    c = conn.cursor()
    c.execute('''
        SELECT id, user_email, lokasi, rating, review_text, created_at, admin_reply
        FROM user_reviews
        ORDER BY created_at DESC
    ''')
    feedbacks = c.fetchall()
    conn.close()

    return render_template('admin.html', user=session['user'], users=users, bookings=bookings, feedbacks=feedbacks)

@app.route('/admin/update_membership', methods=['POST'])
def admin_update_membership():
    if 'user' not in session or not is_admin(session['user']):
        return redirect(url_for('home'))
    
    user_email = request.form.get('user_email')
    new_rank = request.form.get('membership_rank')
    
    if not user_email or not new_rank:
        flash('Data tidak lengkap untuk update membership.')
        return redirect(url_for('admin_dashboard'))
    
    valid_ranks = ['Bronze', 'Silver', 'Gold', 'Mythical']
    if new_rank not in valid_ranks:
        flash('Pangkat membership tidak valid.')
        return redirect(url_for('admin_dashboard'))
    
    conn = sqlite3.connect('sparking.db')
    c = conn.cursor()
    c.execute("UPDATE users SET membership_rank = ? WHERE email = ?", (new_rank, user_email))
    conn.commit()
    conn.close()
    
    flash(f'Membership {user_email} berhasil diupdate ke {new_rank}.')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/topup', methods=['POST'])
def admin_topup():
    if 'user' not in session or not is_admin(session['user']):
        return redirect(url_for('home'))
    
    user_email = request.form['user_email']
    amount = int(request.form['amount'])
    
    topup_saldo(user_email, amount)
    flash(f'Berhasil top up saldo {user_email} sebesar Rp {amount:,}')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_user', methods=['POST'])
def admin_delete_user():
    if 'user' not in session or not is_admin(session['user']):
        return redirect(url_for('home'))
    
    user_email = request.form['user_email']
    
    # Pastikan tidak menghapus admin
    if is_admin(user_email):
        flash('Tidak dapat menghapus akun admin.')
        return redirect(url_for('admin_dashboard'))
    
    # Hapus riwayat pemesanan user terlebih dahulu
    conn = sqlite3.connect('sparking.db')
    c = conn.cursor()
    c.execute("DELETE FROM pesan_parkir WHERE user_email=?", (user_email,))
    
    # Hapus user dari tabel users
    c.execute("DELETE FROM users WHERE email=?", (user_email,))
    conn.commit()
    conn.close()
    
    flash(f'Akun pengguna {user_email} berhasil dihapus.')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/update_membership_rank', methods=['POST'])
def update_membership_rank():
    if 'user' not in session or not is_admin(session['user']):
        return redirect(url_for('home'))
    
    user_email = request.form.get('user_email')
    new_rank = request.form.get('membership_rank')
    
    if not user_email or not new_rank:
        flash('Data tidak lengkap untuk memperbarui pangkat membership.')
        return redirect(url_for('admin_dashboard'))
    
    conn = sqlite3.connect('sparking.db')
    c = conn.cursor()
    c.execute("UPDATE users SET membership_rank = ? WHERE email = ?", (new_rank, user_email))
    conn.commit()
    conn.close()
    
    flash(f'Pangkat membership untuk {user_email} berhasil diperbarui menjadi {new_rank}.')
    return redirect(url_for('admin_dashboard'))

import time
import sqlite3
import threading
import logging

checkout_lock = threading.Lock()

@app.route('/checkout', methods=['POST'])
def checkout():
    import pytz
    utc_tz = pytz.utc

    user = session.get('user')
    if not user:
        return redirect(url_for('home'))
    
    parkir_id = request.form['parkir_id']

    success = False
    message = ''

    with checkout_lock:
        max_retries = 10
        retry_delay = 0.5  # seconds

        for attempt in range(max_retries):
            try:
                now_utc = datetime.utcnow()
                now_utc_str = now_utc.strftime('%Y-%m-%d %H:%M:%S')

                with sqlite3.connect('sparking.db', timeout=10) as conn:
                    c = conn.cursor()
                    # Get spot_number for this booking
                    c.execute("SELECT spot_number FROM pesan_parkir WHERE id=? AND status='active'", (parkir_id,))
                    row = c.fetchone()
                    if row:
                        spot_number = row[0]
                        # Free the spot
                        c.execute("UPDATE parking_spots SET is_occupied=0 WHERE spot_number=? AND lokasi=(SELECT lokasi FROM pesan_parkir WHERE id=?)", (spot_number, parkir_id))
                    else:
                        spot_number = None

                    # Inline checkout_parkir logic here to avoid multiple connections
                    c.execute("""
                        UPDATE pesan_parkir 
                        SET status='completed', check_out_time=? 
                        WHERE id=? AND status='active'""", (now_utc_str, parkir_id))
                    success = c.rowcount > 0
                    
                    conn.commit()
                break  # success, exit retry loop
            except sqlite3.OperationalError as e:
                logging.error(f"SQLite OperationalError on attempt {attempt+1}: {e}")
                if 'database is locked' in str(e):
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    else:
                        message = 'Checkout gagal karena database terkunci. Silakan coba lagi.'
                        break
                else:
                    raise

    if success:
        message = 'Checkout berhasil!'
    elif not message:
        message = 'Checkout gagal. Parkir tidak ditemukan atau sudah selesai.'

    flash(message)
    return redirect(url_for('dashboard'))

from flask import jsonify, render_template, request, session, redirect, url_for, flash

def get_user_booking_locations(user_email):
    conn = sqlite3.connect('sparking.db')
    c = conn.cursor()
    c.execute('''
        SELECT DISTINCT lokasi FROM pesan_parkir WHERE user_email = ?
    ''', (user_email,))
    locations = [row[0] for row in c.fetchall()]
    conn.close()
    return locations

@app.route('/submit_review', methods=['POST'])
def submit_review():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_email = session['user']
    lokasi = request.form.get('lokasi')
    rating = request.form.get('rating')
    review_text = request.form.get('review_text', '')

    # Check if lokasi is in user's booking history
    user_locations = get_user_booking_locations(user_email)
    if lokasi not in user_locations:
        return jsonify({'error': 'Lokasi tidak valid untuk pengguna ini'}), 400

    if not lokasi or not rating:
        return jsonify({'error': 'Lokasi dan rating wajib diisi'}), 400

    try:
        rating = int(rating)
        if rating < 1 or rating > 5:
            raise ValueError
    except ValueError:
        return jsonify({'error': 'Rating harus antara 1 sampai 5'}), 400

    conn = sqlite3.connect('sparking.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO user_reviews (user_email, lokasi, rating, review_text)
        VALUES (?, ?, ?, ?)
    ''', (user_email, lokasi, rating, review_text))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Review berhasil disimpan'})

@app.route('/get_reviews/<lokasi>', methods=['GET'])
def get_reviews(lokasi):
    conn = sqlite3.connect('sparking.db')
    c = conn.cursor()
    c.execute('''
        SELECT user_email, rating, review_text, created_at, admin_reply
        FROM user_reviews
        WHERE lokasi = ?
        ORDER BY created_at DESC
    ''', (lokasi,))
    reviews = [{
        'user_email': row[0],
        'rating': row[1],
        'review_text': row[2],
        'created_at': row[3],
        'admin_reply': row[4]
    } for row in c.fetchall()]
    conn.close()
    return jsonify(reviews)

@app.route('/admin/feedbacks')
def admin_feedbacks():
    if 'user' not in session or not is_admin(session['user']):
        flash('Akses ditolak. Anda bukan admin.')
        return redirect(url_for('home'))

    conn = sqlite3.connect('sparking.db')
    c = conn.cursor()
    c.execute('''
        SELECT id, user_email, lokasi, rating, review_text, created_at, admin_reply
        FROM user_reviews
        ORDER BY created_at DESC
    ''')
    feedbacks = c.fetchall()
    conn.close()
    return render_template('admin_feedbacks.html', feedbacks=feedbacks)

@app.route('/reviews')
def all_reviews():
    if 'user' not in session:
        return redirect(url_for('home'))

    conn = sqlite3.connect('sparking.db')
    c = conn.cursor()
    c.execute('''
        SELECT id, user_email, lokasi, rating, review_text, created_at, admin_reply
        FROM user_reviews
        ORDER BY created_at DESC
    ''')
    reviews = c.fetchall()
    conn.close()
    return render_template('all_reviews.html', reviews=reviews, current_user=session['user'])

@app.route('/public_reviews')
def public_reviews():
    conn = sqlite3.connect('sparking.db')
    c = conn.cursor()
    c.execute('''
        SELECT id, user_email, lokasi, rating, review_text, created_at, admin_reply
        FROM user_reviews
        ORDER BY created_at DESC
    ''')
    reviews = c.fetchall()
    conn.close()
    return render_template('public_reviews.html', reviews=reviews)

@app.route('/delete_review', methods=['POST'])
def delete_review():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    review_id = request.form.get('review_id')
    if not review_id:
        return jsonify({'error': 'Review ID wajib diisi'}), 400

    conn = sqlite3.connect('sparking.db')
    c = conn.cursor()
    c.execute('SELECT user_email FROM user_reviews WHERE id = ?', (review_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Review tidak ditemukan'}), 404

    review_owner = row[0]
    current_user = session['user']
    if current_user != review_owner and not is_admin(current_user):
        conn.close()
        return jsonify({'error': 'Tidak memiliki izin untuk menghapus review ini'}), 403

    c.execute('DELETE FROM user_reviews WHERE id = ?', (review_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Review berhasil dihapus'})

@app.route('/admin/reply_feedback', methods=['POST'])
def admin_reply_feedback():
    if 'user' not in session or not is_admin(session['user']):
        return jsonify({'error': 'Unauthorized'}), 401

    feedback_id = request.form.get('feedback_id')
    admin_reply = request.form.get('admin_reply', '')

    if not feedback_id:
        return jsonify({'error': 'Feedback ID wajib diisi'}), 400

    conn = sqlite3.connect('sparking.db')
    c = conn.cursor()
    c.execute('''
        UPDATE user_reviews SET admin_reply = ? WHERE id = ?
    ''', (admin_reply, feedback_id))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Balasan berhasil disimpan'})

@app.route('/show_points')
def show_points():
    if 'user' not in session:
        return redirect(url_for('home'))
    user_email = session['user']
    conn = sqlite3.connect('sparking.db')
    c = conn.cursor()
    c.execute("SELECT membership_rank, points FROM users WHERE email=?", (user_email,))
    user_data = c.fetchone()
    conn.close()
    membership_rank = user_data[0] if user_data else 'Bronze'
    points = user_data[1] if user_data else 0
    return render_template('show_points.html', user=user_email, membership_rank=membership_rank, points=points)

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/upload_profile_picture', methods=['POST'])
def upload_profile_picture():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    if 'profile_picture' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
        
    file = request.files['profile_picture']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Gunakan email user sebagai nama file untuk menghindari duplikasi
        extension = filename.rsplit('.', 1)[1].lower()
        new_filename = f"{session['user']}.{extension}"
        
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], new_filename))
        
        # Update profile picture path di database
        conn = sqlite3.connect('sparking.db')
        c = conn.cursor()
        c.execute("UPDATE users SET profile_picture = ? WHERE email = ?", 
                 (f"/uploads/{new_filename}", session['user']))
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Profile picture updated successfully',
            'path': f"/uploads/{new_filename}"
        })
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/profile')
def profile():
    if 'user' not in session:
        return redirect(url_for('home'))
    
    user_email = session['user']
    conn = sqlite3.connect('sparking.db')
    c = conn.cursor()
    c.execute("""
        SELECT email, saldo, membership_rank, points, full_name, phone_number, profile_picture 
        FROM users WHERE email=?
    """, (user_email,))
    user_data = c.fetchone()
    conn.close()
    
    if user_data:
        user_info = {
            'email': user_data[0],
            'saldo': user_data[1] if user_data[1] else 0,
            'membership_rank': user_data[2] if user_data[2] else 'Bronze',
            'points': user_data[3] if user_data[3] else 0,
            'full_name': user_data[4] if user_data[4] else '',
            'phone_number': user_data[5] if user_data[5] else '',
            'profile_picture': user_data[6] if user_data[6] else '/static/images/default-avatar.png'
        }
    else:
        user_info = {
            'email': user_email,
            'saldo': 0,
            'membership_rank': 'Bronze',
            'points': 0,
            'full_name': '',
            'phone_number': '',
            'profile_picture': '/static/images/default-avatar.png'
        }
    
    return render_template('profile.html', user_info=user_info)

@app.route('/settings')
def settings():
    if 'user' not in session:
        return redirect(url_for('home'))
    
    user_email = session['user']
    conn = sqlite3.connect('sparking.db')
    c = conn.cursor()
    c.execute("""
        SELECT email, full_name, phone_number, profile_picture 
        FROM users WHERE email=?
    """, (user_email,))
    user_data = c.fetchone()
    conn.close()
    
    if user_data:
        user_info = {
            'email': user_data[0],
            'full_name': user_data[1] if user_data[1] else '',
            'phone_number': user_data[2] if user_data[2] else '',
            'profile_picture': user_data[3] if user_data[3] else '/static/images/default-avatar.png'
        }
    else:
        user_info = {
            'email': user_email,
            'full_name': '',
            'phone_number': '',
            'profile_picture': '/static/images/default-avatar.png'
        }
    
    return render_template('settings.html', user_info=user_info)

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_email = session['user']
    full_name = request.form.get('full_name', '').strip()
    phone_number = request.form.get('phone_number', '').strip()
    
    # Validasi input
    if len(full_name) > 100:
        return jsonify({'error': 'Nama lengkap terlalu panjang (maksimal 100 karakter)'}), 400
    
    if phone_number and (len(phone_number) < 10 or len(phone_number) > 15):
        return jsonify({'error': 'Nomor telepon harus antara 10-15 digit'}), 400
    
    # Update database
    conn = sqlite3.connect('sparking.db')
    c = conn.cursor()
    c.execute("""
        UPDATE users SET full_name = ?, phone_number = ? WHERE email = ?
    """, (full_name, phone_number, user_email))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Profil berhasil diperbarui'})

if __name__ == '__main__':
    app.run(debug=True, threaded=False, processes=1)
