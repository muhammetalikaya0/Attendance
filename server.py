import os
import base64
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask import send_from_directory
from scipy.io import wavfile
from scipy.fftpack import dct
import random

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
    def extract_mfcc(file_path):
        try:
            # Ses dosyasını oku
            sample_rate, signal = wavfile.read(file_path)
            
            # Ses sinyali kontrolü
            if signal.size == 0:
                print(f"DEBUG: Boş ses sinyali tespit edildi: {file_path}")
                return None
                
            # Ses seviyesi kontrolü
            audio_level = np.abs(signal).mean()
            if audio_level < 100:  # Bu eşik değeri ayarlanabilir
                print(f"DEBUG: Çok düşük ses seviyesi tespit edildi: {file_path}, Level: {audio_level}")
                return None

            # Mono'ya çevir
            if len(signal.shape) > 1:
                signal = np.mean(signal, axis=1)
            
            # Normalize signal
            signal = signal / (np.max(np.abs(signal)) + 1e-10)
            
            # Pre-emphasis
            pre_emphasis = 0.97
            emphasized_signal = np.append(signal[0], signal[1:] - pre_emphasis * signal[:-1])
            
            # Framing parameters
            frame_size = 0.025
            frame_stride = 0.01
            frame_length = int(round(frame_size * sample_rate))
            frame_step = int(round(frame_stride * sample_rate))
            signal_length = len(emphasized_signal)
            
            # Minimum sinyal uzunluğu kontrolü
            min_signal_length = sample_rate * 0.5  # En az 0.5 saniye
            if signal_length < min_signal_length:
                print(f"DEBUG: Çok kısa ses kaydı tespit edildi: {file_path}")
                return None

            # Frame the signal
            num_frames = int(np.ceil(float(np.abs(signal_length - frame_length)) / frame_step))
            pad_signal_length = num_frames * frame_step + frame_length
            z = np.zeros((pad_signal_length - signal_length))
            pad_signal = np.append(emphasized_signal, z)
            indices = np.tile(np.arange(0, frame_length), (num_frames, 1)) + \
                     np.tile(np.arange(0, num_frames * frame_step, frame_step), (frame_length, 1)).T
            frames = pad_signal[indices.astype(np.int32, copy=False)]
            
            # Apply Hamming window
            frames *= np.hamming(frame_length)
            
            # FFT and Power Spectrum
            NFFT = 512
            mag_frames = np.absolute(np.fft.rfft(frames, NFFT))
            pow_frames = ((1.0 / NFFT) * ((mag_frames) ** 2))
            
            # Spectral entropy kontrolü
            spectral_entropy = -np.sum(pow_frames * np.log2(pow_frames + 1e-10), axis=1)
            if np.mean(spectral_entropy) < 0.1:  # Bu eşik değeri ayarlanabilir
                print(f"DEBUG: Düşük spektral entropi tespit edildi: {file_path}")
                return None
            
            # Filter Banks
            nfilt = 40
            low_freq_mel = 0
            high_freq_mel = (2595 * np.log10(1 + (sample_rate / 2) / 700))
            mel_points = np.linspace(low_freq_mel, high_freq_mel, nfilt + 2)
            hz_points = (700 * (10**(mel_points / 2595) - 1))
            bin = np.floor((NFFT + 1) * hz_points / sample_rate)
            
            # Create filterbank
            fbank = np.zeros((nfilt, int(np.floor(NFFT / 2 + 1))))
            for m in range(1, nfilt + 1):
                f_m_minus = int(bin[m - 1])
                f_m = int(bin[m])
                f_m_plus = int(bin[m + 1])
                for k in range(f_m_minus, f_m):
                    fbank[m - 1, k] = (k - bin[m - 1]) / (bin[m] - bin[m - 1])
                for k in range(f_m, f_m_plus):
                    fbank[m - 1, k] = (bin[m + 1] - k) / (bin[m + 1] - bin[m])
            
            filter_banks = np.dot(pow_frames, fbank.T)
            filter_banks = np.where(filter_banks == 0, np.finfo(float).eps, filter_banks)
            filter_banks = 20 * np.log10(filter_banks)
            
            # MFCCs
            num_ceps = 13
            mfcc = dct(filter_banks, type=2, axis=1, norm='ortho')[:, 1:(num_ceps + 1)]
            
            # Liftering
            cep_lifter = 22
            (nframes, ncoeff) = mfcc.shape
            n = np.arange(ncoeff)
            lift = 1 + (cep_lifter / 2) * np.sin(np.pi * n / cep_lifter)
            mfcc *= lift
            
            # Normalize
            mfcc = (mfcc - np.mean(mfcc, axis=0)) / (np.std(mfcc, axis=0) + 1e-10)
            
            return mfcc
            
        except Exception as e:
            print(f"MFCC extraction error for {file_path}: {str(e)}")
            return None

    try:
        print(f"Processing file1: {file1}")
        print(f"Processing file2: {file2}")
        
        mfcc1 = extract_mfcc(file1)
        mfcc2 = extract_mfcc(file2)

        # MFCC çıkarma kontrolü
        if mfcc1 is None or mfcc2 is None:
            print("DEBUG: MFCC çıkarma başarısız")
            return 0

        # Minimum frame sayısı kontrolü
        if len(mfcc1) < 10 or len(mfcc2) < 10:  # En az 10 frame olmalı
            print("DEBUG: Yetersiz frame sayısı")
            return 0

        # Dynamic Time Warping için minimum uzunluğa getir
        min_len = min(len(mfcc1), len(mfcc2))
        mfcc1 = mfcc1[:min_len]
        mfcc2 = mfcc2[:min_len]

        # Calculate similarity using correlation
        similarity_matrix = np.corrcoef(mfcc1.T, mfcc2.T)
        similarity = np.mean(np.diagonal(similarity_matrix[:mfcc1.shape[1], mfcc1.shape[1]:]))
        
        # Normalize similarity to [0, 1] range
        similarity = (similarity + 1) / 2

        # Similarity değeri kontrolü
        if np.isnan(similarity) or np.isinf(similarity):
            print("DEBUG: Geçersiz benzerlik değeri")
            return 0
        
        print(f"Raw similarity score: {similarity}")
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

        student_audio_path = os.path.join(upload_dir, f'student_{student_id}_{course_name}_{week}.wav')
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
