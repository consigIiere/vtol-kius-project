from flask import Flask, jsonify, request, render_template
import random

app = Flask(__name__)

# Глобальний стан нашого гібридного БПЛА (спрощена математична модель)
drone_state = {
    "mode": "Очікування", # Можливі: Очікування, VTOL, Літак, RTH
    "altitude": 0.0,
    "speed": 0.0,
    "battery": 100.0,
    "motor_temp": 40.0
}

# Функція, яка імітує фізику польоту (змінює параметри при кожному запиті)
def update_physics():
    global drone_state
    
    # Батарея потроху сідає завжди під час роботи системи
    if drone_state["battery"] > 0:
        drone_state["battery"] -= random.uniform(0.1, 0.3)
    
    # Математика для різних режимів польоту КІУС
    if drone_state["mode"] == "VTOL":
        if drone_state["altitude"] < 30.0:
            drone_state["altitude"] += 2.5  # Набираємо висоту (вертикальний зліт)
        drone_state["speed"] = random.uniform(0, 5)  # Горизонтальної швидкості майже немає
        drone_state["motor_temp"] = min(95.0, drone_state["motor_temp"] + random.uniform(0.5, 2.0))  # Підйомні мотори сильно гріються
        
    elif drone_state["mode"] == "Літак":
        drone_state["speed"] = min(90.0, drone_state["speed"] + 5.0)  # Розганяємось маршовим двигуном
        # В літаковому режимі підйомні мотори вимкнені, тому вони охолоджуються потоком повітря
        drone_state["motor_temp"] = max(40.0, drone_state["motor_temp"] - random.uniform(1.0, 3.0)) 
        
    elif drone_state["mode"] == "RTH":
        # Повернення додому: спочатку гасимо швидкість, потім знижуємо висоту
        drone_state["speed"] = max(0.0, drone_state["speed"] - 5.0)
        if drone_state["speed"] == 0:
            drone_state["altitude"] = max(0.0, drone_state["altitude"] - 2.0)
        
    # Округлюємо всі значення до 1 знаку після коми для красивого виводу
    for key in ["altitude", "speed", "battery", "motor_temp"]:
        drone_state[key] = round(max(0.0, drone_state[key]), 1)

# Маршрут 1: Віддає візуальний інтерфейс
@app.route('/')
def index():
    return render_template('index.html')

# Маршрут 2: Інформаційна підсистема (віддає телеметрію)
@app.route('/api/telemetry', methods=['GET'])
def get_telemetry():
    update_physics() # Прораховуємо нові координати перед відправкою
    return jsonify(drone_state)

# Маршрут 3: Управляюча підсистема (приймає команди)
@app.route('/api/command', methods=['POST'])
def send_command():
    global drone_state
    data = request.json
    command = data.get('command')
    
    # Виводимо команду в консоль сервера для логування
    print(f"[КІУС ЛОГ] Отримано команду від наземної станції: {command}")
    
    if command == "Зліт":
        drone_state["mode"] = "VTOL"
    elif command == "Перехід":
        drone_state["mode"] = "Літак"
    elif command == "Повернення":
        drone_state["mode"] = "RTH"
        
    return jsonify({"status": "success", "message": f"Команду {command} прийнято та інтегровано"})

if __name__ == '__main__':
    # Запускаємо сервер (Наземну станцію)
    app.run(debug=True, port=5000)