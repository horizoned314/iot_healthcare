import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib

print("[INFO] 1. Memuat dataset medis dari file CSV...")
try:
    df = pd.read_csv("dataset_medis_gemastik.csv")
except FileNotFoundError:
    print("[ERROR] File 'dataset_medis_gemastik.csv' tidak ditemukan! Jalankan build_dataset.py dulu.")
    exit()

# Memilih fitur (input AI) dan target (kunci jawaban AI)
# Input: BPM, SpO2, dan Suhu
X = df[["bpm", "spo2", "suhu"]]
# Target: label_risk (-1: Error/Artefak, 0: Normal, 1: Waspada, 2: Bahaya, 3: Kritis)
y = df["label_risk"]

print("[INFO] 2. Membagi data: 80% untuk latihan (Training), 20% untuk ujian (Testing)...")
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

print("[INFO] 3. Melatih algoritma Random Forest Classifier...")
# Menggunakan 100 pohon keputusan (trees) agar akurat namun tetap ringan
model = RandomForestClassifier(n_estimators=100, random_state=42, max_depth=10)
model.fit(X_train, y_train)

print("[INFO] 4. Menguji keakuratan AI pada data ujian (Testing Data)...")
y_pred = model.predict(X_test)
akurasi = accuracy_score(y_test, y_pred)

print("-" * 50)
print(f"[HASIL UJIAN AI] Akurasi Model: {akurasi * 100:.2f}%")
print("-" * 50)
print("Laporan Detail Per Kelas Kondisi Medis:")
# Nama label untuk laporan presentasi
target_names = ["Artefak Sensor (-1)", "Normal (0)", "Waspada (1)", "Bahaya (2)", "Kritis (3)"]
print(classification_report(y_test, y_pred, target_names=target_names))

print("[INFO] 5. Menyimpan model AI yang sudah pintar ke dalam file biner...")
joblib.dump(model, "model_ews.pkl")
print("[SUKSES] File 'model_ews.pkl' berhasil disimpan! Otak AI siap diintegrasikan ke sistem IoT.")