// Ders ve öğrenci bilgileri için veri saklama
const courses = {};

// HTML elemanlarını seç
const newCourseInput = document.getElementById("newCourse");
const courseSelect = document.getElementById("courseSelect");
const newStudentInput = document.getElementById("newStudent");
const attendanceCourseSelect = document.getElementById("attendanceCourse");
const weekSelect = document.getElementById("weekSelect"); // Hafta seçimi
const addCourseButton = document.getElementById("addCourse");
const addStudentButton = document.getElementById("addStudent");
const startAttendanceButton = document.getElementById("startAttendance");

// Sunucuya ders ekleme
async function addCourseToServer(courseName) {
    try {
        const response = await fetch('http://127.0.0.1:5000/api/courses', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name: courseName })
        });
        if (!response.ok) {
            throw new Error("Sunucuya ders eklenirken bir hata oluştu.");
        }
        console.log(`Ders sunucuya eklendi: ${courseName}`);
    } catch (error) {
        console.error(error);
        alert("Ders sunucuya eklenemedi: " + error.message);
    }
}

// Ders ekleme
addCourseButton.addEventListener("click", async () => {
    const courseName = newCourseInput.value.trim();
    if (courseName === "") {
        alert("Lütfen bir ders adı giriniz!");
        return;
    }

    if (courses[courseName]) {
        alert("Bu ders zaten mevcut!");
        return;
    }

    // Ders ekle ve listeyi güncelle
    courses[courseName] = [];
    const option = new Option(courseName, courseName);
    courseSelect.add(option);
    attendanceCourseSelect.add(option.cloneNode(true));

    newCourseInput.value = "";
    alert(`${courseName} dersi eklendi.`);

    // Sunucuya gönder
    await addCourseToServer(courseName);
});

// Sunucuya öğrenci ekleme
async function addStudentToServer(courseName, studentNumber) {
    try {
        const response = await fetch(`http://127.0.0.1:5000/api/courses/${courseName}/students`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ studentNumber })
        });
        if (!response.ok) {
            throw new Error("Sunucuya öğrenci eklenirken bir hata oluştu.");
        }
        console.log(`Öğrenci sunucuya eklendi: ${studentNumber}`);
    } catch (error) {
        console.error(error);
        alert("Öğrenci sunucuya eklenemedi: " + error.message);
    }
}

// Öğrenci ekleme
addStudentButton.addEventListener("click", async () => {
    const selectedCourse = courseSelect.value;
    const studentNumber = newStudentInput.value.trim();
    if (selectedCourse === "") {
        alert("Lütfen bir ders seçiniz!");
        return;
    }
    if (studentNumber === "") {
        alert("Lütfen bir öğrenci numarası giriniz!");
        return;
    }

    if (courses[selectedCourse].includes(studentNumber)) {
        alert("Bu öğrenci zaten derse kayıtlı!");
        return;
    }

    // Öğrenci ekle
    courses[selectedCourse].push(studentNumber);
    newStudentInput.value = "";
    alert(`Öğrenci ${studentNumber}, \"${selectedCourse}\" dersine eklendi.`);

    // Sunucuya gönder
    await addStudentToServer(selectedCourse, studentNumber);
});

// Yoklama başlatma
startAttendanceButton.addEventListener("click", async () => {
    const selectedCourse = attendanceCourseSelect.value;
    const selectedWeek = weekSelect.value;

    if (selectedCourse === "") {
        alert("Lütfen bir ders seçiniz!");
        return;
    }

    if (selectedWeek === "") {
        alert("Lütfen bir hafta seçiniz!");
        return;
    }

    // Rastgele bir dosya seçmek için 1 ile 25 arasında bir sayı üret
    const randomIndex = Math.floor(Math.random() * 25) + 1;
    const audioFile = `audio/file${randomIndex}.mp3`;

    // Seçilen dosyayı çal ve sunucuya bildir
    const audio = new Audio(audioFile);
    try {
        await audio.play();
        alert(`${selectedCourse} için Hafta ${selectedWeek} yoklaması başlatıldı! Ses dosyası çalınıyor...`);

        // FormData ile ses dosyasını ve diğer bilgileri ekleyin
        const formData = new FormData();
        formData.append('course', selectedCourse);
        formData.append('week', selectedWeek);
        formData.append('audio', new File([audio], audioFile));

        // Sunucuya yoklama bilgisi gönder
        const response = await fetch('http://127.0.0.1:5000/api/attendance', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error("Sunucuya yoklama bilgisi gönderilirken bir hata oluştu.");
        }
        console.log(`Yoklama bilgisi sunucuya gönderildi: ${selectedCourse}, Hafta ${selectedWeek}`);
    } catch (error) {
        console.error(error);
        alert("Ses dosyası oynatılamadı veya yoklama bilgisi gönderilemedi: " + error.message);
    }
});
