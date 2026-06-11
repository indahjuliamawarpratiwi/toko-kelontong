from flask import Flask, render_template, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import os

app = Flask(__name__)

# Mengambil URL Database dari Environment Variable di Render nanti
DATABASE_URL = os.environ.get('DATABASE_URL', 'SALIN_URI_SUPABASE_ANDA_DI_SINI_UNTUK_TEST_LOKAL')

def get_db_connection():
    """Membuka koneksi ke PostgreSQL Supabase."""
    conn = psycopg2.connect(DATABASE_URL)
    return conn

# =========================================================================
# CATATAN: Ubah semua 'sqlite3.Row' di fungsi API Anda menjadi RealDictCursor
# Contoh modifikasi salah satu API untuk PostgreSQL:
# =========================================================================

@app.route('/api/barang', methods=['GET', 'POST'])
def api_barang():
    conn = get_db_connection()
    # Menggunakan RealDictCursor agar hasil query berupa dictionary otomatis
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    if request.method == 'GET':
        search = request.args.get('search', '')
        query = "SELECT * FROM barang WHERE 1=1"
        params = []
        if search:
            query += " AND nama_barang ILIKE %s" # PostgreSQL menggunakan ILIKE & %s
            params.append(f"%{search}%")
            
        cursor.execute(query, params)
        barang = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(barang)
        
    elif request.method == 'POST':
        data = request.json
        cursor.execute('''
            INSERT INTO barang (nama_barang, kategori, harga_beli, harga_jual, stok, satuan)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (data['nama_barang'], data['kategori'], data['harga_beli'], data['harga_jual'], data['stok'], data['satuan']))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Barang sukses ditambahkan!"}), 201

# Lakukan penyesuaian tanda "?" menjadi "%s" pada query SQL di endpoint lainnya.