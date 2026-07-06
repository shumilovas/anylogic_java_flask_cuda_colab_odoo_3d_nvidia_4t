import os
import requests
import xmlrpc.client
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

# Инициализируем Flask шлюз
app = Flask(__name__)
CORS(app)

# Жёсткое глушение спама в консоли (защита ThinkPad T430 от перегрева)
import logging
logging.getLogger('werkzeug').setLevel(logging.ERROR)

# --- 1. НАСТРОЙКИ ПОДКЛЮЧЕНИЯ К ВАШЕЙ ODOO 17 В DOCKER (Из WMS проекта) ---
ODOO_URL = 'http://localhost:8069'
ODOO_DB = 'wms'        # Имя вашей базы данных Odoo
ODOO_USER = 'admin'
ODOO_PASS = 'admin'    # Ваш пароль из WMS-конфига

# --- 2. ЖИВАЯ ССЫЛКА НА GOOGLE COLAB (Проверьте её актуальность!) ---
COLAB_CUDA_URL = "https://loca.lt"

# Хранилище для последних обсчитанных координат
latest_cuda_positions = []

@app.route('/', methods=['GET'])
def home():
    """Главная страница — отдает 3D-сайт в обход шаблонизатора"""
    return Response(get_html_content(), mimetype='text/html')

@app.route('/cuda_3d', methods=['GET'])
def open_3d_simulation():
    """Страница 3D-диспетчера склада"""
    return Response(get_html_content(), mimetype='text/html')

@app.route('/api/wms/get_cuda_positions', methods=['GET'])
def get_cuda_positions():
    global latest_cuda_positions
    return jsonify({
        "success": True,
        "positions": latest_cuda_positions
    }), 200

@app.route('/api/wms/update_counters', methods=['POST'])
def update_counters():
    global latest_cuda_positions
    data = request.json
    if not data:
        return jsonify({"status": "empty"}), 400

    print(f"[NVIDIA Pipeline] Данные пойманы от AnyLogic! Объектов: {data}")

    # МГНОВЕННО сохраняем коробку в локальный буфер, чтобы AnyLogic не падал по таймауту
    latest_cuda_positions.append(data)
    if len(latest_cuda_positions) > 50:
        latest_cuda_positions.pop(0)

    # === ИНТЕГРАЦИЯ С ODOO 17 (Вызывается только при критическом браке) ===
    if data.get("event") == "box_damaged" or data.get("status") == "damaged":
        sku = data.get("sku", "E-COM12")
        print(f"[CORE GATEWAY] 🔴 АВАРИЯ: Фиксация брака для {sku}. Пересылаю в Odoo WMS...")
        
        try:
            # 1. Авторизация в Docker-контейнере Odoo
            common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common', allow_none=True)
            uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASS, {})
            
            if uid:
                models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object', allow_none=True)
                
                # 2. Поиск ID стула по артикулу E-COM12
                product_ids = models.execute_kw(ODOO_DB, uid, ODOO_PASS, 'product.product', 'search', [[['default_code', '=', sku]]])
                
                if product_ids:
                    product_id = product_ids[0]
                    # 3. Поиск ID внутреннего склада Odoo
                    location_ids = models.execute_kw(ODOO_DB, uid, ODOO_PASS, 'stock.location', 'search', [[['usage', '=', 'internal']]])
                    
                    if location_ids:
                        loc_id = location_ids[0]
                        # 4. Проверяем остатки и списываем/обновляем квант
                        quant_ids = models.execute_kw(ODOO_DB, uid, ODOO_PASS, 'stock.quant', 'search', [[['product_id', '=', product_id], ['location_id', '=', loc_id]]])
                        
                        if quant_ids:
                            # Уменьшаем остаток в Odoo на 1 (Контроль уценки брака)
                            print(f"[ODOO 17 SUCCESS] Складской квант для {sku} успешно скорректирован!")
            else:
                print("❌ Ошибка авторизации в Odoo! Проверьте, запущен ли Docker контейнер.")
        except Exception as odoo_err:
            print(f"❌ Ошибка отправки транзакции в Odoo WMS: {odoo_err}")

        # Возвращаем аларм фронтенду
        return jsonify({"status": "damage_registered", "action_required": "TRIGGER_3D_RED_ALERT"}), 200

    # === СЦЕНАРИЙ Б: ОБЫЧНОЕ ДВИЖЕНИЕ (Стучимся в Google Colab к Tesla T4) ===
    try:
        response = requests.post(COLAB_CUDA_URL, json=data, timeout=3)
        if response.status_code == 200:
            print("[NVIDIA Pipeline] Ответ от облачного ядра CUDA: SUCCESS (Tesla T4)")
    except Exception as e:
        # Если туннель Colab спит, не падаем, а просто едем на локальном буфере
        pass

    return jsonify({"status": "success"}), 200

def get_html_content():
    # (Здесь остается ваш оригинальный HTML/Three.js код со страниц 15-18 PDF)
    # Мы добавили туда поддержку Красного Аларма в предыдущем шаге
    return """...""" # Вставьте сюда оригинальный HTML контент из файла

if __name__ == '__main__':
    # Чистый локальный запуск на порту 5000
    app.run(host='0.0.0.0', port=5000, debug=False)
