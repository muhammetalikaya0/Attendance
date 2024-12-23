document.getElementById('fetchCourses').addEventListener('click', async () => {
    const studentId = document.getElementById('studentNumber').value.trim();
    if (!studentId) {
        alert('Lütfen öğrenci numaranızı giriniz.');
        return;
    }

    try {
        // Fetch courses from the server
        const response = await fetch(`/api/students/${studentId}/courses`);
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

                try {
                    const response = await fetch('/api/attendance', {
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

                    const data = await response.json();

                    if (!response.ok) {
                        throw new Error(data.message || 'Sunucu hatası oluştu');
                    }

                    if (data.matched) {
                        alert('Yoklama başarıyla kaydedildi!');
                    } else {
                        alert('Yoklama kaydı başarısız oldu. Lütfen tekrar deneyin.');
                    }
                    
                    if (document.getElementById('matchingStatus')) {
                        document.getElementById('matchingStatus').textContent = data.message;
                    }
                } catch (error) {
                    console.error('Sunucu hatası:', error);
                    alert(`Hata: ${error.message}`);
                }
            };

            reader.readAsDataURL(audioBlob);
        };

        // Kayıt başlat
        mediaRecorder.start();
        alert('Ses kaydı başlatıldı. 5 saniye sonra otomatik olarak duracak.');
        
        // 5 saniye sonra kayıt durdur
        setTimeout(() => {
            mediaRecorder.stop();
            stream.getTracks().forEach(track => track.stop()); // Mikrofonu kapat
        }, 10000);
    } catch (error) {
        console.error('Mikrofon erişim hatası:', error);
        alert('Mikrofon erişiminde bir sorun oluştu. Lütfen mikrofon izinlerini kontrol edin.');
    }
});
