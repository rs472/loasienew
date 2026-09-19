from flask import Flask, render_template, request, jsonify ,send_from_directory, abort, send_file
import smtplib
import firebase_admin
from functools import wraps
from firebase_admin import credentials, auth, firestore
from email.mime.text import MIMEText
import os

import uuid
from datetime import datetime

from flask import Flask, render_template, jsonify, request
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash


from flask import Flask, request, jsonify, session
from flask_mail import Mail, Message  # Exemplo com Flask-Mail
import random
from datetime import datetime, timedelta

app = Flask(__name__)
auth = HTTPBasicAuth()



USERS = {
    "Jesus": generate_password_hash("istheLord")  
}

@auth.verify_password
def verify_password(username, password):
    if username in USERS and check_password_hash(USERS.get(username), password):
        return username
    return None


app = Flask(__name__)

# Initialize Firebase Admin SDK
# (Replace with your service account JSON file path)
cred = credentials.Certificate("firebase_credentials.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Directory where your PDF/ZIP files are actually stored
DOWNLOADS_DIR = os.path.join(app.root_path, 'static', '_media')


#path firebase json



# 2. Authentication Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Read the Authorization header: "Bearer <ID_TOKEN>"
        auth_header = request.headers.get("Authorization")
        
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Unauthorized. Missing token."}), 401
        
        id_token = auth_header.split("Bearer ")[1]
        
        try:
            # Verify the token with Firebase Admin
            decoded_token = auth.verify_id_token(id_token)
            # Attach user info to Flask's request context
            request.user = decoded_token 
        except Exception as e:
            return jsonify({"error": "Unauthorized. Invalid or expired token."}), 401
            
        return f(*args, **kwargs)
    return decorated_function

# 3. Protected Download Route
# Make sure Firebase Admin SDK is initialized in Flask
if not firebase_admin._apps:
    cred = credentials.Certificate("path/to/your/serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

@app.route('/api/download/<path:filename>', methods=['GET'])
def download_file(filename):
    # 1. VERIFICA O TOKEN DO FIREBASE
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Nenhum token fornecido"}), 401

    id_token = auth_header.split('Bearer ')[1]

    try:
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        print(f"DEBUG: Usuário autenticado com sucesso -> {uid}")
    except Exception as e:
        print(f"DEBUG: Falha na validação do token -> {e}")
        return jsonify({"error": "Token inválido ou expirado"}), 401

    # 2. VERIFICA SE O ARQUIVO EXISTE EM static/_media
    file_path = os.path.join(DOWNLOADS_DIR, filename)
    print(f"DEBUG: Procurando arquivo em -> {file_path}")

    if not os.path.exists(file_path):
        print(f"DEBUG: Arquivo NÃO encontrado em -> {file_path}")
        return jsonify({"error": f"Arquivo '{filename}' não foi encontrado no servidor."}), 404

    # 3. ENVIA O ARQUIVO DE static/_media
    return send_from_directory(DOWNLOADS_DIR, filename, as_attachment=True)
    
### -- ALL OF THE HTMLS---
@app.route("/")
@auth.login_required
def index():
    return render_template("index.html")

@app.route("/brainbot", endpoint="brainbot")

def software():
    return render_template("brainbot.html")

@app.route("/logiheart", endpoint="logiheart")
def design():
    return render_template("logiheart.html")

@app.route('/painel')
def painel():
    # Your dashboard view logic here
    return render_template('painel.html')

####---OTA UPDATE

# ROUTE TO CHECK THE UPDATE
UPDATE_FOLDER = "updates_vault" 

@app.route('/updates/version.txt')
def get_version():
    try:
        with open(os.path.join(UPDATE_FOLDER, "version.txt"),'r')as f:
            content = f.read().strip()
        return content, 200 ,{"Content-type":"text/plain"}
    except Exception as e:
        return "2.5", 404
        
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPDATE_FOLDER = os.path.join(BASE_DIR, "updates_vault")

@app.route('/updates/brainbot_latest.exe')
def get_script():
    #MAKE UP THE PATH 
    target_file = os.path.join(UPDATE_FOLDER, "brainbot_latest.exe")
    
    #print(f"DEBUG: trying to give the file: {target_file}")
    
    if os.path.exists(target_file):
        return send_file(
            target_file,
            mimetype='application/octet-stream', 
            download_name='brainbot_latest.exe'
        )
    else:
        #print(f"DEBUG: could not find the file")
        abort(404)

#### --- FUNCIOS VERIFY IF USER IS LOGGED

@app.route('/_media/<nome_do_arquivo>')
@login_required # O Flask barra aqui se não estiver logado!
def baixar_arquivo(nome_do_arquivo):
    
    # Cenário A: Se for o arquivo do Google Drive
    if nome_do_arquivo == "Stock_Heart_System_v5.1.zip":
        id_do_drive = "1ds6a_wuQUzbxDr7d7dbWDRZx_iJ3lq6l&export=download&authuser=0"
        # ... (aquela lógica do requests.get que fizemos antes)
        
    # Cenário B: Se for um arquivo local (que você colocou numa pasta privada)
    else:
        diretorio_seguro = "/caminho/da/sua/pasta_privada"
        try:
            return send_from_directory(diretorio_seguro, nome_do_arquivo, as_attachment=True)
        except FileNotFoundError:
            return jsonify({"erro": "Arquivo não encontrado."}), 404

##### vrtify license
@app.route('/')
def home():
    return render_template('painel.html')


@app.route('/api/verify-key', methods=['POST'])
def verify_key():
    data = request.get_json(silent=True) or {}
    license_key = data.get('license_key')

    if license_key:
        license_key = str(license_key).strip()

    if not license_key:
        return jsonify({"status": "ERROR", "message": "Nenhuma chave fornecida."}), 400

    # Query Firestore for the key document
    key_ref = db.collection('licenses').document(license_key)
    doc = key_ref.get()

    if not doc.exists:
        return jsonify({"status": "INVALID", "message": "Chave de licença inválida."}), 404

    license_info = doc.to_dict()
    today = datetime.now().date()

    # --- Case 1: Permanent Key ---
    if license_info.get('key_type') == 'PERMANENT':
        if not license_info.get('is_claimed'):
            key_ref.update({"is_claimed": True, "claimed_at": today.strftime('%Y-%m-%d')})
        return jsonify({"status": "ACTIVE", "type": "PERMANENT", "message": "Licença Vitalícia Ativa!"})

    # --- Case 2: Trial Key ---
    if license_info.get('key_type') == 'TRIAL':
        # First time using this key -> Claim it and start clock today
        if not license_info.get('is_claimed'):
            key_ref.update({
                "is_claimed": True,
                "claimed_at": today.strftime('%Y-%m-%d')
            })
            return jsonify({
                "status": "ACTIVE", 
                "type": "TRIAL", 
                "days_left": license_info.get('trial_days', 7)
            })

        # Already claimed -> Calculate days passed since claimed_at
        claimed_date_str = license_info.get('claimed_at')
        claimed_date = datetime.strptime(claimed_date_str, '%Y-%m-%d').date()
        days_passed = (today - claimed_date).days
        trial_days = license_info.get('trial_days', 7)
        days_left = trial_days - days_passed

        if days_left <= 0:
            key_ref.update({"status": "EXPIRED"})
            return jsonify({
                "status": "EXPIRED", 
                "message": "Seu período de teste expirou. Adquira a chave permanente!"
            })
        
        return jsonify({
            "status": "ACTIVE", 
            "type": "TRIAL", 
            "days_left": days_left
        })

@app.route('/api/register-license', defaults={'product_id': None}, methods=['POST'])
@app.route('/api/register-license/<product_id>', methods=['POST'])
def register_license(product_id):
    data = request.get_json(silent=True) or {}

    # --- LINHAS DE DIAGNÓSTICO (Olhe o terminal ao clicar no botão) ---
    print("==========================================")
    print("URL product_id:", product_id)
    print("BODY JSON received:", data)
    print("==========================================")

    # Resto da lógica...
    final_product = product_id or data.get('product') or data.get('product_id')
    email = (data.get('email') or data.get('user_email') or '').strip().lower()
    company = data.get('company', '').strip()

    if not email or '@' not in email:
        return jsonify({"success": False, "message": "E-mail corporativo inválido."}), 400

    # 1. Filtra se JÁ existe uma licença deste e-mail para ESTE produto específico
    existing_keys = db.collection('licenses') \
                      .where('owner_email', '==', email) \
                      .where('product', '==', final_product) \
                      .get()

    if len(existing_keys) > 0:
        return jsonify({
            "success": False, 
            "message": f"Este e-mail já possui uma licença cadastrada para o produto {final_product.upper()}."
        }), 400

    # Define o prefixo correto na chave (SH para StockHeart, BB para BrainBot)
    prefix = "SH" if "stock" in final_product else "BB"
    raw_uuid = str(uuid.uuid4()).upper().replace('-', '')
    new_key = f"{prefix}-{raw_uuid[:4]}-{raw_uuid[4:8]}-{raw_uuid[8:12]}"

    # Salva no Firestore gravando o produto correto
    db.collection('licenses').document(new_key).set({
        "product": final_product, # <-- Gravará 'stockheart' ou 'brainbot' corretamente
        "key_type": "TRIAL",
        "owner_email": email,
        "company_name": company,
        "is_claimed": False,
        "trial_days": 7,
        "status": "ACTIVE",
        "created_at": datetime.now().strftime('%Y-%m-%d')
    })

    return jsonify({"success": True, "license_key": new_key, "email": email, "product": final_product})

##### PAINEL ACTIVE

@app.route('/api/user-status', methods=['POST'])
def get_user_status():
    data = request.get_json(silent=True) or {}
    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({"success": False, "message": "E-mail não fornecido."}), 400
    
    allowed_products = ['brainbot', 'stockheart']
    
    # Removemos o .limit(1) para buscar todas as licenças do e-mail nos produtos permitidos
    docs = db.collection('licenses') \
             .where('owner_email', '==', email) \
             .where('product', 'in', allowed_products) \
             .get()

    if not docs:
        return jsonify({
            "success": True,
            "has_license": False,
            "status_text": "Nenhuma licença ativa"
        })

    today = datetime.now().date()
    products_info = []
    has_any_active_license = False

    for doc in docs:
        license_info = doc.to_dict()
        product_id = license_info.get('product', '').lower()
        product_name = product_id.capitalize()
        key_type = license_info.get('key_type', 'TRIAL')
        company_name = license_info.get('company_name', 'Não informada')

        if key_type == 'PERMANENT':
            has_any_active_license = True
            products_info.append({
                "product": product_id,
                "company": company_name,
                "status_text": f"Plano Vitalício Ativo em: {product_name}"
            })
        else:
            trial_days = license_info.get('trial_days', 7)
            claimed_at_str = license_info.get('claimed_at')

            if claimed_at_str:
                claimed_date = datetime.strptime(claimed_at_str, '%Y-%m-%d').date()
                days_passed = (today - claimed_date).days
                days_left = max(0, trial_days - days_passed)
            else:
                days_left = trial_days

            is_active = days_left > 0
            if is_active:
                has_any_active_license = True

            plan_name = "Teste" if key_type == 'TRIAL' else "Plano Anual"
            
            if is_active:
                status_text = f"Situação {product_name}: {plan_name} ({days_left} dias restantes)"
            else:
                status_text = f"Situação {product_name}: {plan_name} Expirado"

            products_info.append({
                "product": product_id,
                "company": company_name,
                "status_text": status_text
            })

    # Cria uma frase resumida concatenando os status de todos os produtos encontrados
    summary_text = " | ".join([p["status_text"] for p in products_info])

    return jsonify({
        "success": True,
        "has_license": has_any_active_license,
        "products": products_info, # Lista detalhada de cada licença/produto
        "status_text": summary_text # Ex: "Plano Vitalício Ativo em: Brainbot | Plano Vitalício Ativo em: Stockheart"
    })
    
##### message funcion

@app.route("/enviar", methods=["POST"])
def enviar():
    nome = request.form["nome"]
    email = request.form["email"]
    telefone = request.form["telefone"]
    mensagem = request.form["mensagem"]

    corpo = f"""New contat from site LOA IT

Nome: {nome}
E-mail: {email}
Telefone: {telefone}
Mensagem: {mensagem}
"""

    msg = MIMEText(corpo)
    msg["Subject"] = "📩 New contact from site LOA IT"
    msg["From"] = "brainstormcompany9@gmail.com"
    msg["To"] = "brainstormcompany9@gmail.com"

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login("brainstormcompany9@gmail.com", "ytzz gtbv iusc ytbo")
            server.send_message(msg)
        return render_template("mensagens.html")
    except Exception as e:
        return f"<h2>Erro ao enviar: {e}</h2>"

########## verification 2 ways ###############


#Função de validação de e-mail corporativo (Python/Flask)

# Lista de provedores de e-mail pessoais/gratuitos mais comuns
DISALLOWED_DOMAINS = {
   
}

def is_corporate_email(email: str) -> bool:
    """Valida se o e-mail não pertence a um provedor gratuito ou descartável."""
    if '@' not in email:
        return False
    
    domain = email.split('@')[-1].lower().strip()
    return domain not in DISALLOWED_DOMAINS

#Aplicando no seu Endpoint de Cadastro/Autenticação:
@app.route('/api/register', methods=['POST'])
def register_user():
    data = request.get_json(silent=True) or {}
    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({"success": False, "message": "E-mail não fornecido."}), 400

    # Valida se é um e-mail corporativo
    if not is_corporate_email(email):
        return jsonify({
            "success": False, 
            "message": "Por favor, utilize um e-mail corporativo. Provedores gratuitos (Gmail, Yahoo, Hotmail, etc.) não são permitidos."
        }), 400

#implementação no Firestore (E-mail ou SMS):

import random
from datetime import datetime, timedelta, timezone

def generate_otp_code() -> str:
    """Gera um código de 6 dígitos."""
    return str(random.randint(100000, 999999))


import resend
from dotenv import load_dotenv
import os

# Carrega o arquivo .env apenas localmente (se ele existir)
load_dotenv()

# No Render, ele lerá a variável configurada no painel da plataforma
resend.api_key = os.getenv("RESEND_API_KEY")

 # Obtenha gratuitamente em resend.com

@app.route('/api/send-2fa', methods=['POST'])
def send_2fa():
    data = request.get_json(silent=True) or {}
    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({"success": False, "message": "E-mail não fornecido."}), 400

    code = str(random.randint(100000, 999999))
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

    # Salva no Firestore
    db.collection('2fa_codes').document(email).set({
        'code': code,
        'expires_at': expires_at,
        'used': False
    })

    # Envio via API HTTP
    try:
        resend.Emails.send({
            "from": "Loa IT <onboarding@resend.dev>", 
            "to": [email],
            "subject": "Seu Código de Verificação",
            "html": f"<p>Seu código é: <strong>{code}</strong></p>"
        })
        return jsonify({"success": True, "message": "Código enviado por e-mail!"})
    except Exception as e:
        # Exibe o erro exato no terminal do Python
        print(f"Erro ao enviar 2FA: {e}") 
        return jsonify({"success": False, "message": str(e)}), 500

# 2. ETAPA: Valida o código E CRIA a conta / Login
@app.route('/api/verify-2fa', methods=['POST'])
def verify_2fa():
    data = request.get_json(silent=True) or {}
    email = data.get('email', '').strip().lower()
    code_input = data.get('code', '').strip()
    
    # Dados do cadastro vindos do front-end
    user_name = data.get('userName')
    company = data.get('userCompany')
    password = data.get('password')

    doc_ref = db.collection('2fa_codes').document(email)
    doc = doc_ref.get()

    if not doc.exists:
        return jsonify({"success": False, "message": "Nenhum código encontrado."}), 400

    auth_data = doc.to_dict()

    if auth_data.get('used') or auth_data.get('code') != code_input:
        return jsonify({"success": False, "message": "Código incorreto ou já utilizado."}), 400

    if datetime.utcnow() > auth_data.get('expires_at').replace(tzinfo=None):
        return jsonify({"success": False, "message": "Código expirado."}), 400

    # Marcar código como usado
    doc_ref.update({'used': True})

    # === SOMENTE AGORA REGISTRA O USUÁRIO NO BANCO DE DADOS ===
    # db.collection('users').add({ 'name': user_name, 'email': email, ... })
    
    # === SOMENTE AGORA DEFINE A SESSÃO DE LOGIN ===
    # session['user_email'] = email

    return jsonify({"success": True, "message": "Conta criada e verificada com sucesso!"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)