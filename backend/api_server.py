import os
from typing import List
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2 import Error
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel
from dotenv import load_dotenv

# --- TAMBAHAN UNTUK AUTH ---
from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta

load_dotenv()

app = FastAPI(title="IoT Healthcare API", description="API untuk Dashboard Monitoring")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("[ERROR] DATABASE_URL tidak ditemukan di file .env!")

# --- KONFIGURASI KEAMANAN AUTH ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY", "rahasia-mediot-2026") # Idealnya taruh di .env
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # Token berlaku 24 jam

# --- PYDANTIC MODELS ---
class VitalRecord(BaseModel):
    id: int
    id_pasien: str
    waktu: str
    bpm: int
    spo2: int
    suhu: float
    status_alat: str

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    full_name: str

# --- ENDPOINT AUTH LOGIN ---
@app.post("/api/v1/auth/login", response_model=LoginResponse)
def login(request: LoginRequest):
    try:
        connection = psycopg2.connect(DATABASE_URL)
        cursor = connection.cursor(cursor_factory=RealDictCursor)

        # 1. Cari user di database
        cursor.execute("SELECT * FROM users WHERE username = %s", (request.username,))
        user = cursor.fetchone()

        # 2. Verifikasi Username & Password
        if not user or not pwd_context.verify(request.password, user['password_hash']):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Username atau password salah",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 3. Buat JWT Token
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode = {"sub": user['username'], "role": user['role'], "exp": expire}
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

        return {
            "access_token": encoded_jwt,
            "token_type": "bearer",
            "role": user['role'],
            "full_name": user['full_name']
        }

    except Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if "connection" in locals() and not connection.closed:
            cursor.close()
            connection.close()

# --- ENDPOINT HISTORY (TETAP SAMA) ---
@app.get("/api/v1/history/{id_pasien}", response_model=List[VitalRecord])
def get_patient_history(id_pasien: str, limit: int = Query(50, ge=1, le=500)):
    # ... (Isi kode ini persis sama seperti milikmu sebelumnya) ...
    try:
        connection = psycopg2.connect(DATABASE_URL)
        cursor = connection.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT id, id_pasien, TO_CHAR(waktu, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as waktu, 
                   bpm, spo2, suhu, status_alat
            FROM riwayat_vitals 
            WHERE id_pasien = %s 
            ORDER BY waktu DESC 
            LIMIT %s
        """
        cursor.execute(query, (id_pasien, limit))
        records = cursor.fetchall()

        if not records:
            raise HTTPException(status_code=404, detail="Data pasien tidak ditemukan.")
        return records
    except Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if "connection" in locals() and not connection.closed:
            cursor.close()
            connection.close()