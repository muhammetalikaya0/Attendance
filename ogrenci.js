// Updated ogrenci.js file to integrate student course fetching and attendance functionalities

document.getElementById('fetchCourses').addEventListener('click', async () => {
    const studentId = document.getElementById('studentNumber').value.trim();
    if (!studentId) {
        alert('Lütfen öğrenci numaranızı giriniz.');
        return;
    }

    try {
        // Fetch courses from the server
        const response = await fetch(`https://10.8.1.217:5000/api/students/${studentId}/courses`);
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

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mediaRecorder = new MediaRecorder(stream);
        let audioChunks = [];

        mediaRecorder.ondataavailable = event => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            const reader = new FileReader();

            reader.onloadend = async () => {
                const base64Audio = reader.result.split(',')[1];

                const response = await fetch('https://10.8.1.217:5000/api/attendance', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        audio: base64Audio,
                        studentId: studentId,
                        course: course,
                        week: week
                    })
                });

                if (!response.ok) {
                    throw new Error('Eşleşme işlemi sırasında bir hata oluştu.');
                }

                const data = await response.json();
                document.getElementById('matchingStatus').textContent = data.message;
            };

            reader.readAsDataURL(audioBlob);
        };

        mediaRecorder.start();
        setTimeout(() => {
            mediaRecorder.stop();
        }, 5000);
    } catch (error) {
        console.error('Mikrofon erişim hatası:', error);
        alert('Mikrofon erişiminde bir sorun oluştu.');
    }
});
