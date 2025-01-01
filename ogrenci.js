let mediaRecorder;
let audioChunks = [];
let recordingTimeout;
let timerDisplay;
let timeLeft;

// Desteklenen MIME tiplerini kontrol eden fonksiyon
function getSupportedMimeType() {
    const possibleTypes = [
        'audio/webm',
        'audio/webm;codecs=opus',
        'audio/ogg;codecs=opus',
        'audio/mp4'
    ];
    
    for (const type of possibleTypes) {
        if (MediaRecorder.isTypeSupported(type)) {
            return type;
        }
    }
    return null;
}

// WAV dönüşüm fonksiyonu
function convertToWav(audioBuffer) {
    const numOfChan = audioBuffer.numberOfChannels;
    const length = audioBuffer.length * numOfChan * 2;
    const buffer = new ArrayBuffer(44 + length);
    const view = new DataView(buffer);
    
    // RIFF chunk descriptor
    writeUTFBytes(view, 0, 'RIFF');
    view.setUint32(4, 36 + length, true);
    writeUTFBytes(view, 8, 'WAVE');
    
    // FMT sub-chunk
    writeUTFBytes(view, 12, 'fmt ');
    view.setUint32(16, 16, true); // subchunk1size
    view.setUint16(20, 1, true); // audio format
    view.setUint16(22, numOfChan, true); // numOfChan
    view.setUint32(24, audioBuffer.sampleRate, true); // sampleRate
    view.setUint32(28, audioBuffer.sampleRate * 2 * numOfChan, true); // byteRate
    view.setUint16(32, numOfChan * 2, true); // blockAlign
    view.setUint16(34, 16, true); // bitsPerSample
    
    // Data sub-chunk
    writeUTFBytes(view, 36, 'data');
    view.setUint32(40, length, true);
    
    // Write the PCM samples
    const data = new Float32Array(audioBuffer.length);
    let offset = 44;
    for (let i = 0; i < audioBuffer.numberOfChannels; i++) {
        audioBuffer.copyFromChannel(data, i);
        for (let j = 0; j < data.length; j++) {
            const sample = Math.max(-1, Math.min(1, data[j]));
            view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true);
            offset += 2;
        }
    }
    
    return new Blob([buffer], { type: 'audio/wav' });
}

function writeUTFBytes(view, offset, string) {
    for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
    }
}

function updateTimerDisplay() {
    const timerElement = document.getElementById('timer');
    if (timerElement) {
        timerElement.textContent = `Kalan süre: ${timeLeft} saniye`;
    }
}

document.getElementById('fetchCourses').addEventListener('click', async () => {
    const studentId = document.getElementById('studentNumber').value.trim();
    if (!studentId) {
        alert('Lütfen öğrenci numaranızı giriniz.');
        return;
    }

    try {
        const response = await fetch(`https://10.8.38.93:5000/api/students/${studentId}/courses`);
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
        const stream = await navigator.mediaDevices.getUserMedia({ 
            audio: {
                channelCount: 1,
                sampleRate: 44100,
                sampleSize: 16,
                volume: 1.0
            }
        });
        
        audioChunks = [];

        // Desteklenen MIME tipini kontrol et
        const mimeType = getSupportedMimeType();
        if (!mimeType) {
            throw new Error('Desteklenen ses formatı bulunamadı');
        }

        // MediaRecorder'ı yapılandırılmış ayarlarla oluştur
        mediaRecorder = new MediaRecorder(stream, {
            mimeType: mimeType,
            audioBitsPerSecond: 128000
        });

        mediaRecorder.ondataavailable = event => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: mimeType });
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const audioBuffer = await audioBlob.arrayBuffer();
            const audioData = await audioContext.decodeAudioData(audioBuffer);
            const wavBlob = await convertToWav(audioData);
            
            const reader = new FileReader();
            reader.onloadend = async () => {
                const base64Audio = reader.result.split(',')[1];

                try {
                    const response = await fetch('https://10.8.38.93:5000/api/attendance', {
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
                        alert('Yoklama alınamadı. Lütfen tekrar deneyiniz.');
                    }
                } catch (error) {
                    console.error('Sunucu hatası:', error);
                    alert('Yoklama işlemi sırasında bir hata oluştu. Lütfen tekrar deneyiniz.');
                }
            };

            reader.readAsDataURL(wavBlob);
        };

        // Kaydı başlat ve zamanlayıcıyı ayarla
        mediaRecorder.start();
        timeLeft = 20;
        updateTimerDisplay();

        timerDisplay = setInterval(() => {
            timeLeft--;
            updateTimerDisplay();
            if (timeLeft <= 0) {
                clearInterval(timerDisplay);
            }
        }, 1000);

        recordingTimeout = setTimeout(() => {
            if (mediaRecorder.state === "recording") {
                mediaRecorder.stop();
                stream.getTracks().forEach(track => track.stop());
                clearInterval(timerDisplay);
            }
        }, 20000);

        alert('Ses kaydı başlatıldı. 20 saniye bekleyin...');

    } catch (error) {
        if (error.name === 'NotAllowedError') {
            alert('Mikrofon izni reddedildi. Lütfen mikrofon izinlerini kontrol edin.');
        } else {
            console.error('Mikrofon erişim hatası:', error);
            alert('Mikrofon erişiminde bir sorun oluştu. Lütfen mikrofon izinlerini kontrol edin.');
        }
    }
});

// Sayfa yüklendiğinde hafta seçeneklerini oluştur
window.onload = function() {
    const weekSelect = document.getElementById('weekSelect');
    weekSelect.innerHTML = '<option value="">Hafta seçiniz</option>';
    
    // 14 haftalık ders dönemi için seçenekler
    for(let i = 1; i <= 14; i++) {
        const option = document.createElement('option');
        option.value = i;
        option.textContent = `Hafta ${i}`;
        weekSelect.appendChild(option);
    }

    // Timer element'ini oluştur
    if (!document.getElementById('timer')) {
        const timerDiv = document.createElement('div');
        timerDiv.id = 'timer';
        document.body.appendChild(timerDiv);
    }
};
