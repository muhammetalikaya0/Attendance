// Updated ogrenci.js file to integrate student course fetching and attendance functionalities

document.getElementById('fetchCourses').addEventListener('click', async () => {
    const studentId = document.getElementById('studentNumber').value.trim();
    if (!studentId) {
        alert('Lütfen öğrenci numaranızı giriniz.');
        return;
    }

    try {
        // Fetch courses from the server
        const response = await fetch(`http://127.0.0.1:5000/api/students/${studentId}/courses`);
        if (!response.ok) {
            throw new Error('Sunucudan ders bilgileri alınamadı.');
        }

        const data = await response.json();
        const courseSelect = document.getElementById('courseSelect');
        courseSelect.innerHTML = '<option value="">Bir ders seçiniz</option>';

        data.courses.forEach(course => {
            const option = document.createElement('option');
            option.value = course;
            option.textContent = course;
            courseSelect.appendChild(option);
        });

        alert('Dersler başarıyla yüklendi.');
    } catch (error) {
        console.error('Dersleri getirme hatası:', error);
        alert('Ders bilgileri alınırken bir sorun oluştu.');
    }
});

document.getElementById('startListening').addEventListener('click', async () => {
    const studentId = document.getElementById('studentNumber').value.trim();
    const course = document.getElementById('courseSelect').value;
    const week = document.getElementById('weekSelect').value;

    if (!studentId || !course || !week) {
        alert('Lütfen öğrenci numarası, ders ve hafta seçimini tamamlayınız.');
        return;
    }

    navigator.mediaDevices.getUserMedia({ audio: true })
        .then(stream => {
            const mediaRecorder = new MediaRecorder(stream);
            let audioChunks = [];

            mediaRecorder.ondataavailable = event => {
                audioChunks.push(event.data);
            };

            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });

                const formData = new FormData();
                formData.append('audio', audioBlob);
                formData.append('studentId', studentId);
                formData.append('course', course);
                formData.append('week', week);

                try {
                    const response = await fetch('http://127.0.0.1:5000/api/attendance', {
                        method: 'POST',
                        body: formData
                    });

                    if (!response.ok) {
                        throw new Error('Eşleşme işlemi sırasında bir hata oluştu.');
                    }

                    const data = await response.json();
                    document.getElementById('matchingStatus').textContent = data.message;
                } catch (error) {
                    console.error('Eşleşme hatası:', error);
                    alert('Ses eşleştirme sırasında bir hata oluştu.');
                }
            };

            mediaRecorder.start();
            setTimeout(() => {
                mediaRecorder.stop();
            }, 5000);
        })
        .catch(error => {
            console.error('Mikrofon erişim hatası:', error);
            alert('Mikrofon erişiminde bir sorun oluştu.');
        });
});
