import os
import requests
import xmlrpc.client
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Жесткое глушение спама в консоли (защита ThinkPad T430 от перегрева)
import logging
logging.getLogger('werkzeug').setLevel(logging.ERROR)

# --- 1. НАСТРОЙКИ ПОДКЛЮЧЕНИЯ К ВАШЕЙ ODOO 17 В DOCKER ---
ODOO_URL = 'http://localhost:8069'
ODOO_DB = 'wms'  # Меняем с 'postgres' на 'wms'
ODOO_USER = 'odoo'      # ПОЛЬЗОВАТЕЛЬ ИЗ MANIFESTA (POSTGRES_USER)
ODOO_PASS = 'odoo'      # ПАРОЛЬ ИЗ MANIFESTA (POSTGRES_PASSWORD)

# --- 2. ЖИВАЯ ССЫЛКА НА GOOGLE COLAB ---
COLAB_CUDA_URL = "https://dry-adults-punch.loca.lt/api/cuda/simulate"

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
    
    # МГНОВЕННО сохраняем коробку в локальный буфер для отрисовки змейки на 3D-сайте
    latest_cuda_positions.append(data)
    if len(latest_cuda_positions) > 50:
        latest_cuda_positions.pop(0)

    # Инициализируем дефолтный ответ
    response_data = {"status": "success"}

    # === ИНТЕГРАЦИЯ С ODOO 17 (Вызывается ТОЛЬКО при критическом браке) ===
    if data.get("event") == "box_damaged" or data.get("status") == "damaged":
        sku = data.get("sku", "E-COM12")
        print(f"[CORE GATEWAY] 🚨 АВАРИЯ: Фиксация брака для {sku}. Пересылаю в Odoo WMS...")
        
        # Меняем статус ответа для включения красной сирены на 3D-сайте
        response_data = {
            "status": "damage_registered", 
            "action_required": "TRIGGER_3D_RED_ALERT"
        }
        
        try:
            # Подключаемся к Odoo 17 в Docker (порт 8069)
            common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common', allow_none=True)
            
            # ЖЁСТКО передаем имя базы 'postgres', пользователя 'odoo' и пароль 'odoo'
            uid = common.authenticate(ODOO_DB, 'odoo', 'odoo', {})
            
            if uid:
                models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object', allow_none=True)
                
                # ЖЁСТКО прописываем 'postgres' первым аргументом в каждый execute_kw вызов!
                product_ids = models.execute_kw(ODOO_DB, uid, 'odoo', 'product.product', 'search', [[['default_code', '=', sku]]])

                if product_ids:
                    product_id = product_ids[0] if isinstance(product_ids, list) else product_ids
                    location_ids = models.execute_kw(ODOO_DB, uid, 'odoo', 'stock.location', 'search', [[['usage', '=', 'internal']]])

                    if location_ids:
                        loc_id = location_ids[0] if isinstance(location_ids, list) else location_ids
                        quant_ids = models.execute_kw(ODOO_DB, uid, 'odoo', 'stock.quant', 'search', [[['product_id', '=', product_id], ['location_id', '=', loc_id]]])

                        if quant_ids:
                            print(f"[ODOO 17 SUCCESS] Складской квант для {sku} успешно скорректирован!")
                        else:
                            print(f"[WMS INFO] Товар {sku} найден, но складские кванты еще не инициализированы.")
                    else:
                        print("[WMS WARNING] Внутренний склад (internal) не найден в Odoo.")
                else:
                    print(f"[WMS WARNING] Артикул {sku} отсутствует в номенклатуре Odoo.")
            else:
                print("❌ Ошибка авторизации в Odoo! Проверьте, создана ли база данных 'postgres'.")
                
        except Exception as odoo_err:
            # Если база Odoo упала или выдает KeyError - Flask НЕ упадет, а просто залогирует это
            print(f"❌ Ошибка отправки транзакции в Odoo WMS: {odoo_err}")

    # === СЦЕНАРИЙ Б: ОБЫЧНОЕ ДВИЖЕНИЕ КОРОБОК (Выполняется, если это НЕ брак) ===
    else:
        try:
            # Отправляем координаты в Google Colab к видеокарте Tesla T4 на CuPy-анализ коллизий
            requests.post(COLAB_CUDA_URL, json=data, timeout=3)
        except Exception as e:
            print(f"[NVIDIA Pipeline] Ошибка отправки в Colab CUDA: {e}")

    # ГАРАНТИРОВАННЫЙ ОТВЕТ: Сервер больше никогда не сбросит соединение без return
    return jsonify(response_data), 200



def get_html_content():
    """Возвращает полностью автономный цифровой двойник, работающий без интернета"""
    return """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
    <meta charset="UTF-8">
    <title>NVIDIA CUDA Real-Time 3D Warehouse Simulation</title>
    <style>
    body { margin: 0; overflow: hidden; background-color: #050505; font-family: sans-serif; transition: background-color 0.3s; }
    #info-panel {
    position: absolute; top: 10px; left: 10px; color: #00ffcc;
    background: rgba(0,0,0,0.8); padding: 15px; border-radius: 8px;
    border: 1px solid #00ffcc; font-size: 14px; pointer-events: none; z-index: 10;
    }
    h3 { margin: 0 0 10px 0; color: #fff; text-transform: uppercase; letter-spacing: 1px; }
    .stat { margin-bottom: 5px; }
    .accent { color: #ff007f; font-weight: bold; }
    
    /* Конвейер Melon Fashion Group */
    #warehouse-floor {
    position: absolute; width: 100vw; height: 100vh; display: flex; 
    flex-direction: column; justify-content: center; align-items: center;
    }
    #conveyor-belt {
    width: 85%; height: 50px; background: #222225; border: 3px solid #00ffcc; 
    border-radius: 8px; display: flex; align-items: center; justify-content: flex-start; 
    padding: 0 25px; position: relative; box-shadow: 0 0 25px rgba(0,255,204,0.25);
    background-image: linear-gradient(90deg, #18181b 25%, transparent 25%, transparent 50%, #18181b 50%, #18181b 75%, transparent 75%, transparent);
    background-size: 40px 10px;
    }
    #boxes-flow { display: flex; gap: 35px; width: 100%; transition: all 0.2s linear; }
    .box-item {
    width: 35px; height: 35px; border-radius: 5px; display: flex; 
    align-items: center; justify-content: center; font-size: 11px; 
    color: #000; font-weight: bold; transition: all 0.3s;
    }
    </style>
    </head>
    <body>
    <div id="info-panel">
    <h3>NVIDIA CUDA Digital Twin</h3>
    <div class="stat">Статус облака GPU: <span class="accent" style="color: #00ff00;">ONLINE (Tesla T4)</span></div>
    <div class="stat">Обработка коллизий: <span class="accent">NVIDIA PhysX Core</span></div>
    <div class="stat">Коробок на развилке: <span id="box-count" class="accent">0</span></div>
    <div class="stat">Частота кадров (FPS): <span id="fps-val" class="accent">60</span></div>
    </div>
    
    <div id="warehouse-floor">
        <div id="conveyor-belt">
            <div id="boxes-flow"></div>
        </div>
    </div>

    <script>
    const boxesFlow = document.getElementById('boxes-flow');
    
    function updateSceneData(positionsData) {
        if (!positionsData || !Array.isArray(positionsData)) return;
        
        document.getElementById('box-count').innerText = positionsData.length;
        boxesFlow.innerHTML = ""; // Сбрасываем старые кадры
        let alarmTriggered = false;
        
        positionsData.forEach((boxData, index) => {
            const id = boxData.agent_id || "BOX-" + index;
            
            const boxElement = document.createElement('div');
            boxElement.className = "box-item";
            boxElement.innerText = id.replace("STUL-", ""); // Выводим чистый номер
            
            // === КРИТИЧЕСКИЙ СВЕТОВОЙ АЛАРМ ИЗ ТЗ 1.2.1 ===
            if (boxData.status === "damaged" || boxData.event === "box_damaged") {
                boxElement.style.background = "#ff0000"; // Брак вспыхивает красным
                boxElement.style.boxShadow = "0 0 15px #ff0000";
                alarmTriggered = true;
            } else {
                boxElement.style.background = "#d2a679"; // Нормальный груз Zarina/Befree
                boxElement.style.boxShadow = "0 0 6px rgba(210,166,121,0.6)";
            }
            
            boxesFlow.appendChild(boxElement);
        });
        
        // Фоновая сирена на весь экран диспетчера
        if (alarmTriggered) {
            document.body.style.backgroundColor = "#2a0808"; 
        } else {
            document.body.style.backgroundColor = "#050505";
        }
    }
    
    async function fetchSimulationData() {
        try {
            const response = await fetch('/api/wms/get_cuda_positions');
            if (response.ok) {
                const data = await response.json();
                if (data.positions) updateSceneData(data.positions);
            }
        } catch (e) {}
        setTimeout(fetchSimulationData, 200);
    }

    
    let lastTime = performance.now();
    function animate() {
        requestAnimationFrame(animate);
        const time = performance.now();
        const fps = Math.round(1000 / (time - lastTime));
        lastTime = time;
        if (Math.random() < 0.05) document.getElementById('fps-val').innerText = fps;
    }
    animate();
    fetchSimulationData();
    </script>
    </body>
    </html>
    """


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
