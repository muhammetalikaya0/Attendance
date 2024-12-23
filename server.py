import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask import send_from_directory

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

# Yoklama bilgisi ekleme (Öğretmen/Öğrenci)
@app.route('/api/attendance', methods=['POST'])
def record_attendance():
    data = request.get_json()
    course_name = data.get('course')
    week = data.get('week')
    audio_file = data.get('audioFile')

    if not (course_name and week and audio_file):
        return jsonify({"message": "Eksik bilgi gönderildi."}), 400

    if course_name not in courses:
        return jsonify({"message": "Ders bulunamadı."}), 404

    # Ses dosyasının mevcut olup olmadığını kontrol et
    audio_path = os.path.join(app.root_path, 'static', 'uploads', audio_file)
    if not os.path.exists(audio_path):
        return jsonify({"message": f"Ses dosyası bulunamadı: {audio_file}"}), 404

    # Eşleşme başarılı kabul ediliyor
    attendance_record = {
        "course": course_name,
        "week": week,
        "audioFile": audio_file,
        "matched": True
    }
    attendance_records.append(attendance_record)

    # Dersin yoklama kayıtlarına ekle
    courses[course_name]["attendance"].append(attendance_record)

    return jsonify({
        "message": "Başarılı:",
        "details": f"Ses dosyası sunucuya iletildi: {audio_file}"
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
