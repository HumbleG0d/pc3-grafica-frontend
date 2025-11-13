# app.py - Para Render.com
import os
from flask import Flask, request, jsonify, render_template_string, send_file
import base64
import json
from datetime import datetime
import glob
import zipfile
import io

app = Flask(__name__)

# Directorio persistente
UPLOAD_FOLDER = '/opt/render/project/src/drawings'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Subcarpetas por símbolo
SYMBOL_FOLDERS = {
    "corchea": "corchea",
    "semicorchea": "semicorchea",
    "plica_abajo": "plica_abajo",
    "plica_arriba": "plica_arriba",
    "clave_sol": "clave_sol"
}

for folder in SYMBOL_FOLDERS.values():
    path = os.path.join(UPLOAD_FOLDER, folder)
    if not os.path.exists(path):
        os.makedirs(path)

main_html = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Generador de Dataset - Dibujos</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 30px;
        }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 { color: #333; margin-bottom: 10px; }
        .stats { display: flex; justify-content: center; margin: 20px 0; }
        .stat-box {
            background: #f0f0f0;
            padding: 20px 40px;
            border-radius: 10px;
            text-align: center;
            max-width: 300px;
        }
        .stat-box .number { font-size: 48px; font-weight: bold; color: #667eea; }
        .stat-box .label { font-size: 16px; color: #666; margin-top: 5px; }
        .controls {
            display: flex;
            gap: 15px;
            margin: 20px 0;
            flex-wrap: wrap;
            align-items: center;
            justify-content: center;
        }
        .control-group { display: flex; flex-direction: column; gap: 5px; }
        .control-group label { font-size: 12px; color: #666; font-weight: bold; }
        .mode-toggle {
            display: flex;
            gap: 5px;
            background: #f0f0f0;
            padding: 5px;
            border-radius: 8px;
        }
        .mode-btn {
            padding: 10px 20px;
            border: none;
            background: transparent;
            cursor: pointer;
            border-radius: 5px;
            font-weight: bold;
            transition: all 0.3s;
        }
        .mode-btn.active { background: white; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .color-picker {
            width: 60px;
            height: 40px;
            border: 2px solid #ddd;
            border-radius: 8px;
            cursor: pointer;
        }
        .brush-size { width: 150px; }
        .canvas-container {
            display: flex;
            justify-content: center;
            margin: 20px 0;
            padding: 20px;
            background: #f9f9f9;
            border-radius: 10px;
        }
        #drawingCanvas {
            border: 3px solid #333;
            border-radius: 10px;
            cursor: crosshair;
            background: white;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        .button-group {
            display: flex;
            gap: 10px;
            justify-content: center;
            flex-wrap: wrap;
        }
        button {
            padding: 12px 30px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
        }
        .btn-clear { background: #ff6b6b; color: white; }
        .btn-clear:hover { background: #ff5252; transform: translateY(-2px); }
        .btn-save { background: #51cf66; color: white; }
        .btn-save:hover { background: #40c057; transform: translateY(-2px); }
        .btn-download { background: #667eea; color: white; }
        .btn-download:hover { background: #5568d3; transform: translateY(-2px); }
        .btn-clear-all { background: #ffa500; color: white; }
        .btn-clear-all:hover { background: #ff8c00; transform: translateY(-2px); }
        .notification {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 25px;
            background: #51cf66;
            color: white;
            border-radius: 8px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
            transform: translateX(400px);
            transition: transform 0.3s;
            z-index: 1000;
        }
        .notification.show { transform: translateX(0); }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎨 Generador de Dataset para IA</h1>
            <p>Dibuja libremente y guarda imágenes en el servidor</p>
        </div>
        
        <div class="stats">
            <div class="stat-box">
                <div class="number" id="totalCount">0</div>
                <div class="label">Dibujos Guardados en Servidor</div>
            </div>
        </div>
        
        <div class="controls">
            <div class="control-group">
                <label>Modo de Dibujo</label>
                <div class="mode-toggle">
                    <button class="mode-btn" id="btnBW">⚫ Blanco y Negro</button>
                    <button class="mode-btn active" id="btnColor">🎨 Color</button>
                </div>
            </div>
            
            <div class="control-group" id="colorControl">
                <label>Color del Pincel</label>
                <input type="color" class="color-picker" id="colorPicker" value="#000000">
            </div>
            
            <div class="control-group">
                <label>Grosor: <span id="brushSizeValue">11</span>px</label>
                <input type="range" class="brush-size" id="brushSize" min="1" max="50" value="11">
            </div>
        </div>
        
        <div class="canvas-container">
            <canvas id="drawingCanvas" width="280" height="280"></canvas>
        </div>
        
        <div class="button-group">
            <button class="btn-clear" onclick="clearCanvas()">🗑️ Borrar Canvas</button>
            <button class="btn-save" onclick="saveDrawing()">💾 Guardar en Servidor</button>
            <button class="btn-download" onclick="downloadDataset()">📦 Descargar Dataset (ZIP)</button>
            <button class="btn-clear-all" onclick="clearAllDrawings()">🚮 Limpiar Todo</button>
        </div>
    </div>
    
    <div class="notification" id="notification"></div>
    
    <script>
        const canvas = document.getElementById('drawingCanvas');
        const ctx = canvas.getContext('2d');
        let isDrawing = false;
        let lastX = 0;
        let lastY = 0;
        let currentMode = 'color';
        let currentColor = '#000000';
        
        // Initialize
        ctx.fillStyle = 'white';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        updateCount();
        
        // Drawing functions
        canvas.addEventListener('mousedown', startDrawing);
        canvas.addEventListener('mousemove', draw);
        canvas.addEventListener('mouseup', stopDrawing);
        canvas.addEventListener('mouseout', stopDrawing);
        
        canvas.addEventListener('touchstart', (e) => {
            e.preventDefault();
            const touch = e.touches[0];
            const rect = canvas.getBoundingClientRect();
            lastX = touch.clientX - rect.left;
            lastY = touch.clientY - rect.top;
            isDrawing = true;
        });
        
        canvas.addEventListener('touchmove', (e) => {
            e.preventDefault();
            if (!isDrawing) return;
            const touch = e.touches[0];
            const rect = canvas.getBoundingClientRect();
            const x = touch.clientX - rect.left;
            const y = touch.clientY - rect.top;
            drawLine(lastX, lastY, x, y);
            lastX = x;
            lastY = y;
        });
        
        canvas.addEventListener('touchend', (e) => {
            e.preventDefault();
            isDrawing = false;
        });
        
        function startDrawing(e) {
            isDrawing = true;
            const rect = canvas.getBoundingClientRect();
            lastX = e.clientX - rect.left;
            lastY = e.clientY - rect.top;
        }
        
        function draw(e) {
            if (!isDrawing) return;
            const rect = canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            drawLine(lastX, lastY, x, y);
            lastX = x;
            lastY = y;
        }
        
        function stopDrawing() { isDrawing = false; }
        
        function drawLine(x1, y1, x2, y2) {
            ctx.beginPath();
            ctx.moveTo(x1, y1);
            ctx.lineTo(x2, y2);
            ctx.strokeStyle = currentMode === 'bw' ? '#000000' : currentColor;
            ctx.lineWidth = document.getElementById('brushSize').value;
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';
            ctx.stroke();
        }
        
        function clearCanvas() {
            ctx.fillStyle = 'white';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
        }
        
        async function saveDrawing() {
            const imageData = canvas.toDataURL('image/png');
            
            const formData = new FormData();
            formData.append('myImage', imageData);
            formData.append('mode', currentMode);
            formData.append('color', currentColor);
            
            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showNotification('✓ Dibujo guardado en servidor');
                    clearCanvas();
                    updateCount();
                } else {
                    showNotification('⚠️ Error al guardar', 'error');
                }
            } catch (error) {
                showNotification('⚠️ Error de conexión', 'error');
            }
        }
        
        async function updateCount() {
            try {
                const response = await fetch('/count');
                const data = await response.json();
                document.getElementById('totalCount').textContent = data.count;
            } catch (error) {
                console.error('Error getting count:', error);
            }
        }
        
        function downloadDataset() {
            window.open('/download_dataset', '_blank');
        }
        
        async function clearAllDrawings() {
            if (!confirm('¿Estás seguro de eliminar TODOS los dibujos del servidor?')) {
                return;
            }
            
            try {
                const response = await fetch('/clear_all', { method: 'POST' });
                const data = await response.json();
                
                if (data.success) {
                    showNotification('🗑️ Todos los dibujos eliminados');
                    updateCount();
                }
            } catch (error) {
                showNotification('⚠️ Error al limpiar', 'error');
            }
        }
        
        function showNotification(message, type = 'success') {
            const notification = document.getElementById('notification');
            notification.textContent = message;
            notification.style.background = type === 'success' ? '#51cf66' : '#ff6b6b';
            notification.classList.add('show');
            
            setTimeout(() => {
                notification.classList.remove('show');
            }, 3000);
        }
        
        // Mode toggle
        document.getElementById('btnBW').addEventListener('click', () => {
            currentMode = 'bw';
            document.getElementById('btnBW').classList.add('active');
            document.getElementById('btnColor').classList.remove('active');
            document.getElementById('colorControl').style.opacity = '0.5';
            document.getElementById('colorControl').style.pointerEvents = 'none';
        });
        
        document.getElementById('btnColor').addEventListener('click', () => {
            currentMode = 'color';
            document.getElementById('btnColor').classList.add('active');
            document.getElementById('btnBW').classList.remove('active');
            document.getElementById('colorControl').style.opacity = '1';
            document.getElementById('colorControl').style.pointerEvents = 'auto';
        });
        
        document.getElementById('colorPicker').addEventListener('input', (e) => {
            currentColor = e.target.value;
        });
        
        document.getElementById('brushSize').addEventListener('input', (e) => {
            document.getElementById('brushSizeValue').textContent = e.target.value;
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(main_html)

@app.route('/upload', methods=['POST'])
def upload():
    try:
        img_data = request.form.get('myImage').replace("data:image/png;base64,", "")
        mode = request.form.get('mode', 'bw')
        color = request.form.get('color', '#000000')
        symbol = request.form.get('symbol', 'unknown')  # ← NUEVO
        
        # Validar símbolo
        folder_name = SYMBOL_FOLDERS.get(symbol, "otros")
        symbol_folder = os.path.join(UPLOAD_FOLDER, folder_name)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        filename = f'{symbol}_{timestamp}.png'
        filepath = os.path.join(symbol_folder, filename)
        
        with open(filepath, 'wb') as fh:
            fh.write(base64.b64decode(img_data))
        
        metadata = {
            'filename': filename,
            'symbol': symbol,
            'mode': mode,
            'color': color,
            'timestamp': timestamp
        }
        
        meta_file = os.path.join(symbol_folder, f'meta_{timestamp}.json')
        with open(meta_file, 'w') as f:
            json.dump(metadata, f)
        
        print(f"Image saved: {symbol}/{filename}")
        return jsonify({'success': True})
    
    except Exception as err:
        print(f"Error: {err}")
        return jsonify({'success': False, 'error': str(err)}), 500

@app.route('/count', methods=['GET'])
def get_count():
    try:
        total = 0
        for folder in SYMBOL_FOLDERS.values():
            path = os.path.join(UPLOAD_FOLDER, folder)
            total += len(glob.glob(os.path.join(path, '*.png')))
        return jsonify({'count': total})
    except:
        return jsonify({'count': 0})

@app.route('/download_dataset', methods=['GET'])
def download_dataset():
    try:
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for folder_name, folder_path in SYMBOL_FOLDERS.items():
                full_path = os.path.join(UPLOAD_FOLDER, folder_path)
                if not os.path.exists(full_path):
                    continue
                for file_path in glob.glob(os.path.join(full_path, '*.png')):
                    arcname = f"{folder_path}/{os.path.basename(file_path)}"
                    zf.write(file_path, arcname)
                # Opcional: incluir metadata
                for meta_path in glob.glob(os.path.join(full_path, 'meta_*.json')):
                    arcname = f"{folder_path}/metadata/{os.path.basename(meta_path)}"
                    os.makedirs(os.path.dirname(arcname), exist_ok=True)
                    zf.write(meta_path, arcname)
        
        memory_file.seek(0)
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'musical_dataset_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
        )
    except Exception as err:
        return f"Error: {str(err)}", 500

@app.route('/clear_all', methods=['POST'])
def clear_all():
    try:
        for folder in SYMBOL_FOLDERS.values():
            path = os.path.join(UPLOAD_FOLDER, folder)
            if os.path.exists(path):
                for f in os.listdir(path):
                    os.remove(os.path.join(path, f))
                # Borrar metadata también
                meta_dir = os.path.join(path, 'metadata')
                if os.path.exists(meta_dir):
                    for f in os.listdir(meta_dir):
                        os.remove(os.path.join(meta_dir, f))
        return jsonify({'success': True})
    except Exception as err:
        return jsonify({'success': False, 'error': str(err)}), 500

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)