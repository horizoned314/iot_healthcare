import os
import psycopg2
from passlib.context import CryptContext
from dotenv import load_dotenv

# Load konfigurasi dari file .env
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Konfigurasi enkripsi password
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Data akun baru
username_baru = "dokter_a"
password_asli = "iot_healthcare314159"
email_baru = "dokter_a@mediot.com"
role_baru = "doctor"
nama_lengkap = "Dr. A"

# Enkripsi password
hashed_password = pwd_context.hash(password_asli)

print("Menyiapkan database...")

try:
    connection = psycopg2.connect(DATABASE_URL)
    cursor = connection.cursor()
    
    # --- 1. BUAT TABEL JIKA BELUM ADA ---
    create_table_query = """
    CREATE TABLE IF NOT EXISTS users (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        username VARCHAR(50) UNIQUE NOT NULL,
        email VARCHAR(100) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        role VARCHAR(20) NOT NULL,
        full_name VARCHAR(100) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    cursor.execute(create_table_query)
    connection.commit()
    print("✅ Tabel 'users' dipastikan sudah ada!")

    # --- 2. MASUKKAN DATA USER BARU ---
    print(f"Membuat user '{username_baru}'...")
    insert_query = """
        INSERT INTO users (username, email, password_hash, role, full_name) 
        VALUES (%s, %s, %s, %s, %s)
    """
    cursor.execute(insert_query, (username_baru, email_baru, hashed_password, role_baru, nama_lengkap))
    connection.commit()
    
    print("✅ AKUN BERHASIL DIBUAT!")
    print(f"Username : {username_baru}")
    print(f"Password : {password_asli}")

except psycopg2.IntegrityError:
    print("❌ GAGAL: Username atau Email sudah terdaftar di database.")
except Exception as e:
    print(f"❌ ERROR DATABASE: {e}")
finally:
    if "connection" in locals() and not connection.closed:
        cursor.close()
        connection.close()