import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Kunci angka acak agar hasil data selalu konsisten saat didemonstrasikan ke juri
np.random.seed(42)

def generate_patient_series(patient_id, num_rows=1000, scenario="normal"):
    base_time = datetime(2026, 7, 24, 8, 0, 0)
    data = []
    
    # Nilai awal fisiologis orang sehat
    bpm = np.random.normal(75, 4)
    spo2 = np.random.normal(98, 0.8)
    suhu = np.random.normal(36.6, 0.15)
    
    for i in range(num_rows):
        current_time = base_time + timedelta(seconds=i*3)  # Data masuk tiap 3 detik
        
        if scenario == "normal":
            bpm += np.random.normal(0, 0.5)
            spo2 += np.random.normal(0, 0.2)
            suhu += np.random.normal(0, 0.01)
            
            # Batas biologis manusia normal
            bpm = np.clip(bpm, 60, 90)
            spo2 = np.clip(spo2, 96, 100)
            suhu = np.clip(suhu, 36.2, 37.1)
            label_risk = 0  # 0: Normal / Stabil
            is_artifact = 0
            
        elif scenario == "deterioration":
            # Simulasi pemburukan klinis (seperti hipotermia, demam tinggi, atau sesak napas)
            bpm += np.random.normal(0.08, 0.4)
            spo2 -= np.random.normal(0.03, 0.15)
            suhu += np.random.normal(0.004, 0.01)
            
            bpm = np.clip(bpm, 65, 145)
            spo2 = np.clip(spo2, 84, 99)
            suhu = np.clip(suhu, 36.5, 40.2)
            
            # Pelabelan otomatis menggunakan standar medis internasional NEWS2
            if spo2 < 90 or bpm > 120 or suhu > 38.5:
                label_risk = 3  # Kritis
            elif spo2 < 94 or bpm > 105 or suhu > 37.8:
                label_risk = 2  # Bahaya
            elif spo2 < 96 or bpm > 90 or suhu > 37.2:
                label_risk = 1  # Waspada
            else:
                label_risk = 0  # Normal
            is_artifact = 0

        # Sisipkan 3% kemungkinan sensor error / wajah bergeser (Motion Artifact)
        if np.random.rand() < 0.03:
            bpm_rec = np.random.choice([np.random.uniform(20, 35), np.random.uniform(160, 190)])
            spo2_rec = np.random.uniform(70, 85)
            suhu_rec = suhu
            is_artifact = 1
            label_risk = -1  # -1: Abaikan dari scoring EWS (ini data rusak)
        else:
            bpm_rec = round(bpm)
            spo2_rec = round(spo2, 1)
            suhu_rec = round(suhu, 2)
            
        data.append({
            "id_pasien": patient_id,
            "waktu": current_time.strftime("%Y-%m-%d %H:%M:%S"),
            "bpm": int(bpm_rec),
            "spo2": float(spo2_rec),
            "suhu": float(suhu_rec),
            "status_alat": "ERROR_ARTIFACT" if is_artifact == 1 else "OK",
            "label_risk": label_risk
        })
        
    return pd.DataFrame(data)

print("[INFO] Mengaktifkan generator data medis berstandar NEWS2...")
df_p1 = generate_patient_series("P-001", num_rows=2000, scenario="normal")
df_p2 = generate_patient_series("P-002", num_rows=2000, scenario="deterioration")
df_p3 = generate_patient_series("P-003", num_rows=1000, scenario="normal")

# Gabung semua pasien dan simpan ke file CSV
df_final = pd.concat([df_p1, df_p2, df_p3], ignore_index=True)
df_final.to_csv("dataset_medis_gemastik.csv", index=False)

print(f"[SUKSES] File 'dataset_medis_gemastik.csv' berhasil dibuat!")
print(f"Total baris data: {len(df_final)}")
print("\nDistribusi label kondisi pasien di dalam dataset:")
print("0: Normal | 1: Waspada | 2: Bahaya | 3: Kritis | -1: Sensor Error")
print(df_final["label_risk"].value_counts())