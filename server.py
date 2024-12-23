import os
import base64
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask import send_from_directory
from scipy.io import wavfile
from scipy.fftpack import dct

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
        sample_rate, signal = wavfile.read(file_path)
        # Pre-emphasis
        pre_emphasis = 0.97
        emphasized_signal = np.append(signal[0], signal[1:] - pre_emphasis * signal[:-1])
        # Framing
        frame_size = 0.025
        frame_stride = 0.01
        frame_length, frame_step = frame_size * sample_rate, frame_stride * sample_rate
        signal_length = len(emphasized_signal)
        frame_length = int(round(frame_length))
        frame_step = int(round(frame_step))
        num_frames = int(np.ceil(float(np.abs(signal_length - frame_length)) / frame_step))
        pad_signal_length = num_frames * frame_step + frame_length
        z = np.zeros((pad_signal_length - signal_length))
        pad_signal = np.append(emphasized_signal, z)
        indices = np.tile(np.arange(0, frame_length), (num_frames, 1)) + np.tile(np.arange(0, num_frames * frame_step, frame_step), (frame_length, 1)).T
        frames = pad_signal[indices.astype(np.int32, copy=False)]
        # Window
        frames *= np.hamming(frame_length)
        # Fourier Transform and Power Spectrum
        NFFT = 512
        mag_frames = np.absolute(np.fft.rfft(frames, NFFT))
        pow_frames = ((1.0 / NFFT) * ((mag_frames) ** 2))
        # Filter Banks
        nfilt = 40
        low_freq_mel = 0
        high_freq_mel = (2595 * np.log10(1 + (sample_rate / 2) / 700))
        mel_points = np.linspace(low_freq_mel, high_freq_mel, nfilt + 2)
        hz_points = (700 * (10**(mel_points / 2595) - 1))
        bin = np.floor((NFFT + 1) * hz_points / sample_rate)
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
        # Mel-frequency Cepstral Coefficients (MFCCs)
        num_ceps = 12
        cep_lifter = 22
        mfcc = dct(filter_banks, type=2, axis=1, norm='ortho')[:, 1 : (num_ceps + 1)]
        (nframes, ncoeff) = mfcc.shape
        n = np.arange(ncoeff)
        lift = 1 + (cep_lifter / 2) * np.sin(np.pi * n / cep_lifter)
        mfcc *= lift
        return mfcc

    mfcc1 = extract_mfcc(file1)
    mfcc2 = extract_mfcc(file2)

    # Normalize MFCCs
    mfcc1 = (mfcc1 - np.mean(mfcc1)) / np.std(mfcc1)
    mfcc2 = (mfcc2 - np.mean(mfcc2)) / np.std(mfcc2)

    # Calculate similarity (using cosine similarity)
    similarity = np.dot(mfcc1, mfcc2.T) / (np.linalg.norm(mfcc1) * np.linalg.norm(mfcc2))
    mean_similarity = np.mean(similarity)

    return mean_similarity

# Yoklama bilgisi ekleme (Öğretmen/Öğrenci)
@app.route('/api/attendance', methods=['POST'])
def record_attendance():
    data = request.get_json()
    course_name = data.get('course')
    week = data.get('week')
    student_id = data.get('studentId')
    student_audio_base64 = data.get('audio')

    if not (course_name and week and student_id and student_audio_base64):
        return jsonify({"message": "Eksik bilgi gönderildi."}), 400

    if course_name not in courses:
        return jsonify({"message": "Ders bulunamadı."}), 404

    # Öğrenci ses dosyasını kaydetme
    student_audio_path = os.path.join(app.root_path, 'static', 'uploads', f'{student_id}_{course_name}_{week}.wav')
    with open(student_audio_path, 'wb') as f:
        f.write(base64.b64decode(student_audio_base64))

    # Burada öğretmenin çaldığı dosya adını belirlemek için loglardan alınan bilgi kullanılabilir
    # Örneğin, loglardan son çalınan dosya adını alalım
    audio_path = 'path_to_last_played_file'  # Örneğin, 'file22.mp3'

    if not os.path.exists(audio_path):
        return jsonify({"message": f"Ses dosyası bulunamadı: {audio_path}"}), 404

    # Ses dosyalarını karşılaştırma
    similarity = compare_audio_files(audio_path, student_audio_path)
    matched = similarity > 0.8  # Eşleşme oranını belirli bir eşiğin üstünde kontrol et

    attendance_record = {
        "course": course_name,
        "week": week,
        "audioFile": audio_path,
        "studentId": student_id,
        "matched": matched
    }
    attendance_records.append(attendance_record)

    # Dersin yoklama kayıtlarına ekle
    courses[course_name]["attendance"].append(attendance_record)

    return jsonify({
        "message": "Başarılı" if matched else "Başarısız",
        "details": f"Eşleşme oranı: {similarity}",
        "matched": matched
    })

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
