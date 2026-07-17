from typing import List
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2 import Error
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel

app = FastAPI(
    title="IoT Medis API", description="API untuk Dashboard Monitoring"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "jakartaku01",
    "dbname": "db_iot_medis",
}


class VitalRecord(BaseModel):
    id: int
    id_pasien: str
    waktu: str
    bpm: int
    spo2: int
    suhu: float
    status_alat: str


@app.get("/api/v1/history/{id_pasien}", response_model=List[VitalRecord])
def get_patient_history(
    id_pasien: str, limit: int = Query(50, ge=1, le=500)
):
    try:
        connection = psycopg2.connect(**DB_CONFIG)
        # Gunakan RealDictCursor agar hasil query dari Postgres langsung berbentuk Dictionary/JSON
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
            raise HTTPException(
                status_code=404,
                detail="Data pasien tidak ditemukan atau masih kosong.",
            )

        return records

    except Error as e:
        raise HTTPException(
            status_code=500, detail=f"Database error: {str(e)}"
        )
    finally:
        if "connection" in locals() and not connection.closed:
            cursor.close()
            connection.close()