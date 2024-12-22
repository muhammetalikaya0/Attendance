import os
from flask import Flask, request, jsonify
from flask_cors import CORS  # Flask-CORS modülünü ekleyin
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
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'ogrenci.html')

@app.route('/js/ogrenci.js')
def serve_student_js():
    return send_from_directory(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'js'), 'ogrenci.js')

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
    data = request.form
    student_id = data.get('studentId')
    course_name = data.get('course')
    week = data.get('week')
    audio = request.files.get('audio')

    if not (student_id and course_name and week and audio):
        return jsonify({"message": "Eksik bilgi gönderildi."}), 400

    if course_name not in courses:
        return jsonify({"message": "Ders bulunamadı."}), 404

    # Ses dosyasını kaydet
    audio_filename = f"{course_name}_week{week}_{audio.filename}"
    audio.save(os.path.join("uploads", audio_filename))

    # Simulate audio matching process (replace with real logic)
    match_successful = True  # Bu kısım gerçek ses eşleştirme mantığı ile değiştirilmelidir

    attendance_record = {
        "student_id": student_id,
        "course": course_name,
        "week": week,
        "audioFile": audio_filename,
        "matched": match_successful
    }
    attendance_records.append(attendance_record)

    # Dersin yoklama kayıtlarına ekle
    courses[course_name]["attendance"].append(attendance_record)

    message = "Eşleşme başarılı! Yoklama alındı." if match_successful else "Eşleşme başarısız."
    return jsonify({"message": message})

# Ses dosyasını yükleme (Öğrenci)
@app.route('/upload-audio', methods=['POST'])
def upload_audio():
    if 'audio' not in request.files:
        return jsonify({"status": "error", "message": "Ses dosyası bulunamadı"}), 400

    audio = request.files['audio']
    upload_path = os.path.join("uploads", audio.filename)
    os.makedirs("uploads", exist_ok=True)  # uploads klasörünü oluştur
    audio.save(upload_path)  # Dosyayı kaydet

    return jsonify({"status": "success", "message": "Ses kaydı başarıyla alındı", "filePath": upload_path})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)  # 0.0.0.0 ile tüm IP'lerden erişime izin verir
