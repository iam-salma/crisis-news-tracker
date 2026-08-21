// Global map and layer references
var map = null;
var lightModeLayer = null;
var darkModeLayer = null;

// Dark Mode Toggle Function
function toggleDarkMode() {
    const currentTheme = document.documentElement.getAttribute('data-bs-theme') || localStorage.getItem('theme') || 'light';
    const isDarkMode = currentTheme !== 'dark';

    // Save to Local Storage
    localStorage.setItem('theme', isDarkMode ? 'dark' : 'light');

    // Toggle Bootstrap Theme
    document.documentElement.setAttribute('data-bs-theme', isDarkMode ? 'dark' : 'light');

    // Sync all toggle checkboxes across desktop and mobile nav
    ['darkModeToggle', 'darkModeToggleMobile', 'darkModeToggleDrawer'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.checked = isDarkMode;
    });

    // Toggle Main Map Dark Mode if it exists
    if (map && lightModeLayer && darkModeLayer) {
        if (isDarkMode) {
            if (map.hasLayer(lightModeLayer)) map.removeLayer(lightModeLayer);
            darkModeLayer.addTo(map);
        } else {
            if (map.hasLayer(darkModeLayer)) map.removeLayer(darkModeLayer);
            lightModeLayer.addTo(map);
        }
    }
}

// Initialize Theme on Load
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    const isDarkMode = savedTheme === 'dark';

    document.documentElement.setAttribute('data-bs-theme', savedTheme);

    // Sync all toggles
    ['darkModeToggle', 'darkModeToggleMobile', 'darkModeToggleDrawer'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.checked = isDarkMode;
    });

    // Toggle Main Map Dark Mode if it exists
    if (map && lightModeLayer && darkModeLayer) {
        if (isDarkMode) {
            if (map.hasLayer(lightModeLayer)) map.removeLayer(lightModeLayer);
            darkModeLayer.addTo(map);
        } else {
            if (map.hasLayer(darkModeLayer)) map.removeLayer(darkModeLayer);
            lightModeLayer.addTo(map);
        }
    }
}

// Event Listeners
document.addEventListener('DOMContentLoaded', initTheme);

window.onload = function() {
    const urlParams = new URLSearchParams(window.location.search);

    if (urlParams.get("country_error") === "true") {
        Swal.fire({
            title: "Error!",
            text: "Invalid or unsupported country search.",
            icon: "error",
            confirmButtonText: "OK",
            timer: 3000,
            timerProgressBar: true
        });
    }

    if (urlParams.get("email_success") === "true") {
        Swal.fire({
            title: "Success!",
            text: "Your email has been saved successfully.",
            icon: "success",
            confirmButtonText: "OK",
            timer: 3000,
            timerProgressBar: true
        });
    }

    if (urlParams.get("error") === "true") {
        Swal.fire({
            title: "Error!",
            text: "This email already exists in the database.",
            icon: "error",
            confirmButtonText: "OK",
            timer: 3000,
            timerProgressBar: true
        });
    }

    // Note: Dedicated map views (locate.html / news_article.html) manage their own specialized map instances.
};

// Audio Speed Controller
function setAudioSpeed(audioId, speed, btnEl) {
    const audio = document.getElementById(audioId);
    if (audio) {
        audio.playbackRate = speed;
    }
    if (btnEl && btnEl.parentElement) {
        btnEl.parentElement.querySelectorAll('.btn-speed').forEach(b => {
            b.classList.remove('active', 'btn-primary');
            b.classList.add('btn-outline-secondary');
        });
        btnEl.classList.add('active');
    }
}

// Auto-set energetic broadcast tempo (1.15x) when audio starts playing
document.addEventListener('play', function(e) {
    if (e.target && e.target.tagName === 'AUDIO') {
        if (!e.target.dataset.customSpeedSet) {
            e.target.playbackRate = 1.15;
            e.target.dataset.customSpeedSet = 'true';
        }
    }
}, true);

