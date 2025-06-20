// Dark Mode Toggle Function
function toggleDarkMode() {
    const darkModeToggle = document.getElementById('darkModeToggle');
    const isDarkMode = darkModeToggle.checked;

    // Save to Local Storage
    localStorage.setItem('theme', isDarkMode ? 'dark' : 'light');

    // Toggle Bootstrap Theme
    document.documentElement.setAttribute('data-bs-theme', isDarkMode ? 'dark' : 'light');

    // Toggle Navbar Colors
    const navbar = document.querySelector('.navbar');
    if (navbar) {
        navbar.classList.toggle('navbar-light', !isDarkMode);
        navbar.classList.toggle('bg-light', !isDarkMode);
        navbar.classList.toggle('navbar-dark', isDarkMode);
        navbar.classList.toggle('bg-dark', isDarkMode);
    }

    // Toggle Map Dark Mode
    if (isDarkMode) {
        map.removeLayer(lightModeLayer);
        darkModeLayer.addTo(map);
    } else {
        map.removeLayer(darkModeLayer);
        lightModeLayer.addTo(map);
    }
}

// Initialize Theme on Load
function initTheme() {
    const savedTheme = localStorage.getItem('theme');
    const darkModeToggle = document.getElementById('darkModeToggle');

    if (savedTheme === 'dark') {
        darkModeToggle.checked = true;
        document.documentElement.setAttribute('data-bs-theme', 'dark');

        // Navbar And Map Dark Mode
        const navbar = document.querySelector('.navbar');
        if (navbar) {
            navbar.classList.remove('navbar-light', 'bg-light');
            navbar.classList.add('navbar-dark', 'bg-dark');
        }
        if (map) {
            map.removeLayer(lightModeLayer);
            darkModeLayer.addTo(map);
        }
    }
}

// Event Listeners
document.addEventListener('DOMContentLoaded', initTheme);
document.getElementById('darkModeToggle').addEventListener('change', toggleDarkMode);


window.onload = function() {
    const urlParams = new URLSearchParams(window.location.search);

    if (urlParams.get("country_error") === "true") {
        Swal.fire({
            title: "Error!",
                text: "invalid country",
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
};




// using leaflet.js to display the map
var map = L.map('map').setView([20, 0], 3); // [Latitude, Longitude], Zoom Level

// Define Light Mode and Dark Mode Tile Layers
var lightModeLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
});

var darkModeLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
  attribution: '&copy; OpenStreetMap & CartoDB'
});

// Add default tile layer (Light Mode)
lightModeLayer.addTo(map);

fetch('/get_crisis_countries')
  .then(response => response.json())
  .then(data => {
    var crisisLocations = data.crisis_countries;

    if (crisisLocations.length > 0) {
      crisisLocations.forEach(function(location) {
        var imageUrl = location.imageUrl || '/static/assets/images/hero-active.jpg';

        if (location.lat && location.lng) {
          var popupContent = `
            <div class="container">
              <div class="row">
                <div class="col-md-12">
                  <h5 class="display-6 fw-bold text-body-emphasis mb-3"><b>${location.name}</b></h5>
                  <img src="${location.img}" alt="Crisis Image" class="img-fluid mb-2" style="width: 100%; max-height: 200px; object-fit: cover;" />
                  <p class="lead">${location.news}</p>
                  <a href="https://www.redcross.org/donate/donation.html/" class="btn btn-primary btn-lg px-4 me-md-2" style="color: white" target="_blank">Donate</a>
                </div>
              </div>
            </div>
          `;

          var marker = L.marker([location.lat, location.lng], {
            color: 'indianred',
            fillColor: 'indianred',
            fillOpacity: 0.8,
            radius: 8
          }).addTo(map)
            .bindPopup(popupContent)
            .openPopup();

          marker.getPopup().getElement().style.width = "350px";
          marker.getPopup().getElement().style.height = "auto";
        } else {
          console.warn('Missing lat or lng for location:', location.name);
        }
      });
    } else {
      console.warn('No crisis locations found.');
    }
  })
  .catch(error => {
    console.error('Error fetching crisis countries:', error);
  });
