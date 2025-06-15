// Initialize animations for landing page
document.addEventListener('DOMContentLoaded', function() {
    // Add visible class to animate elements
    const animatedElements = document.querySelectorAll('.animate-fade-in');
    animatedElements.forEach(element => {
        element.classList.add('visible');
    });

    // Intersection Observer for scroll-based animations
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    }, { threshold: 0.1 });

    animatedElements.forEach(element => {
        observer.observe(element);
    });

    // Smooth scrolling for navbar links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            const targetElement = document.querySelector(targetId);
            
            if (targetElement) {
                const offset = 80; // Fixed navbar height
                const elementPosition = targetElement.getBoundingClientRect().top;
                const offsetPosition = elementPosition + window.pageYOffset - offset;
                
                window.scrollTo({
                    top: offsetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });
});

// Location filtering and display
var lokasiData = [
    "UIN Raden Fatah Kampus B Jakabaring",
    "Rumah Sakit Charitas",
    "Universitas Sriwijaya Indralaya",
    "PTC(Palembang Trade Center)Mall",
    "PIM(Palembang Indah Mall)",
    "Hotel Harper",
    "Hotel The Zuri",
    "Transmart Palembang",
    "PS(Palembang Square)",
    "RSUD Mohammad Husein"
];

function showLokasiList() {
    var lokasiList = document.getElementById("lokasiList");
    lokasiList.innerHTML = "";
    lokasiData.forEach(function(item) {
        var option = document.createElement("div");
        option.className = "location-item";
        option.innerHTML = '<i class="fas fa-map-marker-alt me-2"></i>' + item;
        option.onclick = function() {
            document.getElementById("lokasi").value = item;
            lokasiList.style.display = 'none';
            hitungBiaya();
        };
        lokasiList.appendChild(option);
    });
    lokasiList.style.display = 'block';
}

function filterLokasi() {
    var query = document.getElementById("lokasi").value.toLowerCase();
    var lokasiList = document.getElementById("lokasiList");
    lokasiList.innerHTML = "";

    if (query) {
        var filtered = lokasiData.filter(function(item) {
            return item.toLowerCase().includes(query);
        });
        filtered.forEach(function(item) {
            var option = document.createElement("div");
            option.className = "location-item";
            option.innerHTML = '<i class="fas fa-map-marker-alt me-2"></i>' + item;
            option.onclick = function() {
                document.getElementById("lokasi").value = item;
                lokasiList.style.display = 'none';
                hitungBiaya();
            };
            lokasiList.appendChild(option);
        });
        lokasiList.style.display = 'block';
    } else {
        lokasiList.style.display = 'none';
    }
}

// Close location dropdown when clicking outside
document.addEventListener("click", function(event) {
    var lokasiList = document.getElementById("lokasiList");
    var lokasiInput = document.getElementById("lokasi");
    if (lokasiList && lokasiInput && !lokasiList.contains(event.target) && event.target !== lokasiInput) {
        lokasiList.style.display = 'none';
    }
});

// Cost calculation
function hitungBiaya() {
    var kendaraan = document.getElementById('kendaraan').value;
    var waktu = parseInt(document.getElementById('waktu').value) || 0;
    var biayaPreview = document.getElementById('biayaPreview');
    var estimasiBiaya = document.getElementById('estimasiBiaya');

    if (kendaraan && waktu > 0) {
        var biayaDasar = 0;
        var biayaTambahan = 0;

        if (kendaraan === 'Motor') {
            biayaDasar = 3000;  // Rp 3.000 untuk jam pertama
            if (waktu > 1) {
                var jamTambahan = waktu - 1;
                biayaTambahan = jamTambahan * 2000;  // Rp 2.000 per jam
            }
        } else if (kendaraan === 'Mobil') {
            biayaDasar = 5000; // Rp 5.000 untuk jam pertama
            if (waktu > 1) {
                var jamTambahan = waktu - 1;
                biayaTambahan = jamTambahan * 3000;  // Rp 3.000 per jam
            }
        }

        var totalBiaya = biayaDasar + biayaTambahan;
        estimasiBiaya.textContent = totalBiaya.toLocaleString('id-ID');
        biayaPreview.style.display = 'block';
    } else {
        biayaPreview.style.display = 'none';
    }
}

// Form validation and plate number combination
function combinePlatNomor(event) {
    var prefix = document.getElementById('plat_prefix').value.trim();
    var number = document.getElementById('plat_number').value.trim();
    var suffix = document.getElementById('plat_suffix').value.trim();

    if (!prefix.match(/^[A-Za-z]{1,2}$/)) {
        alert('Prefix plat harus 1-2 huruf.');
        event.preventDefault();
        return false;
    }
    if (!number.match(/^[0-9]{1,4}$/)) {
        alert('Nomor plat harus 1-4 angka.');
        event.preventDefault();
        return false;
    }
    if (!suffix.match(/^[A-Za-z]{1,3}$/)) {
        alert('Suffix plat harus 1-3 huruf.');
        event.preventDefault();
        return false;
    }

    var combined = prefix.toUpperCase() + number + suffix.toUpperCase();
    document.getElementById('plat_nomor').value = combined;
    return true;
}

// Star rating system
const stars = document.querySelectorAll('#starRating .star');
const ratingInput = document.getElementById('feedbackRating');

stars.forEach(star => {
    star.addEventListener('click', function() {
        const rating = parseInt(this.getAttribute('data-value'));
        ratingInput.value = rating;
        updateStars(rating);
    });
});

function updateStars(rating) {
    stars.forEach(star => {
        if (parseInt(star.getAttribute('data-value')) <= rating) {
            star.classList.add('active');
        } else {
            star.classList.remove('active');
        }
    });
}

// Feedback form submission
document.getElementById('feedbackForm')?.addEventListener('submit', function(e) {
    e.preventDefault();
    var lokasi = document.getElementById('feedbackLokasi').value;
    var rating = document.getElementById('feedbackRating').value;
    var review_text = document.getElementById('feedbackText').value;

    if (!lokasi || !rating) {
        alert('Lokasi dan rating wajib diisi.');
        return;
    }

    fetch('/submit_review', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: new URLSearchParams({
            lokasi: lokasi,
            rating: rating,
            review_text: review_text
        })
    })
    .then(response => response.json())
    .then(data => {
        var messageDiv = document.getElementById('feedbackMessage');
        if (data.error) {
            messageDiv.innerHTML = '<div class="alert alert-danger glass-card">' + data.error + '</div>';
        } else {
            messageDiv.innerHTML = '<div class="alert alert-success glass-card">' + data.message + '</div>';
            document.getElementById('feedbackForm').reset();
            updateStars(0);
        }
    })
    .catch(error => {
        var messageDiv = document.getElementById('feedbackMessage');
        messageDiv.innerHTML = '<div class="alert alert-danger glass-card">Terjadi kesalahan saat mengirim feedback.</div>';
    });
});

// Initialize tooltips
var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
});
