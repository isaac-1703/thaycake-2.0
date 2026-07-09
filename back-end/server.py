import hashlib
import secrets
from functools import wraps

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import json
from datetime import datetime

app = Flask(__name__, static_folder='../front-end', static_url_path='')
app.secret_key = 'thaycake-admin-secret-key-change-in-production'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
CORS(app)

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'front-end', 'uploads')
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

ADMIN_PASSWORD = 'admin123'
admin_tokens = {}


def generate_token():
    return hashlib.sha256(secrets.token_hex(32).encode()).hexdigest()


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        token = auth.replace('Bearer ', '') if auth.startswith('Bearer ') else ''
        if token not in admin_tokens:
            return jsonify({"error": "Não autorizado"}), 401
        return f(*args, **kwargs)
    return decorated

PRODUCTS_FILE = os.path.join(DATA_DIR, 'products.json')
TESTIMONIALS_FILE = os.path.join(DATA_DIR, 'testimonials.json')

DEFAULT_PRODUCTS = [
    {
        "id": 1,
        "name": "Brigadeiro",
        "description": "Clássico bolo de pote com massa de chocolate e recheio cremoso de brigadeiro.",
        "price": 12.00,
        "emoji": "🍫",
        "color1": "#5C3A30",
        "color2": "#8B5E4A",
        "category": "tradicional",
        "whatsapp_link": "https://wa.me/5589988194690?text=Ol%C3%A1!%20Quero%20pedir%20o%20Bolo%20de%20Pote%20de%20Brigadeiro%20%F0%9F%8D%AB"
    },
    {
        "id": 2,
        "name": "Morango com Leite Condensado",
        "description": "Camadas de bolo branco, morangos frescos e leite condensado cremoso.",
        "price": 14.00,
        "emoji": "🍓",
        "color1": "#E8A0A0",
        "color2": "#D46A6A",
        "category": "frutas",
        "whatsapp_link": "https://wa.me/5589988194690?text=Ol%C3%A1!%20Quero%20pedir%20o%20Bolo%20de%20Pote%20de%20Morango%20%F0%9F%8D%93"
    },
    {
        "id": 3,
        "name": "Churros",
        "description": "Bolo de canela com recheio de doce de leite e cobertura de açúcar com canela.",
        "price": 13.00,
        "emoji": "🥟",
        "color1": "#E8C84A",
        "color2": "#C49A2C",
        "category": "especial",
        "whatsapp_link": "https://wa.me/5589988194690?text=Ol%C3%A1!%20Quero%20pedir%20o%20Bolo%20de%20Pote%20de%20Churros%20%F0%9F%A5%9F"
    },
    {
        "id": 4,
        "name": "Ninho com Nutella",
        "description": "Massa branca fofinha com recheio cremoso de Ninho e Nutella.",
        "price": 15.00,
        "emoji": "🤎",
        "color1": "#D4A0D4",
        "color2": "#A86AA8",
        "category": "premium",
        "whatsapp_link": "https://wa.me/5589988194690?text=Ol%C3%A1!%20Quero%20pedir%20o%20Bolo%20de%20Pote%20de%20Ninho%20com%20Nutella%20%F0%9F%A4%8E"
    },
    {
        "id": 5,
        "name": "Red Velvet",
        "description": "Bolo vermelho aveludado com cream cheese frosting.",
        "price": 16.00,
        "emoji": "❤️",
        "color1": "#C84B4B",
        "color2": "#8A2E2E",
        "category": "premium",
        "whatsapp_link": "https://wa.me/5589988194690?text=Ol%C3%A1!%20Quero%20pedir%20o%20Bolo%20de%20Pote%20Red%20Velvet%20%E2%9D%A4%EF%B8%8F"
    },
    {
        "id": 6,
        "name": "Limão",
        "description": "Bolo branco com recheio cítrico de limão e cobertura de merengue.",
        "price": 12.00,
        "emoji": "🍋",
        "color1": "#C8E8A0",
        "color2": "#8AB84A",
        "category": "frutas",
        "whatsapp_link": "https://wa.me/5589988194690?text=Ol%C3%A1!%20Quero%20pedir%20o%20Bolo%20de%20Pote%20de%20Lim%C3%A3o%20%F0%9F%8D%8B"
    }
]

DEFAULT_TESTIMONIALS = [
    {
        "id": 1,
        "name": "Ana Clara",
        "rating": 5,
        "comment": "Simplesmente os melhores bolos de pote da região! O brigadeiro é sensacional, super cremoso.",
        "date": "2026-06-20T14:30:00"
    },
    {
        "id": 2,
        "name": "Rafaela",
        "rating": 5,
        "comment": "Comprei para o aniversário da minha filha e foi um sucesso! Todos amaram. Super recomendo!",
        "date": "2026-06-18T10:15:00"
    },
    {
        "id": 3,
        "name": "Lucas",
        "rating": 4,
        "comment": "Bolo de pote de churros é maravilhoso! Entrega rápida e bem embalado.",
        "date": "2026-06-15T16:45:00"
    },
    {
        "id": 4,
        "name": "Juliana",
        "rating": 5,
        "comment": "O de morango é de outro nível! Você sente o gosto do morango fresco. Muito bom!",
        "date": "2026-06-12T09:00:00"
    },
    {
        "id": 5,
        "name": "Marcos",
        "rating": 5,
        "comment": "Entrega pontual e bolos deliciosos. O Red Velvet é o meu favorito, cremoso na medida certa.",
        "date": "2026-06-10T19:20:00"
    },
    {
        "id": 6,
        "name": "Camila",
        "rating": 4,
        "comment": "Produtos de qualidade e atendimento excelente pelo WhatsApp. Nota 10!",
        "date": "2026-06-08T11:30:00"
    }
]


def load_json(filepath, default):
    if not os.path.exists(filepath):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(default, f, ensure_ascii=False, indent=2)
        return default
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return default


def save_json(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@app.route('/api/products')
def get_products():
    products = load_json(PRODUCTS_FILE, DEFAULT_PRODUCTS)
    return jsonify(products)


@app.route('/api/products/<int:product_id>')
def get_product(product_id):
    products = load_json(PRODUCTS_FILE, DEFAULT_PRODUCTS)
    product = next((p for p in products if p['id'] == product_id), None)
    if product is None:
        return jsonify({"error": "Produto não encontrado"}), 404
    return jsonify(product)


@app.route('/api/products/category/<category>')
def get_products_by_category(category):
    products = load_json(PRODUCTS_FILE, DEFAULT_PRODUCTS)
    filtered = [p for p in products if p['category'] == category]
    return jsonify(filtered)


@app.route('/api/testimonials', methods=['GET'])
def get_testimonials():
    testimonials = load_json(TESTIMONIALS_FILE, DEFAULT_TESTIMONIALS)
    testimonials.sort(key=lambda t: t.get('date', ''), reverse=True)
    return jsonify(testimonials)


@app.route('/api/testimonials', methods=['POST'])
def create_testimonial():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Dados inválidos"}), 400

    name = data.get('name', 'Anônimo').strip() or 'Anônimo'
    rating = data.get('rating')
    comment = data.get('comment', '').strip()

    if not rating or not isinstance(rating, int) or rating < 1 or rating > 5:
        return jsonify({"error": "Nota inválida. Escolha entre 1 e 5."}), 400

    if not comment or len(comment) < 3:
        return jsonify({"error": "Comentário deve ter pelo menos 3 caracteres."}), 400

    if len(name) > 60:
        name = name[:60]

    if len(comment) > 500:
        comment = comment[:500]

    testimonials = load_json(TESTIMONIALS_FILE, DEFAULT_TESTIMONIALS)

    new_id = max((t['id'] for t in testimonials), default=0) + 1

    new_testimonial = {
        "id": new_id,
        "name": name,
        "rating": rating,
        "comment": comment,
        "date": datetime.now().isoformat()
    }

    testimonials.append(new_testimonial)
    save_json(TESTIMONIALS_FILE, testimonials)

    return jsonify(new_testimonial), 201


@app.route('/api/stats')
def get_stats():
    testimonials = load_json(TESTIMONIALS_FILE, DEFAULT_TESTIMONIALS)
    products = load_json(PRODUCTS_FILE, DEFAULT_PRODUCTS)

    total_ratings = len(testimonials)
    avg_rating = round(
        sum(t['rating'] for t in testimonials) / total_ratings, 1
    ) if total_ratings > 0 else 0

    return jsonify({
        "total_products": len(products),
        "total_testimonials": total_ratings,
        "average_rating": avg_rating
    })


@app.route('/health')
def health():
    return jsonify({"status": "ok", "service": "Thay Cake API"})


SECTION_ROUTES = ['/sabores', '/feedbacks', '/avaliar']


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
    filename = f"prod_{secrets.token_hex(8)}.{ext}"
    file.save(os.path.join(UPLOAD_DIR, filename))
    return jsonify({"url": f"/uploads/{filename}"}), 201


@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    if not data or data.get('password') != ADMIN_PASSWORD:
        return jsonify({"error": "Senha incorreta"}), 401

    token = generate_token()
    admin_tokens[token] = datetime.now().isoformat()

    if len(admin_tokens) > 50:
        cutoff = list(admin_tokens.keys())[:-40]
        for t in cutoff:
            admin_tokens.pop(t, None)

    return jsonify({"token": token, "message": "Login bem-sucedido"})


@app.route('/api/admin/products', methods=['POST'])
@require_auth
def admin_create_product():
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({"error": "Nome do produto é obrigatório"}), 400

    products = load_json(PRODUCTS_FILE, DEFAULT_PRODUCTS)
    new_id = max((p['id'] for p in products), default=0) + 1

    product = {
        "id": new_id,
        "name": data['name'].strip()[:60],
        "description": (data.get('description') or '').strip()[:200],
        "price": max(0, float(data.get('price', 0))),
        "emoji": data.get('emoji', '🧁'),
        "color1": data.get('color1', '#BD6B62'),
        "color2": data.get('color2', '#D4A69E'),
        "category": data.get('category', 'tradicional'),
        "image": (data.get('image') or '').strip(),
        "whatsapp_link": f"https://wa.me/5589988194690?text=Ol%C3%A1!%20Quero%20pedir%20o%20{data['name'].replace(' ', '%20')}"
    }

    products.append(product)
    save_json(PRODUCTS_FILE, products)
    return jsonify(product), 201


@app.route('/api/admin/products/<int:product_id>', methods=['PUT'])
@require_auth
def admin_update_product(product_id):
    data = request.get_json()
    products = load_json(PRODUCTS_FILE, DEFAULT_PRODUCTS)
    product = next((p for p in products if p['id'] == product_id), None)

    if not product:
        return jsonify({"error": "Produto não encontrado"}), 404

    if data.get('name'):
        product['name'] = data['name'].strip()[:60]
    if 'description' in data:
        product['description'] = (data['description'] or '').strip()[:200]
    if 'price' in data:
        product['price'] = max(0, float(data['price']))
    if 'category' in data:
        product['category'] = data['category']
    if 'image' in data:
        product['image'] = (data['image'] or '').strip()
    if 'emoji' in data:
        product['emoji'] = data['emoji']
    if 'color1' in data:
        product['color1'] = data['color1']
    if 'color2' in data:
        product['color2'] = data['color2']

    product['whatsapp_link'] = f"https://wa.me/5589988194690?text=Ol%C3%A1!%20Quero%20pedir%20o%20{product['name'].replace(' ', '%20')}"

    save_json(PRODUCTS_FILE, products)
    return jsonify(product)


@app.route('/api/admin/products/<int:product_id>', methods=['DELETE'])
@require_auth
def admin_delete_product(product_id):
    products = load_json(PRODUCTS_FILE, DEFAULT_PRODUCTS)
    product = next((p for p in products if p['id'] == product_id), None)

    if not product:
        return jsonify({"error": "Produto não encontrado"}), 404

    products = [p for p in products if p['id'] != product_id]
    save_json(PRODUCTS_FILE, products)
    return jsonify({"message": "Produto excluído"})


@app.route('/api/admin/testimonials/<int:testimonial_id>', methods=['PUT'])
@require_auth
def admin_update_testimonial(testimonial_id):
    data = request.get_json()
    testimonials = load_json(TESTIMONIALS_FILE, DEFAULT_TESTIMONIALS)
    testimonial = next((t for t in testimonials if t['id'] == testimonial_id), None)

    if not testimonial:
        return jsonify({"error": "Avaliação não encontrada"}), 404

    if data.get('name'):
        testimonial['name'] = data['name'].strip()[:60]
    if 'rating' in data:
        rating = int(data['rating'])
        if rating < 1 or rating > 5:
            return jsonify({"error": "Nota deve ser entre 1 e 5"}), 400
        testimonial['rating'] = rating
    if 'comment' in data:
        testimonial['comment'] = (data['comment'] or '').strip()[:500]

    save_json(TESTIMONIALS_FILE, testimonials)
    return jsonify(testimonial)


@app.route('/api/admin/testimonials/<int:testimonial_id>', methods=['DELETE'])
@require_auth
def admin_delete_testimonial(testimonial_id):
    testimonials = load_json(TESTIMONIALS_FILE, DEFAULT_TESTIMONIALS)
    testimonial = next((t for t in testimonials if t['id'] == testimonial_id), None)

    if not testimonial:
        return jsonify({"error": "Avaliação não encontrada"}), 404

    testimonials = [t for t in testimonials if t['id'] != testimonial_id]
    save_json(TESTIMONIALS_FILE, testimonials)
    return jsonify({"message": "Avaliação excluída"})


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Rota não encontrada"}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Erro interno do servidor"}), 500


if __name__ == '__main__':
    print("=" * 50)
    print("  Thay Cake API Server")
    print("  http://localhost:5000")
    print("  Admin: http://localhost:5000/z_admin")
    print("  Senha: admin123")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)
