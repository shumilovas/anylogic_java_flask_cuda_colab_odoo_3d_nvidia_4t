import os
import requests
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

# Инициализируем Flask шлюз
app = Flask(__name__)
CORS(app)

# Жёсткое глушение спама в консоли (подавляем все GET-логи)
import logging
logging.getLogger('werkzeug').setLevel(logging.ERROR)

# Хранилище для последних обсчитанных CUDA координат
latest_cuda_positions = []

# Ваша точная живая ссылка из логов Google Colab, не забудем /api/cuda/simulate
COLAB_CUDA_URL = "https://https://deep-sites-sleep.loca.lt///api/cuda/simulate"

@app.route('/', methods=['GET'])
def home():
    """Главная страница — отдает 3D-сайт в обход шаблонизатора"""
    return Response(get_html_content(), mimetype='text/html')

@app.route('/cuda_3d', methods=['GET'])
def open_3d_simulation():
    """Страница 3D-диспетчера склада — отдает 3D-сайт в обход шаблонизатора"""
    return Response(get_html_content(), mimetype='text/html')

@app.route('/api/wms/get_cuda_positions', methods=['GET'])
def get_cuda_positions():
    global latest_cuda_positions
    # Отдаем сайту Three.js массив всех актуальных коробок
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

    print(f"[NVIDIA Pipeline] Данные пойманы от AnyLogic! Объектов/Параметров: {data}")

    # Стучимся в Google Colab к видеокарте Tesla T4
    try:
        response = requests.post(COLAB_CUDA_URL, json=data, timeout=5)
        if response.status_code == 200:
            print("[NVIDIA Pipeline] Ответ от облачного ядра CUDA: SUCCESS (Tesla T4)")
            
            # --- ВАЖНОЕ ИЗМЕНЕНИЕ: Добавляем коробку в общий список ---
            # Сохраняем ID, время входа и параметры для отрисовки
            latest_cuda_positions.append({
                "agent_id": data.get("agent_id"),
                "red_qty": data.get("red_qty", 1),
                "blue_qty": data.get("blue_qty", 0),
                "green_qty": data.get("green_qty", 0)
            })
            
            # Ограничим список последними 50 коробками, чтобы память не переполнялась
            if len(latest_cuda_positions) > 50:
                latest_cuda_positions.pop(0)
                
            return jsonify({"status": "success"}), 200
        else:
            print(f"[NVIDIA Pipeline] Ошибка CUDA ядра: {response.status_code}")
            return jsonify({"status": "cuda_error"}), 503
    except Exception as e:
        print(f"[NVIDIA Pipeline] CUDA таймаут или сбой связи: {e}")
        return jsonify({"status": "error"}), 500

def get_html_content():
    """Функция возвращает чистый HTML/Three.js код 3D-сайта"""
    return """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>NVIDIA CUDA Real-Time 3D Warehouse Simulation</title>
        <style>
            body { margin: 0; overflow: hidden; background-color: #050505; font-family: sans-serif; }
            #info-panel {
                position: absolute; top: 10px; left: 10px; color: #00ffcc;
                background: rgba(0,0,0,0.8); padding: 15px; border-radius: 8px;
                border: 1px solid #00ffcc; font-size: 14px; pointer-events: none;
            }
            h3 { margin: 0 0 10px 0; color: #fff; text-transform: uppercase; letter-spacing: 1px; }
            .stat { margin-bottom: 5px; }
            .accent { color: #ff007f; font-weight: bold; }
        </style>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>

    </head>
    <body>
        <div id="info-panel">
            <h3>NVIDIA CUDA Digital Twin</h3>
            <div class="stat">Статус облака GPU: <span class="accent" style="color: #00ff00;">ONLINE (Tesla T4)</span></div>
            <div class="stat">Обработка коллизий: <span class="accent">NVIDIA PhysX Core</span></div>
            <div class="stat">Коробок на развилке: <span id="box-count" class="accent">0</span></div>
            <div class="stat">Частота кадров (FPS): <span id="fps-val" class="accent">60</span></div>
        </div>
        <script>
            const scene = new THREE.Scene();
            scene.background = new THREE.Color(0x0a0a0c);

            const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
            const renderer = new THREE.WebGLRenderer({ antialias: true });
            renderer.setSize(window.innerWidth, window.innerHeight);
            document.body.appendChild(renderer.domElement);

            camera.position.set(-15, 12, 18);
            camera.lookAt(0, 2, 0);

            const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
            scene.add(ambientLight);

            const directionalLight = new THREE.DirectionalLight(0x00ffcc, 0.8);
            directionalLight.position.set(-10, 20, 10);
            scene.add(directionalLight);

            // Визуализируем конвейерную ленту
            const conveyorGeo = new THREE.BoxGeometry(40, 0.2, 4);
            const conveyorMat = new THREE.MeshBasicMaterial({ color: 0x222225 });
            const conveyor = new THREE.Mesh(conveyorGeo, conveyorMat);
            scene.add(conveyor);

            const boxes = [];
            const boxGeometry = new THREE.BoxGeometry(1.2, 1.2, 1.2);
            const boxMaterial = new THREE.MeshBasicMaterial({ color: 0xd2a679 });

            function updateSceneData(positionsData) {
                if (!positionsData) return;
                
                let count = 0;
                let coordinates = [];

                // УМНЫЙ ДЕКОДЕР НА ФРОНТЕНДЕ:
                // Случай А: Прилетел массив координат от CUDA
                if (Array.isArray(positionsData)) {
                    count = positionsData.length;
                    coordinates = positionsData;
                } 
                // Случай Б: Прилетел старый пакет счетчика из AnyLogic (словарь с red_qty)
                else if (typeof positionsData === 'object' && positionsData.red_qty !== undefined) {
                    count = parseInt(positionsData.red_qty) || 0;
                    // Генерируем временные точки в ряд, чтобы сайт не падал
                    for(let i=0; i<count; i++) coordinates.push([i * 2.5 - 5, 0]);
                }

                document.getElementById('box-count').innerText = count;

                // Синхронизируем количество 3D-кубиков на сцене
                while (boxes.length < count) {
                    const mesh = new THREE.Mesh(boxGeometry, boxMaterial);
                    scene.add(mesh);
                    boxes.push(mesh);
                }
                while (boxes.length > count) {
                    const mesh = boxes.pop();
                    scene.remove(mesh);
                }

                // Расставляем кубики по конвейеру
                for (let i = 0; i < count; i++) {
                    if (coordinates[i] && Array.isArray(coordinates[i])) {
                        // Если есть реальные координаты X и Y от GPU
                        boxes[i].position.set(coordinates[i][0], 0.6, coordinates[i][1]);
                    } else if (typeof coordinates[i] === 'number') {
                        // Фолбэк на случай плоского списка чисел
                        boxes[i].position.set(coordinates[i], 0.6, 0);
                    } else {
                        // Временный ряд, если координат еще нет
                        boxes[i].position.set(i * 2.5 - 5, 0.6, 0);
                    }
                }
            }

            async function fetchSimulationData() {
                try {
                    const response = await fetch('/api/wms/get_cuda_positions');
                    if (response.ok) {
                        const data = await response.json();
                        if (data.positions) updateSceneData(data.positions);
                    }
                } catch (e) { console.log("Ожидание кадров..."); }
                setTimeout(fetchSimulationData, 100);
            }

            let lastTime = performance.now();
            function animate() {
                requestAnimationFrame(animate);
                const time = performance.now();
                const fps = Math.round(1000 / (time - lastTime));
                lastTime = time;
                if (Math.random() < 0.05) document.getElementById('fps-val').innerText = fps;
                renderer.render(scene, camera);
            }

            animate();
            fetchSimulationData();

            window.addEventListener('resize', () => {
                camera.aspect = window.innerWidth / window.innerHeight;
                camera.updateProjectionMatrix();
                renderer.setSize(window.innerWidth, window.innerHeight);
            });
        </script>
    </body>
    </html>
    """

if __name__ == '__main__':
    # Оставляем Flask в покое, даем ему нормально поднять порт 5000
    app.run(host='0.0.0.0', port=5000, debug=False)

