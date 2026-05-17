// ІНІЦІАЛІЗАЦІЯ МАПИ
const map = L.map('map').setView([50.4000, 30.3333], 15); 
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', { maxZoom: 19 }).addTo(map);

// Іконка дрона (Світло-сірий військовий колір)
const droneIcon = L.divIcon({ 
    html: `<svg width="30" height="30" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg">
        <circle cx="20" cy="20" r="4" fill="#9ca3af" stroke="#fff" stroke-width="2"/>
        <line x1="20" y1="20" x2="6" y2="6" stroke="#9ca3af" stroke-width="2"/><line x1="20" y1="20" x2="34" y2="6" stroke="#9ca3af" stroke-width="2"/><line x1="20" y1="20" x2="6" y2="34" stroke="#9ca3af" stroke-width="2"/><line x1="20" y1="20" x2="34" y2="34" stroke="#9ca3af" stroke-width="2"/>
        <circle cx="6" cy="6" r="3" fill="#fff" stroke="#9ca3af" stroke-width="1.5"/><circle cx="34" cy="6" r="3" fill="#fff" stroke="#9ca3af" stroke-width="1.5"/><circle cx="6" cy="34" r="3" fill="#fff" stroke="#9ca3af" stroke-width="1.5"/><circle cx="34" cy="34" r="3" fill="#fff" stroke="#9ca3af" stroke-width="1.5"/>
    </svg>`, className: '', iconSize: [30, 30], iconAnchor: [15, 15] 
});

// Іконка бази (Тактичний квадрат HQ)
const vanIcon = L.divIcon({
    html: '<div style="background: #064e3b; border: 2px solid #10b981; color: #10b981; font-family: monospace; font-size: 10px; line-height: 20px; text-align: center; width: 24px; height: 24px;">HQ</div>',
    className: '', iconSize: [24, 24], iconAnchor: [12, 12]
});

// Іконка вогню (Тактичний червоний ромб)
const fireIcon = L.divIcon({
    html: '<div class="fire-pulse" style="width: 20px; height: 20px; background: rgba(220, 38, 38, 0.5); border: 2px solid #ef4444; transform: rotate(45deg);"></div>',
    className: '', iconSize: [20, 20], iconAnchor: [10, 10]
});

L.marker([50.4000, 30.3333], {icon: vanIcon}).addTo(map);
let droneMarker = L.marker([50.4000, 30.3333], {icon: droneIcon}).addTo(map);
let flightPath = L.polyline([], {color: '#10b981', weight: 2, dashArray: '5, 5'}).addTo(map); // Зелений пунктир

let targetMarker = null; 
let fireMarker = null;
let mapClickMode = 'fire'; 
let lastLogCount = 0; 

// УПРАВЛІННЯ ІНТЕРФЕЙСОМ
window.setMapMode = function(mode) {
    mapClickMode = mode;
    document.getElementById('btn-fire').classList.toggle('opacity-50', mode !== 'fire');
    document.getElementById('btn-target').classList.toggle('opacity-50', mode !== 'target');
};

window.togglePhoto = function() {
    const container = document.getElementById('photo-container');
    container.classList.toggle('hidden');
};

// ОБРОБКА КЛІКІВ ПО МАПІ
map.on('click', async function(e) {
    const { lat, lng } = e.latlng;
    
    if (mapClickMode === 'fire') {
        if (fireMarker) map.removeLayer(fireMarker);
        fireMarker = L.marker([lat, lng], {icon: fireIcon, draggable: true}).addTo(map);
        let coreTemp = Math.floor(Math.random() * 151) + 300;
        
        await fetch('/api/command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command: 'SetFire', lat: lat, lng: lng, temp: coreTemp })
        });
        
        fireMarker.on('dragend', async function(event) {
            const position = event.target.getLatLng();
            await fetch('/api/command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: 'SetFire', lat: position.lat, lng: position.lng, temp: coreTemp })
            });
        });
        
        setMapMode('target'); 
        
    } else if (mapClickMode === 'target') {
        if (targetMarker) map.removeLayer(targetMarker);
        targetMarker = L.circleMarker([lat, lng], { color: '#10b981', radius: 6, fillOpacity: 0.8, fillColor: '#064e3b' }).addTo(map);
        await fetch('/api/command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command: 'SetTarget', lat: lat, lng: lng })
        });
    }
});

// ІНІЦІАЛІЗАЦІЯ ГРАФІКА (Військові кольори)
const ctx = document.getElementById('flightChart').getContext('2d');
const flightChart = new Chart(ctx, {
    type: 'line',
    data: { labels: [], datasets: [
        { label: 'ВИСОТА (М)', borderColor: '#06b6d4', data: [], yAxisID: 'y', tension: 0.1, borderWidth: 1, pointRadius: 0 },
        { label: 'ШВИДКІСТЬ (КМ/ГОД)', borderColor: '#a855f7', data: [], yAxisID: 'y1', tension: 0.1, borderWidth: 1, pointRadius: 0 }
    ]},
    options: { animation: false, responsive: true, maintainAspectRatio: false, color: '#9ca3af',
        scales: {
            x: { ticks: { color: '#4b5563', font: {family: 'monospace'} }, grid: { color: '#374151' } },
            y: { type: 'linear', position: 'left', ticks: { color: '#06b6d4', font: {family: 'monospace'} }, grid: { color: '#374151' } },
            y1: { type: 'linear', position: 'right', grid: { display: false }, ticks: { color: '#a855f7', font: {family: 'monospace'} } }
        },
        plugins: { legend: { labels: { font: {family: 'monospace'} } } }
    }
});

let timeSeconds = 0;

// ОТРИМАННЯ ТЕЛЕМЕТРІЇ
window.fetchTelemetry = async function() {
    try {
        const response = await fetch('/api/telemetry');
        const data = await response.json();

        document.getElementById('val-mode').innerText = data.mode;
        document.getElementById('val-alt').innerText = data.altitude + " М";
        document.getElementById('val-speed').innerText = data.speed + " КМ/ГОД";
        document.getElementById('val-battery').innerText = data.battery + " %";
        document.getElementById('val-gtemp').innerText = data.ground_temp;

        // ВІЗУАЛІЗАЦІЯ ТЯГИ МОТОРІВ
        document.getElementById('val-thrust-vtol').innerText = data.thrust_vtol.toFixed(1) + '%';
        document.getElementById('bar-thrust-vtol').style.width = data.thrust_vtol + '%';
        
        document.getElementById('val-thrust-main').innerText = data.thrust_main.toFixed(1) + '%';
        document.getElementById('bar-thrust-main').style.width = data.thrust_main + '%';

        // Консоль логів
        if (data.logs && data.logs.length !== lastLogCount) {
            const consoleEl = document.getElementById('console-output');
            consoleEl.innerHTML = data.logs.map(log => `<div>> ${log}</div>`).join('');
            consoleEl.scrollTop = consoleEl.scrollHeight; 
            lastLogCount = data.logs.length;
        }

        if (data.photo_ready) {
            document.getElementById('btn-photo').classList.remove('hidden');
            document.querySelector('#photo-container img').src = `/static/${data.current_photo}`;
        } else {
            document.getElementById('btn-photo').classList.add('hidden');
            document.getElementById('photo-container').classList.add('hidden');
        }

        // Візуальна діагностика стану (Строгі стилі)
        const baseClass = "bg-neutral-900 p-3 border border-neutral-700 border-l-4 ";
        
        const modeCard = document.getElementById('card-mode');
        if (data.mode === "Аварійна посадка") {
            modeCard.className = baseClass + "border-l-red-600 animate-pulse";
        } else {
            modeCard.className = baseClass + "border-l-emerald-600";
        }

        const batCard = document.getElementById('card-battery');
        if (data.mode === "Очікування" && data.battery < 100) {
            batCard.className = baseClass + "border-l-emerald-400";
        } else if (data.battery < 20) {
            batCard.className = baseClass + "border-l-red-600";
        } else {
            batCard.className = baseClass + "border-l-emerald-600";
        }

        const tempCard = document.getElementById('card-temp');
        if (data.ground_temp > 100) {
            tempCard.className = baseClass + "border-l-red-600 transition-colors animate-pulse";
        } else if (data.ground_temp > 50) {
            tempCard.className = baseClass + "border-l-orange-500 transition-colors";
        } else {
            tempCard.className = baseClass + "border-l-amber-500 transition-colors";
        }

        if ((data.mode === 'RTH' || data.mode === "Аварійна посадка") && fireMarker) {
            map.removeLayer(fireMarker);
            fireMarker = null;
        }

        const newLatLng = new L.LatLng(data.lat, data.lng);
        droneMarker.setLatLng(newLatLng); 
        flightPath.addLatLng(newLatLng);  
        map.panTo(newLatLng); 

        timeSeconds++;
        flightChart.data.labels.push(timeSeconds);
        flightChart.data.datasets[0].data.push(data.altitude);
        flightChart.data.datasets[1].data.push(data.speed);

        if (flightChart.data.labels.length > 30) {
            flightChart.data.labels.shift();
            flightChart.data.datasets[0].data.shift();
            flightChart.data.datasets[1].data.shift();
        }
        flightChart.update('none');

    } catch (error) {
        console.error("ПОМИЛКА ЗВ'ЯЗКУ З СЕРВЕРОМ:", error);
    }
};

window.sendCommand = async function(cmd) {
    await fetch('/api/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmd })
    });
};

fetchTelemetry(); 
setInterval(fetchTelemetry, 1000);