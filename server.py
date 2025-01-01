import os
import base64
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask import send_from_directory
from scipy.io import wavfile
import librosa
import random

from datetime import datetime
from flask import jsonify, request, send_from_directory


app = Flask(__name__)
CORS(app)  # Tüm rotalar için CORS'u etkinleştir

# Verileri saklamak için bellek içi yapılar
courses = {}  # {"courseName": {"students": [], "attendance": []}}
attendance_records = []  # Yoklama kayıtları

# Sunucu çalıştırma
@app.route('/')
def index():
    return "Yoklama Sistemi Sunucusu Çalışıyor!"

# Öğrenci arayüzü dosyasını sunma
@app.route('/ogrenci.html')
def serve_student_page():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'ogrenci.html')

# Öğretmen arayüzü dosyasını sunma
@app.route('/ogretmen.html')
def serve_teacher_page():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'ogretmen.html')

# Öğrenci JavaScript dosyasını sunma
@app.route('/js/ogrenci.js')
def serve_student_js():
    return send_from_directory(os.path.join(app.root_path, 'static', 'js'), 'ogrenci.js')

# Öğretmen JavaScript dosyasını sunma
@app.route('/js/app.js')
def serve_teacher_js():
    return send_from_directory(os.path.join(app.root_path, 'static', 'js'), 'app.js')

# Rapor sayfası dosyasını sunma
@app.route('/rapor.html')
def serve_report_page():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'rapor.html')

# Rapor JavaScript dosyasını sunma
@app.route('/js/rapor.js')
def serve_report_js():
    return send_from_directory(os.path.join(app.root_path, 'static', 'js'), 'rapor.js')

# Server.py'da attendance_records listesini global olarak tanımla
attendance_records = []

# Rapor verilerini getirme API'si - düzeltilmiş versiyon
@app.route('/api/report', methods=['GET'])
def get_report():
    try:
        course_name = request.args.get('course')
        week = request.args.get('week')
        
        print(f"DEBUG: Rapor isteniyor - Ders: {course_name}, Hafta: {week}")
        
        # Önce o derse kayıtlı tüm öğrencileri al
        if course_name not in courses:
            return jsonify([]), 404
            
        enrolled_students = courses[course_name]["students"]
        
        # Her kayıtlı öğrenci için bir kayıt oluştur
        all_records = []
        for student_id in enrolled_students:
            # Öğrencinin bu hafta için kaydını bul
            student_record = None
            for record in attendance_records:
                if (record.get('course') == course_name and 
                    str(record.get('week')) == str(week) and 
                    record.get('studentId') == student_id):
                    student_record = record
                    break
            
            # Eğer kayıt yoksa, gelmemiş olarak işaretle
            if student_record is None:
                student_record = {
                    'student': student_id,
                    'course': course_name,
                    'week': week,
                    'timestamp': datetime.now().isoformat(),
                    'matched': False,
                    'similarity': 0.0
                }
            else:
                # Varolan kaydı düzenle
                student_record = {
                    'student': student_record.get('studentId'),
                    'course': student_record.get('course'),
                    'week': student_record.get('week'),
                    'timestamp': student_record.get('timestamp', datetime.now().isoformat()),
                    'matched': bool(student_record.get('matched')),
                    'similarity': float(student_record.get('similarity', 0))
                }
                
            all_records.append(student_record)
        
        print(f"DEBUG: Tüm kayıtlar: {all_records}")
        return jsonify(all_records)
    
    except Exception as e:
        print(f"Error in get_report: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Dersleri listeleme (GET)
@app.route('/api/courses', methods=['GET'])
def list_courses():
    try:
        course_list = list(courses.keys())
        print("DEBUG: Mevcut dersler:", course_list)
        return jsonify(course_list)
    except Exception as e:
        print(f"Error in list_courses: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

# Ders ekleme (Öğretmen)
@app.route('/api/courses', methods=['POST'])
def add_course():
    data = request.get_json()
    course_name = data.get("name")

    if not course_name:
        return jsonify({"status": "error", "message": "Ders adı eksik."}), 400

    if course_name in courses:
        return jsonify({"status": "error", "message": "Bu ders zaten mevcut."}), 400

    # Yeni dersi ekle
    courses[course_name] = {"students": [], "attendance": []}
    return jsonify({"status": "success", "message": f"{course_name} dersi başarıyla eklendi."})

# Derse öğrenci ekleme (Öğretmen)
@app.route('/api/courses/<course_name>/students', methods=['POST'])
def add_student(course_name):
    if course_name not in courses:
        return jsonify({"status": "error", "message": "Ders bulunamadı."}), 404

    data = request.get_json()
    student_number = data.get("studentNumber")

    if not student_number:
        return jsonify({"status": "error", "message": "Öğrenci numarası eksik."}), 400

    if student_number in courses[course_name]["students"]:
        return jsonify({"status": "error", "message": "Bu öğrenci zaten derse kayıtlı."}), 400

    # Öğrenciyi ekle
    courses[course_name]["students"].append(student_number)
    return jsonify({"status": "success", "message": f"{student_number} numaralı öğrenci {course_name} dersine başarıyla eklendi."})

# Öğrenci derslerini getirme (Öğrenci)
@app.route('/api/students/<student_id>/courses', methods=['GET'])
def get_student_courses(student_id):
    student_courses = [
        course_name for course_name, course_data in courses.items()
        if student_id in course_data["students"]
    ]
    return jsonify({"courses": student_courses})

# Ses dosyalarını karşılaştırma fonksiyonu
def compare_audio_files(file1, file2):
    def extract_features(file_path):
        try:
            # Ses dosyasını yükle
            y, sr = librosa.load(file_path, sr=None)
            
            # Ses seviyesi kontrolü
            if np.abs(y).mean() < 0.02:
                print(f"DEBUG: Çok düşük ses seviyesi: {file_path}")
                return None

            # MFCC hesapla
            mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20)
            
            # Chroma özelliklerini hesapla
            chroma = librosa.feature.chroma_stft(y=y, sr=sr)
            
            # Spektral kontrast
            spectral_contrast = librosa.feature.spectral_contrast(y=y, sr=sr)
            
            # Özellikleri birleştir
            features = np.vstack([
                mfcc,
                chroma,
                spectral_contrast
            ])
            
            # Normalize et
            features_mean = np.mean(features, axis=1, keepdims=True)
            features_std = np.std(features, axis=1, keepdims=True) + 1e-8
            features_normalized = (features - features_mean) / features_std
            
            return features_normalized

        except Exception as e:
            print(f"Feature extraction error for {file_path}: {str(e)}")
            return None

    try:
        print(f"Processing file1: {file1}")
        print(f"Processing file2: {file2}")
        
        # Özellikleri çıkar
        features1 = extract_features(file1)
        features2 = extract_features(file2)
        
        if features1 is None or features2 is None:
            return 0
            
        # DTW mesafesini hesapla
        D, _ = librosa.sequence.dtw(features1, features2, metric='cosine')
        
        # Normalize edilmiş benzerlik skoru
        similarity = 1 - (D[-1, -1] / (features1.shape[1] + features2.shape[1]))
        
        print(f"DEBUG: DTW distance: {D[-1, -1]}")
        print(f"DEBUG: Raw similarity: {similarity}")
        
        # 0-1 aralığına sınırla
        similarity = max(0, min(1, similarity))
        
        return similarity

    except Exception as e:
        print(f"Comparison error: {str(e)}")
        return 0

# Yoklama bilgisi ekleme (Öğretmen/Öğrenci)
@app.route('/api/attendance', methods=['POST'])
def record_attendance():
    try:
        data = request.get_json()
        if not data:
            print("DEBUG: Veri alınamadı")
            return jsonify({"message": "Veri alınamadı"}), 400

        course_name = data.get('course')
        week = data.get('week')
        student_id = data.get('studentId')
        student_audio_base64 = data.get('audio')

        print(f"DEBUG: Gelen veriler - Ders: {course_name}, Hafta: {week}, Öğrenci: {student_id}")

        if not all([course_name, week, student_id, student_audio_base64]):
            print("DEBUG: Eksik veri")
            return jsonify({"message": "Eksik bilgi gönderildi"}), 400

        upload_dir = os.path.join(app.root_path, 'static', 'uploads')
        os.makedirs(upload_dir, exist_ok=True)

        student_audio_path = os.path.join(upload_dir, f'student_{student_id}{course_name}{week}.wav')
        try:
            with open(student_audio_path, 'wb') as f:
                f.write(base64.b64decode(student_audio_base64))
            print(f"DEBUG: Öğrenci ses dosyası kaydedildi: {student_audio_path}")
        except Exception as e:
            print(f"DEBUG: Ses dosyası kaydetme hatası: {str(e)}")
            return jsonify({"message": f"Ses dosyası kaydedilemedi: {str(e)}"}), 500

        random_file = random.randint(1, 25)
        teacher_audio_path = os.path.join(upload_dir, f'file{random_file}.wav')
        print(f"DEBUG: Öğretmen ses dosyası: {teacher_audio_path}")

        if not os.path.exists(teacher_audio_path):
            print(f"DEBUG: Öğretmen ses dosyası bulunamadı: {teacher_audio_path}")
            return jsonify({"message": "Öğretmen ses dosyası bulunamadı"}), 404

        try:
            print("DEBUG: Ses karşılaştırması başlıyor...")
            similarity = compare_audio_files(teacher_audio_path, student_audio_path)
            print(f"DEBUG: Karşılaştırma sonucu similarity: {similarity}")

            # Threshold ve benzerlik hesaplama
            threshold = 0.3
            scaled_similarity = similarity * 100
            matched = similarity >= threshold

            print(f"DEBUG: Ses karşılaştırma detayları:")
            print(f"  - Ham benzerlik değeri: {similarity}")
            print(f"  - Ölçeklendirilmiş benzerlik: {scaled_similarity}")
            print(f"  - Threshold değeri: {threshold}")
            print(f"  - Eşleşme sonucu: {matched}")

            attendance_record = {
                "course": course_name,
                "week": week,
                "studentId": student_id,
                "matched": matched,
                "similarity": float(scaled_similarity)
            }

            if course_name not in courses:
                courses[course_name] = {"students": [], "attendance": []}
            courses[course_name]["attendance"].append(attendance_record)
            attendance_records.append(attendance_record)

            print("DEBUG: Yoklama kaydı başarıyla oluşturuldu")
            attendance_records.append(attendance_record)
            return jsonify({
                "message": "Yoklama işlemi tamamlandı",
                "matched": bool(matched),
                "similarity": float(scaled_similarity)
            }), 200

        except Exception as e:
            print(f"DEBUG: Ses karşılaştırma hatası: {str(e)}")
            return jsonify({"message": f"Ses karşılaştırma hatası: {str(e)}"}), 500

    except Exception as e:
        print(f"DEBUG: En üst seviye hata: {str(e)}")
        return jsonify({"message": f"Sunucu hatası: {str(e)}"}), 500

# Ses dosyasını yükleme (Öğrenci)
@app.route('/upload-audio', methods=['POST'])
def upload_audio():
    if 'audio' not in request.files:
        return jsonify({"status": "error", "message": "Ses dosyası bulunamadı"}), 400

    audio = request.files['audio']
    upload_path = os.path.join(app.root_path, 'static', 'uploads', audio.filename)
    os.makedirs(os.path.dirname(upload_path), exist_ok=True)
    audio.save(upload_path)  # Dosyayı kaydet

    return jsonify({"status": "success", "message": "Ses kaydı başarıyla alındı", "filePath": upload_path})

if __name__ == '__main__':
    context = ('cert.pem', 'key.pem')
    app.run(host='0.0.0.0', port=5000, ssl_context=context)
