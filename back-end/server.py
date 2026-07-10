import hashlib
import logging
import os
import re
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps
from urllib.parse import quote

import requests as http_requests
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# ============================================
# Logging
# ============================================
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("thaycake")

# ============================================
# Supabase Config (variáveis de ambiente com fallback)
# ============================================
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://pqdodnnoaulfuleptzij.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBxZG9kbm5vYXVsZnVsZXB0emlqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODM2MzY2NjMsImV4cCI6MjA5OTIxMjY2M30.Zu3CfUNTUP93lFoU5X_foxB8GCZB4RKTsh9pVooReqY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", SUPABASE_KEY)
SUPABASE_STORAGE_URL = f"{SUPABASE_URL}/storage/v1"
SUPABASE_REST_URL = f"{SUPABASE_URL}/rest/v1"

SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

SUPABASE_SERVICE_HEADERS = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# ============================================
# Rate limiting (simple in-memory)
# ============================================
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 10     # max requests per window per IP
_rate_store = {}

def check_rate_limit(ip):
    now = time.time()
    entry = _rate_store.get(ip)
    if not entry or now - entry["reset"] > RATE_LIMIT_WINDOW:
        _rate_store[ip] = {"count": 1, "reset": now + RATE_LIMIT_WINDOW}
        return False
    entry["count"] += 1
    return entry["count"] > RATE_LIMIT_MAX


LOGIN_RATE_LIMIT_WINDOW = 300  # 5 min
LOGIN_RATE_LIMIT_MAX = 5
_login_rate_store = {}

def check_login_rate_limit(ip):
    now = time.time()
    entry = _login_rate_store.get(ip)
    if not entry or now - entry["reset"] > LOGIN_RATE_LIMIT_WINDOW:
        _login_rate_store[ip] = {"count": 1, "reset": now + LOGIN_RATE_LIMIT_WINDOW}
        return False
    entry["count"] += 1
    return entry["count"] > LOGIN_RATE_LIMIT_MAX

# ============================================
# Flask App
# ============================================
app = Flask(__name__, static_folder='../front-end', static_url_path='')
app.secret_key = os.getenv("FLASK_SECRET_KEY", "thaycake-admin-secret-key-change-in-production")
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
CORS(app, origins=["https://thaycake-2.0.vercel.app", "http://localhost:5000", "http://localhost:3000"])

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "thaycake-admin-2026")
VALID_CATEGORIES = {"tradicional", "frutas", "premium", "especial"}

# HTML tag removal for user-submitted fields
def strip_html(text):
    if not isinstance(text, str):
        return ""
    return re.sub(r'<[^>]*>', '', text).strip()


def sanitize_product_input(data):
    return {
        "name": strip_html(data.get('name', ''))[:60],
        "description": strip_html(data.get('description', ''))[:200],
        "price": parse_price(data.get('price', 0)),
        "emoji": data.get('emoji', '🧁')[:5],
        "color1": data.get('color1', '#BD6B62')[:7],
        "color2": data.get('color2', '#D4A69E')[:7],
        "category": data.get('category', 'tradicional'),
        "image": data.get('image', '').strip()[:500],
        "active": True,
        "sort_order": 0
    }


# ============================================
# Supabase Helpers
# ============================================
def sb_get(table, params=None, select="*"):
    url = f"{SUPABASE_REST_URL}/{table}?select={select}"
    if params:
        for k, v in params.items():
            url += f"&{k}={quote(str(v), safe='')}"
    res = http_requests.get(url, headers=SUPABASE_HEADERS, timeout=15)
    if not res.ok:
        log.error("Supabase GET %s -> %s: %s", table, res.status_code, res.text)
        raise Exception("Erro ao acessar dados")
    return res.json()


def sb_insert(table, data):
    url = f"{SUPABASE_REST_URL}/{table}"
    res = http_requests.post(url, headers=SUPABASE_HEADERS, json=data, timeout=15)
    if not res.ok:
        log.error("Supabase INSERT %s -> %s: %s", table, res.status_code, res.text)
        raise Exception("Erro ao salvar dados")
    return res.json()


def sb_update(table, data, filters):
    url = f"{SUPABASE_REST_URL}/{table}"
    for k, v in filters.items():
        url += f"&{k}={quote(str(v), safe='')}" if "?" in url else f"?{k}={quote(str(v), safe='')}"
    res = http_requests.patch(url, headers=SUPABASE_HEADERS, json=data, timeout=15)
    if not res.ok:
        log.error("Supabase UPDATE %s -> %s: %s", table, res.status_code, res.text)
        raise Exception("Erro ao atualizar dados")
    return res.json()


def sb_delete(table, filters):
    url = f"{SUPABASE_REST_URL}/{table}"
    for k, v in filters.items():
        url += f"&{k}={quote(str(v), safe='')}" if "?" in url else f"?{k}={quote(str(v), safe='')}"
    headers = {**SUPABASE_HEADERS, "Prefer": "return=minimal"}
    res = http_requests.delete(url, headers=headers, timeout=15)
    if not res.ok:
        log.error("Supabase DELETE %s -> %s: %s", table, res.status_code, res.text)
        raise Exception("Erro ao excluir dados")
    return True


def sb_rpc(function_name, params=None):
    url = f"{SUPABASE_REST_URL}/rpc/{function_name}"
    res = http_requests.post(url, headers=SUPABASE_HEADERS, json=params or {}, timeout=15)
    if not res.ok:
        log.error("Supabase RPC %s -> %s: %s", function_name, res.status_code, res.text)
        raise Exception("Erro ao calcular estatísticas")
    return res.json()


def sb_upload_file(bucket, path, file_data, content_type):
    url = f"{SUPABASE_STORAGE_URL}/object/{bucket}/{path}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": content_type,
        "x-upsert": "true"
    }
    res = http_requests.post(url, headers=headers, data=file_data, timeout=30)
    if not res.ok:
        log.error("Supabase UPLOAD -> %s: %s", res.status_code, res.text)
        raise Exception("Erro ao fazer upload")
    return res.json()


def sb_get_public_url(bucket, path):
    return f"{SUPABASE_STORAGE_URL}/object/public/{bucket}/{path}"


# Service-role helpers (bypass RLS for admin operations)
_svc = SUPABASE_SERVICE_HEADERS

def svc_get(table, params=None, select="*"):
    url = f"{SUPABASE_REST_URL}/{table}?select={select}"
    if params:
        for k, v in params.items():
            url += f"&{k}={quote(str(v), safe='')}"
    res = http_requests.get(url, headers=_svc, timeout=15)
    if not res.ok:
        log.error("Supabase SVC GET %s -> %s: %s", table, res.status_code, res.text)
        raise Exception("Erro ao acessar dados")
    return res.json()


def svc_insert(table, data):
    url = f"{SUPABASE_REST_URL}/{table}"
    res = http_requests.post(url, headers=_svc, json=data, timeout=15)
    if not res.ok:
        log.error("Supabase SVC INSERT %s -> %s: %s", table, res.status_code, res.text)
        raise Exception("Erro ao salvar dados")
    return res.json()


def svc_update(table, data, filters):
    url = f"{SUPABASE_REST_URL}/{table}"
    for k, v in filters.items():
        url += f"&{k}={quote(str(v), safe='')}" if "?" in url else f"?{k}={quote(str(v), safe='')}"
    res = http_requests.patch(url, headers=_svc, json=data, timeout=15)
    if not res.ok:
        log.error("Supabase SVC UPDATE %s -> %s: %s", table, res.status_code, res.text)
        raise Exception("Erro ao atualizar dados")
    return res.json()


def svc_delete(table, filters):
    url = f"{SUPABASE_REST_URL}/{table}"
    for k, v in filters.items():
        url += f"&{k}={quote(str(v), safe='')}" if "?" in url else f"?{k}={quote(str(v), safe='')}"
    headers = {**_svc, "Prefer": "return=minimal"}
    res = http_requests.delete(url, headers=headers, timeout=15)
    if not res.ok:
        log.error("Supabase SVC DELETE %s -> %s: %s", table, res.status_code, res.text)
        raise Exception("Erro ao excluir dados")
    return True


def svc_rpc(function_name, params=None):
    url = f"{SUPABASE_REST_URL}/rpc/{function_name}"
    res = http_requests.post(url, headers=_svc, json=params or {}, timeout=15)
    if not res.ok:
        log.error("Supabase SVC RPC %s -> %s: %s", function_name, res.status_code, res.text)
        raise Exception("Erro ao calcular estatísticas")
    return res.json()


def svc_upload_file(bucket, path, file_data, content_type):
    url = f"{SUPABASE_STORAGE_URL}/object/{bucket}/{path}"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": content_type,
        "x-upsert": "true"
    }
    res = http_requests.post(url, headers=headers, data=file_data, timeout=30)
    if not res.ok:
        log.error("Supabase SVC UPLOAD -> %s: %s", res.status_code, res.text)
        raise Exception("Erro ao fazer upload")
    return res.json()


# ============================================
# Auth Helpers
# ============================================
def generate_token():
    return hashlib.sha256(secrets.token_hex(32).encode()).hexdigest()


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        ip = request.remote_addr or "unknown"
        if check_rate_limit(ip):
            return jsonify({"error": "Muitas requisições. Aguarde um momento."}), 429

        auth = request.headers.get('Authorization', '')
        token = auth.replace('Bearer ', '') if auth.startswith('Bearer ') else ''
        if not token:
            return jsonify({"error": "Não autorizado"}), 401
        try:
            now = datetime.now(timezone.utc).isoformat()
            sessions = svc_get("admin_sessions",
                              {"token": f"eq.{token}", "expires_at": f"gt.{now}"})
            if not sessions:
                return jsonify({"error": "Sessão expirada"}), 401
        except Exception:
            return jsonify({"error": "Erro ao verificar sessão"}), 500
        return f(*args, **kwargs)
    return decorated


def parse_price(value):
    """Converte preço de string (BR: 10,50) ou number para float."""
    if isinstance(value, (int, float)):
        return max(0.0, float(value))
    if isinstance(value, str):
        return max(0.0, float(value.replace(',', '.')))
    return 0.0


def sanitize_text(text):
    if not isinstance(text, str):
        return ""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = text.replace('"', "&quot;").replace("'", "&#x27;")
    return text


def sanitize_testimonial(t):
    return {
        "id": t.get("id"),
        "name": sanitize_text(t.get("name", "Anônimo")),
        "rating": t.get("rating", 5),
        "comment": sanitize_text(t.get("comment", "")),
        "date": t.get("date", ""),
        "approved": t.get("approved", False)
    }


# ============================================
# Public API: Products
# ============================================
@app.route('/api/products')
def get_products():
    try:
        products = sb_get("products", {"active": "eq.true", "order": "sort_order.asc,created_at.desc"})
        sanitized = []
        for p in products:
            sanitized.append({
                "id": p.get("id"),
                "name": p.get("name", ""),
                "description": p.get("description", ""),
                "price": p.get("price", 0),
                "emoji": p.get("emoji", "🧁"),
                "color1": p.get("color1", "#BD6B62"),
                "color2": p.get("color2", "#D4A69E"),
                "category": p.get("category", "tradicional"),
                "image": p.get("image", ""),
                "whatsapp_link": p.get("whatsapp_link", ""),
                "active": p.get("active", True),
                "sort_order": p.get("sort_order", 0)
            })
        return jsonify(sanitized)
    except Exception:
        return jsonify({"error": "Erro ao carregar produtos"}), 500


@app.route('/api/products/<int:product_id>')
def get_product(product_id):
    try:
        products = sb_get("products", {"id": f"eq.{product_id}"})
        if not products:
            return jsonify({"error": "Produto não encontrado"}), 404
        p = products[0]
        return jsonify({
            "id": p.get("id"),
            "name": p.get("name", ""),
            "description": p.get("description", ""),
            "price": p.get("price", 0),
            "emoji": p.get("emoji", "🧁"),
            "color1": p.get("color1", "#BD6B62"),
            "color2": p.get("color2", "#D4A69E"),
            "category": p.get("category", "tradicional"),
            "image": p.get("image", ""),
            "whatsapp_link": p.get("whatsapp_link", ""),
            "active": p.get("active", True),
            "sort_order": p.get("sort_order", 0)
        })
    except Exception:
        return jsonify({"error": "Erro ao carregar produto"}), 500


@app.route('/api/products/category/<category>')
def get_products_by_category(category):
    if category not in VALID_CATEGORIES:
        return jsonify({"error": "Categoria inválida"}), 400
    try:
        products = sb_get("products",
                          {"active": "eq.true", "category": f"eq.{category}", "order": "sort_order.asc"})
        return jsonify(products)
    except Exception:
        return jsonify({"error": "Erro ao carregar produtos"}), 500


# ============================================
# Public API: Testimonials
# ============================================
@app.route('/api/testimonials', methods=['GET'])
def get_testimonials():
    try:
        testimonials = sb_get("testimonials",
                              {"approved": "eq.true", "order": "date.desc"})
        return jsonify([sanitize_testimonial(t) for t in testimonials])
    except Exception:
        return jsonify({"error": "Erro ao carregar avaliações"}), 500


@app.route('/api/testimonials', methods=['POST'])
def create_testimonial():
    ip = request.remote_addr or "unknown"
    if check_rate_limit(ip):
        return jsonify({"error": "Muitas tentativas. Aguarde um momento."}), 429

    data = request.get_json()
    if not data:
        return jsonify({"error": "Dados inválidos"}), 400

    name = (data.get('name') or 'Anônimo').strip()[0:60] or 'Anônimo'
    rating = data.get('rating')
    comment = (data.get('comment') or '').strip()

    if not isinstance(rating, int) or rating < 1 or rating > 5:
        return jsonify({"error": "Nota inválida. Escolha entre 1 e 5."}), 400
    if len(comment) < 3:
        return jsonify({"error": "Comentário deve ter pelo menos 3 caracteres."}), 400

    comment = comment[:500]

    try:
        result = svc_insert("testimonials", {
            "name": name,
            "rating": rating,
            "comment": comment,
            "approved": False,
            "date": datetime.now(timezone.utc).isoformat()
        })
        return jsonify(result[0] if result else {"message": "Feedback enviado"}), 201
    except Exception:
        return jsonify({"error": "Erro ao enviar avaliação"}), 500


# ============================================
# Public API: Stats
# ============================================
@app.route('/api/stats')
def get_stats():
    try:
        stats = sb_rpc("get_store_stats")
        return jsonify(stats)
    except Exception:
        return jsonify({"error": "Erro ao carregar estatísticas"}), 500


# ============================================
# Health Check
# ============================================
@app.route('/health')
def health():
    return jsonify({"status": "ok", "service": "Thay Cake API", "database": "Supabase"})


# ============================================
# Static File Serving
# ============================================
@app.route('/')
def serve_frontend():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/sabores')
def serve_sabores():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/feedbacks')
def serve_feedbacks():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/avaliar')
def serve_avaliar():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/z_admin')
def serve_admin():
    return send_from_directory(app.static_folder, 'admin.html')


# ============================================
# File Upload
# ============================================
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/api/upload', methods=['POST'])
@require_auth
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Nome de arquivo vazio"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Formato não permitido. Use PNG, JPG, GIF ou WebP"}), 400

    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"prod_{uuid.uuid4().hex[:16]}.{ext}"
    content_type = file.content_type or f"image/{ext}"

    try:
        file_data = file.read()
        svc_upload_file("product-images", filename, file_data, content_type)
        url = sb_get_public_url("product-images", filename)

        svc_insert("uploads", {
            "filename": filename,
            "original_name": file.filename,
            "url": url,
            "mime_type": content_type,
            "file_size": len(file_data)
        })

        return jsonify({"url": url}), 201
    except Exception:
        return jsonify({"error": "Erro ao fazer upload da imagem"}), 500


# ============================================
# Admin: Login
# ============================================
@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    ip = request.remote_addr or "unknown"
    if check_login_rate_limit(ip):
        return jsonify({"error": "Muitas tentativas de login. Tente novamente em 5 minutos."}), 429

    data = request.get_json()
    if not data or data.get('password') != ADMIN_PASSWORD:
        return jsonify({"error": "Senha incorreta"}), 401

    token = generate_token()
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()

    try:
        svc_insert("admin_sessions", {
            "token": token,
            "expires_at": expires_at
        })
    except Exception:
        log.error("Falha ao criar sessão para token %s", token[:8])
        return jsonify({"error": "Erro ao criar sessão"}), 500

    return jsonify({"token": token, "message": "Login bem-sucedido"})


# ============================================
# Admin: Products CRUD
# ============================================
@app.route('/api/admin/products', methods=['POST'])
@require_auth
def admin_create_product():
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({"error": "Nome do produto é obrigatório"}), 400

    base = sanitize_product_input(data)
    if base["category"] not in VALID_CATEGORIES:
        return jsonify({"error": f"Categoria inválida. Use: {', '.join(VALID_CATEGORIES)}"}), 400

    product = {
        **base,
        "whatsapp_link": f"https://wa.me/5589988194690?text=Ol%C3%A1!%20Quero%20pedir%20o%20{quote(base['name'], safe='')}"
    }

    try:
        result = svc_insert("products", product)
        return jsonify(result[0] if result else product), 201
    except Exception:
        return jsonify({"error": "Erro ao criar produto"}), 500


@app.route('/api/admin/products/<int:product_id>', methods=['PUT'])
@require_auth
def admin_update_product(product_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Dados inválidos"}), 400

    updates = {}

    if data.get('name'):
        updates['name'] = strip_html(data['name'])[:60]
    if 'description' in data:
        updates['description'] = strip_html(data.get('description', ''))[:200]
    if 'price' in data:
        updates['price'] = parse_price(data['price'])
    if 'category' in data:
        if data['category'] not in VALID_CATEGORIES:
            return jsonify({"error": f"Categoria inválida. Use: {', '.join(VALID_CATEGORIES)}"}), 400
        updates['category'] = data['category']
    if 'image' in data:
        updates['image'] = (data['image'] or '').strip()
    if 'emoji' in data:
        updates['emoji'] = data['emoji']
    if 'color1' in data:
        updates['color1'] = data['color1']
    if 'color2' in data:
        updates['color2'] = data['color2']
    if 'active' in data:
        updates['active'] = bool(data['active'])
    if 'sort_order' in data:
        updates['sort_order'] = int(data['sort_order'])

    if not updates:
        return jsonify({"error": "Nenhuma alteração fornecida"}), 400

    try:
        result = svc_update("products", updates, {"id": f"eq.{product_id}"})
        if not result:
            return jsonify({"error": "Produto não encontrado"}), 404
        return jsonify(result[0])
    except Exception:
        return jsonify({"error": "Erro ao atualizar produto"}), 500


@app.route('/api/admin/products/<int:product_id>', methods=['DELETE'])
@require_auth
def admin_delete_product(product_id):
    try:
        existing = svc_get("products", {"id": f"eq.{product_id}"})
        if not existing:
            return jsonify({"error": "Produto não encontrado"}), 404
        svc_delete("products", {"id": f"eq.{product_id}"})
        return jsonify({"message": "Produto excluído"})
    except Exception:
        return jsonify({"error": "Erro ao excluir produto"}), 500


# ============================================
# Admin: Testimonials CRUD
# ============================================
@app.route('/api/admin/testimonials/<int:testimonial_id>', methods=['PUT'])
@require_auth
def admin_update_testimonial(testimonial_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Dados inválidos"}), 400

    updates = {}

    if data.get('name'):
        updates['name'] = strip_html(data['name'])[:60]
    if 'rating' in data:
        try:
            rating = int(data['rating'])
        except (ValueError, TypeError):
            return jsonify({"error": "Nota deve ser um número inteiro"}), 400
        if rating < 1 or rating > 5:
            return jsonify({"error": "Nota deve ser entre 1 e 5"}), 400
        updates['rating'] = rating
    if 'comment' in data:
        updates['comment'] = strip_html(data.get('comment', ''))[:500]
    if 'approved' in data:
        updates['approved'] = bool(data['approved'])

    if not updates:
        return jsonify({"error": "Nenhuma alteração fornecida"}), 400

    try:
        result = svc_update("testimonials", updates, {"id": f"eq.{testimonial_id}"})
        if not result:
            return jsonify({"error": "Avaliação não encontrada"}), 404
        return jsonify(result[0])
    except Exception:
        return jsonify({"error": "Erro ao atualizar avaliação"}), 500


@app.route('/api/admin/testimonials/<int:testimonial_id>/approve', methods=['PATCH'])
@require_auth
def admin_approve_testimonial(testimonial_id):
    try:
        existing = svc_get("testimonials", {"id": f"eq.{testimonial_id}"})
        if not existing:
            return jsonify({"error": "Avaliação não encontrada"}), 404
        new_status = not existing[0].get("approved", False)
        result = svc_update("testimonials", {"approved": new_status}, {"id": f"eq.{testimonial_id}"})
        return jsonify({"approved": new_status})
    except Exception:
        return jsonify({"error": "Erro ao atualizar avaliação"}), 500


@app.route('/api/admin/testimonials', methods=['GET'])
@require_auth
def admin_get_testimonials():
    try:
        testimonials = svc_get("testimonials", {"order": "approved.asc,date.desc"})
        return jsonify(testimonials)
    except Exception:
        return jsonify({"error": "Erro ao carregar avaliações"}), 500


@app.route('/api/admin/testimonials/<int:testimonial_id>', methods=['DELETE'])
@require_auth
def admin_delete_testimonial(testimonial_id):
    try:
        existing = svc_get("testimonials", {"id": f"eq.{testimonial_id}"})
        if not existing:
            return jsonify({"error": "Avaliação não encontrada"}), 404
        svc_delete("testimonials", {"id": f"eq.{testimonial_id}"})
        return jsonify({"message": "Avaliação excluída"})
    except Exception:
        return jsonify({"error": "Erro ao excluir avaliação"}), 500


# ============================================
# Error Handlers
# ============================================
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Rota não encontrada"}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Erro interno do servidor"}), 500


# ============================================
# Start
# ============================================
if __name__ == '__main__':
    print("=" * 50)
    print("  Thay Cake API Server (Supabase)")
    print("  http://localhost:5000")
    print("  Admin: http://localhost:5000/z_admin")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=False)
