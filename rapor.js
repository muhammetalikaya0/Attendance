// Sayfa yüklendiğinde çalışacak
document.addEventListener('DOMContentLoaded', function() {
    console.log('Sayfa yüklendi, dersleri getirme başlıyor...');
    loadCourses();
});

// Dersleri yükleme fonksiyonu
function loadCourses() {
    console.log('Dersler yükleniyor...');
    fetch('/api/courses')
        .then(response => {
            console.log('API yanıtı:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(courses => {
            console.log('Gelen dersler:', courses);
            const courseSelect = document.getElementById('course');
            courseSelect.innerHTML = ''; // Mevcut seçenekleri temizle
            
            if (courses && courses.length > 0) {
                courses.forEach(course => {
                    const option = document.createElement('option');
                    option.value = course;
                    option.textContent = course;
                    courseSelect.appendChild(option);
                });
                console.log('Dersler başarıyla yüklendi');
            } else {
                console.log('Hiç ders bulunamadı');
                const option = document.createElement('option');
                option.textContent = 'Ders bulunamadı';
                courseSelect.appendChild(option);
            }
        })
        .catch(error => {
            console.error('Dersler yüklenirken hata:', error);
            alert('Dersler yüklenirken bir hata oluştu!');
        });
}

// Rapor getirme fonksiyonu
function getReport() {
    const course = document.getElementById('course').value;
    const week = document.getElementById('week').value;

    console.log(`Rapor getiriliyor... Ders: ${course}, Hafta: ${week}`);

    if (!course || course === 'Ders bulunamadı') {
        alert('Lütfen geçerli bir ders seçin!');
        return;
    }

    fetch(`/api/report?course=${encodeURIComponent(course)}&week=${encodeURIComponent(week)}`)
        .then(response => {
            console.log('Rapor API yanıtı:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Gelen rapor verileri:', data);
            if (data && Array.isArray(data)) {
                updateReportTable(data);
                updateSummary(data);
                console.log('Rapor başarıyla güncellendi');
            } else {
                console.log('Rapor verisi boş veya hatalı format');
                clearReport();
                alert('Bu ders ve hafta için kayıt bulunamadı.');
            }
        })
        .catch(error => {
            console.error('Rapor alınırken hata:', error);
            alert('Rapor alınırken bir hata oluştu!');
            clearReport();
        });
}

// Rapor tablosunu güncelleme
function updateReportTable(data) {
    const tbody = document.getElementById('reportTable');
    tbody.innerHTML = ''; // Mevcut verileri temizle

    if (data.length === 0) {
        const row = tbody.insertRow();
        const cell = row.insertCell(0);
        cell.colSpan = 6;
        cell.textContent = 'Bu ders ve hafta için kayıt bulunamadı.';
        return;
    }

    data.forEach(record => {
        const row = tbody.insertRow();
        
        // Hücreleri oluştur
        row.insertCell(0).textContent = record.student || 'N/A';
        row.insertCell(1).textContent = record.course || 'N/A';
        row.insertCell(2).textContent = record.week || 'N/A';
        row.insertCell(3).textContent = record.timestamp ? new Date(record.timestamp).toLocaleString() : 'N/A';
        row.insertCell(4).textContent = record.matched ? 'Katıldı' : 'Katılmadı';
        row.insertCell(5).textContent = record.similarity ? `${record.similarity.toFixed(2)}%` : 'N/A';
    });
}

// Özet bilgileri güncelleme
function updateSummary(data) {
    const totalStudents = data.length;
    const presentStudents = data.filter(record => record.matched).length;
    const attendanceRate = totalStudents > 0 ? (presentStudents / totalStudents * 100).toFixed(2) : 0;

    document.getElementById('totalStudents').textContent = totalStudents;
    document.getElementById('presentStudents').textContent = presentStudents;
    document.getElementById('attendanceRate').textContent = `${attendanceRate}%`;

    console.log('Özet bilgiler güncellendi:', {
        total: totalStudents,
        present: presentStudents,
        rate: attendanceRate
    });
}

// Raporu temizleme
function clearReport() {
    const tbody = document.getElementById('reportTable');
    tbody.innerHTML = '';
    document.getElementById('totalStudents').textContent = '0';
    document.getElementById('presentStudents').textContent = '0';
    document.getElementById('attendanceRate').textContent = '0%';
}

// Raporu indirme fonksiyonu
function downloadReport() {
    const course = document.getElementById('course').value;
    const week = document.getElementById('week').value;
    
    if (!course || course === 'Ders bulunamadı') {
        alert('Lütfen geçerli bir ders seçin!');
        return;
    }

    const table = document.querySelector('table');
    if (!table || table.rows.length <= 1) {
        alert('İndirilecek rapor verisi bulunamadı!');
        return;
    }

    try {
        let csv = 'Öğrenci No,Ders,Hafta,Tarih,Durum,Benzerlik Oranı\n';
        
        Array.from(table.querySelectorAll('tr')).slice(1).forEach(row => {
            const cells = Array.from(row.cells);
            const rowData = cells.map(cell => `"${cell.textContent}"`).join(',');
            csv += rowData + '\n';
        });
        
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `yoklama_raporu_${course}_hafta${week}.csv`;
        link.click();
        
        console.log('Rapor başarıyla indirildi');
    } catch (error) {
        console.error('Rapor indirilirken hata:', error);
        alert('Rapor indirilirken bir hata oluştu!');
    }
}
