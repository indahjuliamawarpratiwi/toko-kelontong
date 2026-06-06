from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)
DATABASE = 'toko_kelontong.db'

def get_db_connection():
    """Fungsi helper untuk membuka koneksi ke database SQLite."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Mengembalikan hasil query dalam bentuk dictionary/objek
    return conn

def init_db():
    """Inisialisasi database dan membuat tabel jika belum ada."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Tabel Barang
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS barang (
            id_barang INTEGER PRIMARY KEY AUTOINCREMENT,
            nama_barang TEXT NOT NULL,
            kategori TEXT,
            harga_beli REAL NOT NULL CHECK(harga_beli >= 0),
            harga_jual REAL NOT NULL CHECK(harga_jual >= 0),
            stok INTEGER NOT NULL DEFAULT 0 CHECK(stok >= 0),
            satuan TEXT NOT NULL,
            tanggal_masuk TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 2. Tabel Penjualan
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS penjualan (
            id_penjualan INTEGER PRIMARY KEY AUTOINCREMENT,
            tanggal TEXT DEFAULT CURRENT_TIMESTAMP,
            total_harga REAL NOT NULL
        )
    ''')
    
    # 3. Tabel Detail Penjualan
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS detail_penjualan (
            id_detail INTEGER PRIMARY KEY AUTOINCREMENT,
            id_penjualan INTEGER,
            id_barang INTEGER,
            jumlah INTEGER NOT NULL CHECK(jumlah > 0),
            subtotal REAL NOT NULL,
            FOREIGN KEY(id_penjualan) REFERENCES penjualan(id_penjualan) ON DELETE CASCADE,
            FOREIGN KEY(id_barang) REFERENCES barang(id_barang)
        )
    ''')
    
    # 4. Tabel Restok
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS restok (
            id_restok INTEGER PRIMARY KEY AUTOINCREMENT,
            id_barang INTEGER,
            jumlah_tambah INTEGER NOT NULL CHECK(jumlah_tambah > 0),
            tanggal TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(id_barang) REFERENCES barang(id_barang)
        )
    ''')
    conn.commit()
    conn.close()

# Jalankan inisialisasi database saat aplikasi start
init_db()

# ==========================================
# ROUTING HALAMAN UTAMA (FRONTEND RENDER)
# ==========================================

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/barang')
def halaman_barang():
    return render_template('barang.html')

@app.route('/kasir')
def halaman_kasir():
    return render_template('kasir.html')

@app.route('/restok')
def halaman_restok():
    return render_template('restok.html')

@app.route('/laporan')
def halaman_laporan():
    return render_template('laporan.html')


# ==========================================
# API ENDPOINTS
# ==========================================

# --- API DASHBOARD STATISTIK ---
@app.route('/api/dashboard', methods=['GET'])
def get_dashboard_stats():
    conn = get_db_connection()
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Total Jenis Barang
    total_jenis = conn.execute('SELECT COUNT(*) FROM barang').fetchone()[0]
    # Total Stok Barang
    total_stok = conn.execute('SELECT SUM(stok) FROM barang').fetchone()[0] or 0
    # Jumlah Transaksi Hari Ini
    tx_hari_ini = conn.execute("SELECT COUNT(*) FROM penjualan WHERE tanggal LIKE ?", (f'{today}%',)).fetchone()[0]
    # Barang Stok Menipis (< 10)
    stok_menipis = conn.execute('SELECT id_barang, nama_barang, stok, satuan FROM barang WHERE stok < 10').fetchall()
    stok_menipis_list = [dict(row) for row in stok_menipis]
    
    # Data Grafik Penjualan 7 Hari Terakhir
    grafik_data = conn.execute('''
        SELECT date(tanggal) as tgl, SUM(total_harga) as total 
        FROM penjualan 
        GROUP BY date(tanggal) 
        ORDER BY date(tanggal) DESC LIMIT 7
    ''').fetchall()
    
    labels = [row['tgl'] for row in reversed(grafik_data)]
    values = [row['total'] for row in reversed(grafik_data)]
    
    conn.close()
    return jsonify({
        "total_jenis": total_jenis,
        "total_stok": total_stok,
        "transaksi_hari_ini": tx_hari_ini,
        "stok_menipis": stok_menipis_list,
        "grafik": {"labels": labels, "values": values}
    })

# --- API CRUD BARANG ---
@app.route('/api/barang', methods=['GET', 'POST'])
def handle_barang():
    conn = get_db_connection()
    
    if request.method == 'GET':
        # Mendukung fitur cari berdasarkan nama atau kategori
        search = request.args.get('search', '')
        kategori = request.args.get('kategori', '')
        
        query = "SELECT * FROM barang WHERE 1=1"
        params = []
        if search:
            query += " AND nama_barang LIKE ?"
            params.append(f'%{search}%')
        if kategori:
            query += " AND kategori = ?"
            params.append(kategori)
            
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])
        
    elif request.method == 'POST':
        data = request.json
        # Validasi backend
        if not data.get('nama_barang'):
            return jsonify({"error": "Nama barang tidak boleh kosong"}), 400
        if float(data.get('harga_beli', 0)) < 0 or float(data.get('harga_jual', 0)) < 0:
            return jsonify({"error": "Harga tidak boleh kurang dari 0"}), 400
        if int(data.get('stok', 0)) < 0:
            return jsonify({"error": "Stok tidak boleh negatif"}), 400
            
        conn.execute('''
            INSERT INTO barang (nama_barang, kategori, harga_beli, harga_jual, stok, satuan)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (data['nama_barang'], data['kategori'], data['harga_beli'], data['harga_jual'], data['stok'], data['satuan']))
        conn.commit()
        conn.close()
        return jsonify({"message": "Barang berhasil ditambahkan!"}), 201

@app.route('/api/barang/<int:id>', methods=['PUT', 'DELETE'])
def update_delete_barang(id):
    conn = get_db_connection()
    
    if request.method == 'PUT':
        data = request.json
        if float(data.get('harga_beli', 0)) < 0 or float(data.get('harga_jual', 0)) < 0 or int(data.get('stok', 0)) < 0:
            return jsonify({"error": "Validasi nilai gagal (Input tidak boleh negatif)"}), 400
            
        conn.execute('''
            UPDATE barang SET nama_barang=?, kategori=?, harga_beli=?, harga_jual=?, stok=?, satuan=?
            WHERE id_barang=?
        ''', (data['nama_barang'], data['kategori'], data['harga_beli'], data['harga_jual'], data['stok'], data['satuan'], id))
        conn.commit()
        conn.close()
        return jsonify({"message": "Barang berhasil diperbarui!"})
        
    elif request.method == 'DELETE':
        conn.execute('DELETE FROM barang WHERE id_barang=?', (id,))
        conn.commit()
        conn.close()
        return jsonify({"message": "Barang berhasil dihapus!"})

# --- API TRANSAKSI PENJUALAN ---
@app.route('/api/penjualan', methods=['POST'])
def transaksi_penjualan():
    data = request.json  # Array berisi keranjang belanja: [{"id_barang": 1, "jumlah": 2}, ...]
    if not data:
        return jsonify({"error": "Keranjang kosong"}), 400
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        total_harga_transaksi = 0
        detail_items = []
        
        # Validasi stok terlebih dahulu untuk semua item di keranjang
        for item in data:
            barang = cursor.execute('SELECT * FROM barang WHERE id_barang = ?', (item['id_barang'],)).fetchone()
            if not barang:
                return jsonify({"error": f"Barang ID {item['id_barang']} tidak ditemukan"}), 404
            if barang['stok'] < item['jumlah']:
                return jsonify({"error": f"Stok tidak mencukupi untuk {barang['nama_barang']}. Sisa: {barang['stok']}"}), 400
                
            subtotal = barang['harga_jual'] * item['jumlah']
            total_harga_transaksi += subtotal
            detail_items.append({
                "id_barang": item['id_barang'],
                "jumlah": item['jumlah'],
                "subtotal": subtotal,
                "stok_baru": barang['stok'] - item['jumlah']
            })
            
        # Jika semua validasi lolos, masukkan data ke database
        cursor.execute('INSERT INTO penjualan (total_harga) VALUES (?)', (total_harga_transaksi,))
        id_penjualan = cursor.lastrowid
        
        for detail in detail_items:
            # Masukkan detail transaksi
            cursor.execute('''
                INSERT INTO detail_penjualan (id_penjualan, id_barang, jumlah, subtotal)
                VALUES (?, ?, ?, ?)
            ''', (id_penjualan, detail['id_barang'], detail['jumlah'], detail['subtotal']))
            
            # Kurangi stok otomatis
            cursor.execute('UPDATE barang SET stok = ? WHERE id_barang = ?', (detail['stok_baru'], detail['id_barang']))
            
        conn.commit()
        return jsonify({"message": "Transaksi Berhasil!", "id_penjualan": id_penjualan})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"Terjadi kesalahan sistem: {str(e)}"}), 500
    finally:
        conn.close()

# --- API RESTOK BARANG ---
@app.route('/api/restok', methods=['GET', 'POST'])
def handle_restok():
    conn = get_db_connection()
    if request.method == 'GET':
        # Mengambil riwayat restok digabung dengan nama barang
        rows = conn.execute('''
            SELECT r.id_restok, b.nama_barang, r.jumlah_tambah, r.tanggal 
            FROM restok r JOIN barang b ON r.id_barang = b.id_barang
            ORDER BY r.id_restok DESC
        ''').fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])
        
    elif request.method == 'POST':
        data = request.json
        id_barang = data.get('id_barang')
        jumlah_tambah = int(data.get('jumlah_tambah', 0))
        
        if jumlah_tambah <= 0:
            return jsonify({"error": "Jumlah tambah harus lebih dari 0"}), 400
            
        # Tambahkan ke tabel riwayat restok
        conn.execute('INSERT INTO restok (id_barang, jumlah_tambah) VALUES (?, ?)', (id_barang, jumlah_tambah))
        # Update/Tambahkan stok lama dengan stok baru di tabel barang
        conn.execute('UPDATE barang SET stok = stok + ? WHERE id_barang = ?', (jumlah_tambah, id_barang))
        
        conn.commit()
        conn.close()
        return jsonify({"message": "Berhasil menambahkan stok!"})

# --- API LAPORAN ---
@app.route('/api/laporan', methods=['GET'])
def get_laporan():
    filter_tipe = request.args.get('filter', 'harian') # harian, mingguan, bulanan
    conn = get_db_connection()
    
    # Penentuan filter waktu SQLite
    if filter_tipe == 'harian':
        time_filter = "date(p.tanggal) = date('now')"
    elif filter_tipe == 'mingguan':
        time_filter = "date(p.tanggal) >= date('now', '-7 days')"
    elif filter_tipe == 'bulanan':
        time_filter = "date(p.tanggal) >= date('now', '-30 days')"
    else:
        time_filter = "1=1"
        
    query = f'''
        SELECT p.tanggal, b.nama_barang, dp.jumlah, dp.subtotal as total_pendapatan
        FROM detail_penjualan dp
        JOIN penjualan p ON dp.id_penjualan = p.id_penjualan
        JOIN barang b ON dp.id_barang = b.id_barang
        WHERE {time_filter}
        ORDER BY p.tanggal DESC
    '''
    rows = conn.execute(query).fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')