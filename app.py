from flask import Flask, render_template, request, jsonify
import subprocess
import os
import glob

app = Flask(__name__)

# Configuração de Diretórios
TESTS_DIR = 'tests'
OUTPUT_DIR = 'output'
TEMP_DIR = 'temp_code'

os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/tests', methods=['GET'])
def get_tests():
    tests = [os.path.basename(f) for f in glob.glob(os.path.join(TESTS_DIR, '*.minipar'))]
    return jsonify({"tests": tests})

@app.route('/api/get_test', methods=['POST'])
def get_test():
    filename = request.json.get('filename')
    filepath = os.path.join(TESTS_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return jsonify({"code": f.read()})
    return jsonify({"error": "Arquivo não encontrado"}), 404

@app.route('/api/compile', methods=['POST'])
def compile_code():
    data = request.json
    code = data.get('code')
    filename = data.get('filename', 'ide_temp.minipar')
    
    # Salva o código recebido da IDE em um arquivo temporário
    file_path = os.path.join(TEMP_DIR, filename)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(code)
        
    base_name = filename.replace('.minipar', '')
    
    try:
        # Executa o seu compilador como subprocesso
        process = subprocess.run(
            ['python', 'main.py', file_path], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        
        cpp_file = os.path.join(OUTPUT_DIR, f"{base_name}.cpp")
        tac_file = os.path.join(OUTPUT_DIR, f"{base_name}.tac")
        
        cpp_code = ""
        tac_code = ""
        
        if os.path.exists(cpp_file):
            with open(cpp_file, 'r', encoding='utf-8') as f:
                cpp_code = f.read()
                
        if os.path.exists(tac_file):
             with open(tac_file, 'r', encoding='utf-8') as f:
                tac_code = f.read()
                
        return jsonify({
            "stdout": process.stdout,
            "stderr": process.stderr,
            "cpp": cpp_code,
            "tac": tac_code,
            "success": process.returncode == 0
        })
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Tempo limite de execução excedido.", "success": False}), 500
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)