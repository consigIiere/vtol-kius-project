from flask import Flask, jsonify, request, render_template
import random
import math
from datetime import datetime

app = Flask(__name__)

# Стан КІУС
drone_state = {
    "mode": "Очікування",
    "altitude": 0.0,
    "speed": 0.0,
    "battery": 100.0,
    "motor_temp": 40.0,
    "ground_temp": 20.0, 
    "photo_ready": False,
    "current_photo": "fire1.jpg", 
    "lat": 50.4000, 
    "lng": 30.3333,
    "home_lat": 50.4000,
    "home_lng": 30.3333,
    "target_lat": None,
    "target_lng": None,
    "fire_lat": None,
    "fire_lng": None,
    "fire_core_temp": 300.0,
    "thrust_vtol": 0.0,
    "thrust_main": 0.0,
    "logs": []
}

base_physics = {
    "altitude": 0.0,
    "speed": 0.0,
    "raw_thrust_vtol": 0.0, 
    "raw_thrust_main": 0.0  
}

def add_log(msg):
    t = datetime.now().strftime("%H:%M:%S")
    drone_state["logs"].append(f"[{t}] {msg}")
    if len(drone_state["logs"]) > 30:
        drone_state["logs"].pop(0)

add_log("СИСТЕМУ ІНІЦІАЛІЗОВАНО. КІУС ГОТОВА ДО РОБОТИ.")

def calc_dist(lat1, lng1, lat2, lng2):
    if lat1 is None or lat2 is None: return 999999
    dx = lat1 - lat2
    dy = lng1 - lng2
    return math.sqrt((dx * 111000)**2 + (dy * 71000)**2)

def update_physics():
    global drone_state, base_physics
    
    tgt_vtol = 0.0
    tgt_main = 0.0
    
    if drone_state["mode"] == "Очікування":
        if drone_state["battery"] < 100.0:
            drone_state["battery"] = min(100.0, drone_state["battery"] + 2.5)
            if drone_state["battery"] == 100.0:
                add_log("БАТАРЕЯ ЗАРЯДЖЕНА. БПЛА ГОТОВИЙ ДО МІСІЇ.")
    elif drone_state["battery"] > 0:
        drain = 0.2 if drone_state["mode"] == "VTOL" else 0.1
        drone_state["battery"] -= random.uniform(drain, drain + 0.1)
        
    if drone_state["battery"] < 0: drone_state["battery"] = 0.0
        
    if drone_state["battery"] <= 0.0 and drone_state["mode"] not in ["Аварійна посадка", "Очікування"]:
        drone_state["mode"] = "Аварійна посадка"
        add_log("КРИТИЧНА ВІДМОВА: БАТАРЕЯ 0%. АВАРІЙНА ПОСАДКА!")
    elif drone_state["battery"] <= 10.0 and drone_state["mode"] not in ["RTH", "Аварійна посадка", "Очікування"]:
        drone_state["mode"] = "RTH"
        drone_state["target_lat"] = None
        add_log("УВАГА: ЗАРЯД < 10%. ПРИМУСОВЕ ПОВЕРНЕННЯ (RTH).")

    dist_fire = calc_dist(drone_state["lat"], drone_state["lng"], drone_state["fire_lat"], drone_state["fire_lng"])
    ground_temp_xy = 20.0
    if dist_fire < 150: 
        ground_temp_xy = 20.0 + (150 - dist_fire) * ((drone_state["fire_core_temp"] - 20.0) / 150.0)
        
    alt_factor = max(0.0, 1.0 - (base_physics["altitude"] / 100.0))
    drone_state["ground_temp"] = 20.0 + (ground_temp_xy - 20.0) * alt_factor + random.uniform(-1.0, 1.0)
        
    is_danger = drone_state["ground_temp"] > 45.0 
    if is_danger and drone_state["mode"] in ["Літак", "VTOL"]:
        if base_physics["altitude"] < 100.0: base_physics["altitude"] += 2.5 
    elif not is_danger and base_physics["altitude"] > 30.0 and drone_state["mode"] in ["Літак", "VTOL"]:
        base_physics["altitude"] -= 1.0

    if drone_state["mode"] == "Очікування":
        base_physics["speed"] = 0.0

    elif drone_state["mode"] == "VTOL":
        tgt_vtol = 65.0 if base_physics["altitude"] < 30.0 else 45.0
        base_physics["speed"] = max(0.0, base_physics["speed"] - 5.0) 
        drone_state["motor_temp"] = min(95.0, drone_state["motor_temp"] + random.uniform(0.5, 2.0))
        if base_physics["altitude"] < 30.0 and not is_danger:
            base_physics["altitude"] += 2.5
        
    elif drone_state["mode"] == "Літак":
        if not drone_state["target_lat"]:
            drone_state["mode"] = "VTOL"
            base_physics["speed"] = 0.0
            add_log("АВТОПІЛОТ: КОНФЛІКТ РЕЖИМІВ. СКИДАННЯ У VTOL.")
            return

        dist_target = calc_dist(drone_state["lat"], drone_state["lng"], drone_state["target_lat"], drone_state["target_lng"])
        
        if is_danger:
            tgt_speed = 30.0
            tgt_main = 40.0
            tgt_vtol = 0.0
        elif dist_target < 150:
            tgt_speed = max(10.0, (dist_target / 150.0) * 90.0)
            tgt_main = max(15.0, (dist_target / 150.0) * 85.0)
            tgt_vtol = 45.0 * (1.0 - dist_target/150.0) 
        else:
            tgt_speed = 90.0
            tgt_main = 85.0
            tgt_vtol = 0.0
            
        drone_state["motor_temp"] = max(40.0, drone_state["motor_temp"] - random.uniform(1.0, 3.0))
        
        if base_physics["speed"] < tgt_speed: base_physics["speed"] = min(tgt_speed, base_physics["speed"] + 5.0)
        elif base_physics["speed"] > tgt_speed: base_physics["speed"] = max(tgt_speed, base_physics["speed"] - 5.0)
        
        dx = drone_state["target_lat"] - drone_state["lat"]
        dy = drone_state["target_lng"] - drone_state["lng"]
        dist_deg = math.sqrt(dx**2 + dy**2)
        move_dist_deg = base_physics["speed"] * 0.000002
        
        if dist_target < 2 or dist_deg <= move_dist_deg:
            drone_state["lat"] = drone_state["target_lat"]
            drone_state["lng"] = drone_state["target_lng"]
            drone_state["mode"] = "VTOL"
            drone_state["target_lat"] = None
            add_log("ТОЧКУ МАРШРУТУ ДОСЯГНУТО. ЗАВИСАННЯ.")
            
            if dist_fire < 50 and not drone_state["photo_ready"]:
                drone_state["current_photo"] = random.choice(["fire1.png", "fire2.png", "fire3.png", "fire4.png"])
                add_log(f"ЦІЛЬ У ЗОНІ УРАЖЕННЯ. ДАНІ ПЕЙЛОАДУ ЗБЕРЕЖЕНО: {drone_state['current_photo']}")
                drone_state["photo_ready"] = True
        elif base_physics["speed"] > 0:
            drone_state["lat"] += (dx / dist_deg) * move_dist_deg
            drone_state["lng"] += (dy / dist_deg) * move_dist_deg
                
    elif drone_state["mode"] == "RTH":
        dist_home = calc_dist(drone_state["lat"], drone_state["lng"], drone_state["home_lat"], drone_state["home_lng"])
        
        dx = drone_state["home_lat"] - drone_state["lat"]
        dy = drone_state["home_lng"] - drone_state["lng"]
        dist_deg = math.sqrt(dx**2 + dy**2)
        
        if dist_home > 150: 
            tgt_speed = 90.0
            tgt_main = 85.0
            tgt_vtol = 0.0
        else: 
            tgt_speed = max(0.0, (dist_home / 150.0) * 90.0)
            tgt_main = max(0.0, (dist_home / 150.0) * 85.0)
            tgt_vtol = 45.0 * (1.0 - dist_home/150.0)
            
        if base_physics["speed"] < tgt_speed: base_physics["speed"] = min(tgt_speed, base_physics["speed"] + 5.0)
        elif base_physics["speed"] > tgt_speed: base_physics["speed"] = max(tgt_speed, base_physics["speed"] - 5.0)
        
        move_dist_deg = base_physics["speed"] * 0.000002
        
        if dist_home < 2 or dist_deg <= move_dist_deg:
            drone_state["lat"] = drone_state["home_lat"]
            drone_state["lng"] = drone_state["home_lng"]
            base_physics["speed"] = max(0.0, base_physics["speed"] - 5.0)
            
            if base_physics["speed"] == 0:
                base_physics["altitude"] = max(0.0, base_physics["altitude"] - 2.0)
                tgt_main = 0.0
                tgt_vtol = 35.0 
                if base_physics["altitude"] == 0:
                    drone_state["mode"] = "Очікування"
                    add_log("ПОСАДКА НА БАЗУ УСПІШНА. СИСТЕМИ ЖИВЛЕННЯ ВИМКНЕНО.")
        elif base_physics["speed"] > 0:
            drone_state["lat"] += (dx / dist_deg) * move_dist_deg
            drone_state["lng"] += (dy / dist_deg) * move_dist_deg
                    
    elif drone_state["mode"] == "Аварійна посадка":
        base_physics["speed"] = max(0.0, base_physics["speed"] - 10.0)
        tgt_main = 0.0
        tgt_vtol = 20.0
        if base_physics["speed"] == 0:
            base_physics["altitude"] = max(0.0, base_physics["altitude"] - 3.0)
            
    base_physics["raw_thrust_vtol"] += (tgt_vtol - base_physics["raw_thrust_vtol"]) * 0.2
    base_physics["raw_thrust_main"] += (tgt_main - base_physics["raw_thrust_main"]) * 0.2
    
    tv = base_physics["raw_thrust_vtol"] + (random.uniform(-2.0, 2.0) if base_physics["raw_thrust_vtol"] > 5 else 0)
    tm = base_physics["raw_thrust_main"] + (random.uniform(-2.0, 2.0) if base_physics["raw_thrust_main"] > 5 else 0)
    
    drone_state["thrust_vtol"] = max(0.0, min(100.0, tv))
    drone_state["thrust_main"] = max(0.0, min(100.0, tm))

    if drone_state["mode"] != "Очікування":
        noise_factor = 0.5 if base_physics["altitude"] > 0 else 0.0
        drone_state["altitude"] = max(0.0, base_physics["altitude"] + random.uniform(-noise_factor, noise_factor))
        drone_state["speed"] = max(0.0, base_physics["speed"] + random.uniform(-noise_factor * 2, noise_factor * 2))
        drone_state["motor_temp"] = drone_state["motor_temp"] + random.uniform(-0.2, 0.2)

    for key in ["altitude", "speed", "battery", "motor_temp", "ground_temp", "thrust_vtol", "thrust_main"]:
        drone_state[key] = round(drone_state[key], 1)
    for key in ["lat", "lng"]:
        drone_state[key] = round(drone_state[key], 6)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/telemetry', methods=['GET'])
def get_telemetry():
    update_physics()
    return jsonify(drone_state)

@app.route('/api/command', methods=['POST'])
def send_command():
    global drone_state
    data = request.json
    command = data.get('command')
    
    if command == "SetTarget":
        drone_state["target_lat"] = data.get('lat')
        drone_state["target_lng"] = data.get('lng')
        add_log("ПРИЙНЯТО КООРДИНАТИ ПАТРУЛЮВАННЯ.")
    elif command == "SetFire":
        drone_state["fire_lat"] = data.get('lat')
        drone_state["fire_lng"] = data.get('lng')
        drone_state["fire_core_temp"] = data.get('temp')
        drone_state["photo_ready"] = False 
        add_log(f"УВАГА: ОНОВЛЕНО КООРДИНАТИ ЦІЛІ (T: ~{data.get('temp')}°C).")
    elif command == "Зліт":
        if drone_state["battery"] < 10.0:
            add_log("ВІДМОВА В ДОСТУПІ: НИЗЬКИЙ ЗАРЯД БАТАРЕЇ.")
        else:
            drone_state["mode"] = "VTOL"
            add_log("КОМАНДА: ЗЛІТ (VTOL). ПІДЙОМНІ МОТОРИ АКТИВОВАНО.")
    elif command == "Перехід":
        if drone_state["mode"] == "Очікування":
            add_log("ВІДМОВА В ДОСТУПІ: ПОТРІБЕН ЗЛІТ.")
        elif not drone_state["target_lat"]:
            add_log("ВІДМОВА В ДОСТУПІ: ВІДСУТНЯ ЦІЛЬ МАРШРУТУ.")
        else:
            drone_state["mode"] = "Літак"
            add_log("КОМАНДА: ЛІТАК. МАРШРОВИЙ ДВИГУН АКТИВОВАНО.")
    elif command == "Повернення":
        drone_state["mode"] = "RTH"
        add_log("КОМАНДА: ПРИМУСОВЕ ПОВЕРНЕННЯ (RTH).")
        
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)