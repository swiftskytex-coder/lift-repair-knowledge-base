"""
Веб-сервер базы знаний
Порт: 8082
"""

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import json
from datetime import datetime
from knowledge_db import KnowledgeBaseDB
from integration_manager import IntegrationManager

app = Flask(__name__)
CORS(app)

# Инициализация базы данных и менеджера интеграции
kb_db = KnowledgeBaseDB()
integration = IntegrationManager()


# ======== Веб-интерфейс ========

@app.route('/')
def dashboard():
    """Главная страница базы знаний"""
    stats = kb_db.get_statistics()
    return render_template('knowledge_dashboard.html', stats=stats)


@app.route('/articles')
def articles_page():
    """Страница статей"""
    return render_template('articles.html')


@app.route('/objects')
def objects_page():
    """Страница объектов"""
    return render_template('objects.html')


@app.route('/search')
def search_page():
    """Страница поиска"""
    return render_template('search.html')


# ======== API: Статьи базы знаний ========

@app.route('/api/kb/articles', methods=['GET'])
def get_articles():
    """Получение списка статей"""
    query = request.args.get('q', '')
    category = request.args.get('category')
    equipment_type = request.args.get('equipment_type')
    manufacturer = request.args.get('manufacturer')
    limit = request.args.get('limit', 20, type=int)
    
    articles = kb_db.search_knowledge(
        query=query if query else None,
        category=category,
        equipment_type=equipment_type,
        manufacturer=manufacturer,
        limit=limit
    )
    
    return jsonify({
        'total': len(articles),
        'articles': articles
    })


@app.route('/api/kb/articles', methods=['POST'])
def create_article():
    """Создание новой статьи"""
    data = request.get_json()
    
    if not data or 'title' not in data or 'content' not in data:
        return jsonify({'error': 'Missing required fields: title, content'}), 400
    
    try:
        article_id = kb_db.create_knowledge_article(data)
        return jsonify({
            'success': True,
            'article_id': article_id,
            'message': 'Article created successfully'
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/kb/articles/<int:article_id>', methods=['GET'])
def get_article(article_id):
    """Получение статьи по ID"""
    article = kb_db.get_knowledge_article(article_id)
    
    if not article:
        return jsonify({'error': 'Article not found'}), 404
    
    return jsonify(article)


@app.route('/api/kb/search', methods=['POST'])
def search_knowledge():
    """Поиск по базе знаний"""
    data = request.get_json()
    
    if not data or 'query' not in data:
        return jsonify({'error': 'Missing query'}), 400
    
    articles = kb_db.search_knowledge(
        query=data['query'],
        category=data.get('category'),
        equipment_type=data.get('equipment_type'),
        manufacturer=data.get('manufacturer'),
        limit=data.get('limit', 20)
    )
    
    return jsonify({
        'query': data['query'],
        'results': articles
    })


# ======== API: Объекты ========

@app.route('/api/objects', methods=['GET'])
def get_objects():
    """Получение списка объектов"""
    conn = kb_db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM objects 
        ORDER BY created_at DESC
    ''')
    
    rows = cursor.fetchall()
    conn.close()
    
    objects = [kb_db._row_to_dict(row) for row in rows]
    
    return jsonify({
        'total': len(objects),
        'objects': objects
    })


@app.route('/api/objects', methods=['POST'])
def create_object():
    """Создание нового объекта"""
    data = request.get_json()
    
    if not data or 'address' not in data:
        return jsonify({'error': 'Missing required field: address'}), 400
    
    try:
        object_id = kb_db.create_object(data)
        return jsonify({
            'success': True,
            'object_id': object_id,
            'message': 'Object created successfully'
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/objects/<int:object_id>', methods=['GET'])
def get_object(object_id):
    """Получение объекта по ID"""
    conn = kb_db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM objects WHERE id = ?', (object_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return jsonify({'error': 'Object not found'}), 404
    
    return jsonify(kb_db._row_to_dict(row))


@app.route('/api/objects/<int:object_id>/history', methods=['GET'])
def get_object_history(object_id):
    """Получение истории обслуживания объекта"""
    limit = request.args.get('limit', 50, type=int)
    
    history = kb_db.get_object_history(object_id, limit)
    
    return jsonify({
        'object_id': object_id,
        'total_records': len(history),
        'history': history
    })


@app.route('/api/objects/<int:object_id>/history', methods=['POST'])
def add_maintenance_record(object_id):
    """Добавление записи об обслуживании"""
    data = request.get_json()
    
    if not data or 'date' not in data or 'work_type' not in data or 'description' not in data:
        return jsonify({'error': 'Missing required fields: date, work_type, description'}), 400
    
    data['object_id'] = object_id
    
    try:
        record_id = kb_db.add_maintenance_record(data)
        return jsonify({
            'success': True,
            'record_id': record_id,
            'message': 'Maintenance record added successfully'
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ======== API: Типовые неисправности ========

@app.route('/api/issues', methods=['GET'])
def get_common_issues():
    """Получение списка типовых неисправностей"""
    equipment_type = request.args.get('equipment_type')
    priority = request.args.get('priority')
    
    issues = kb_db.get_common_issues(equipment_type, priority)
    
    return jsonify({
        'total': len(issues),
        'issues': issues
    })


@app.route('/api/issues', methods=['POST'])
def create_common_issue():
    """Создание типовой неисправности"""
    data = request.get_json()
    
    if not data or 'issue_code' not in data or 'title' not in data:
        return jsonify({'error': 'Missing required fields: issue_code, title'}), 400
    
    try:
        issue_id = kb_db.create_common_issue(data)
        return jsonify({
            'success': True,
            'issue_id': issue_id,
            'message': 'Common issue created successfully'
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ======== API: Интеграция с заявками ========

@app.route('/api/integration/ticket/<int:ticket_id>/context', methods=['GET'])
def get_ticket_context(ticket_id):
    """Получение контекста для заявки"""
    context = integration.get_ticket_context(ticket_id)
    
    if 'error' in context:
        return jsonify(context), 404 if context['error'] == 'Ticket not found' else 503
    
    return jsonify(context)


@app.route('/api/integration/ticket/<int:ticket_id>/suggest', methods=['GET'])
def suggest_solutions(ticket_id):
    """Предложение решений для заявки"""
    suggestions = integration.suggest_solutions_for_ticket(ticket_id)
    
    if 'error' in suggestions:
        return jsonify(suggestions), 404 if suggestions['error'] == 'Ticket not found' else 503
    
    return jsonify(suggestions)


@app.route('/api/integration/ticket/<int:ticket_id>/create-knowledge', methods=['POST'])
def create_knowledge_from_ticket(ticket_id):
    """Создание статьи из заявки"""
    data = request.get_json() or {}
    
    result = integration.create_knowledge_from_ticket(ticket_id, data)
    
    if 'error' in result:
        return jsonify(result), 404 if result['error'] == 'Ticket not found' else 500
    
    return jsonify(result), 201


# ======== API: Интеграция со складом ========

@app.route('/api/integration/parts/check', methods=['POST'])
def check_parts():
    """Проверка наличия запчастей"""
    data = request.get_json()
    
    if not data or 'parts' not in data:
        return jsonify({'error': 'Missing required field: parts'}), 400
    
    result = integration.check_parts_availability(data['parts'])
    return jsonify(result)


@app.route('/api/integration/parts/recommend', methods=['POST'])
def recommend_parts():
    """Рекомендации по запчастям для проблемы"""
    data = request.get_json()
    
    if not data or 'problem' not in data:
        return jsonify({'error': 'Missing required field: problem'}), 400
    
    recommendations = integration.get_parts_recommendations(data['problem'])
    return jsonify({
        'problem': data['problem'],
        'recommendations': recommendations
    })


@app.route('/api/integration/parts/consume', methods=['POST'])
def consume_parts():
    """Списание запчастей"""
    data = request.get_json()
    
    if not data or 'ticket_id' not in data or 'parts' not in data:
        return jsonify({'error': 'Missing required fields: ticket_id, parts'}), 400
    
    result = integration.consume_parts_for_ticket(data['ticket_id'], data['parts'])
    return jsonify(result)


# ======== API: Отчеты ========

@app.route('/api/reports/maintenance/<int:object_id>', methods=['GET'])
def maintenance_report(object_id):
    """Отчет по обслуживанию объекта"""
    date_from = request.args.get('from')
    date_to = request.args.get('to')
    
    report = integration.generate_maintenance_report(object_id, date_from, date_to)
    return jsonify(report)


@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    """Статистика системы"""
    stats = kb_db.get_statistics()
    return jsonify(stats)


@app.route('/api/integration/statistics', methods=['GET'])
def get_integration_stats():
    """Статистика интеграции"""
    stats = integration.get_integration_statistics()
    return jsonify(stats)


# ======== API: Поиск решений ========

@app.route('/api/solutions/find', methods=['POST'])
def find_solutions():
    """Поиск решений для проблемы"""
    data = request.get_json()
    
    if not data or 'problem' not in data:
        return jsonify({'error': 'Missing required field: problem'}), 400
    
    solutions = kb_db.find_solutions_for_ticket(
        data['problem'],
        data.get('elevator_model')
    )
    
    return jsonify({
        'problem': data['problem'],
        'solutions_count': len(solutions),
        'solutions': solutions
    })


# ======== API: Каталог оборудования ========

@app.route('/api/equipment', methods=['GET'])
def get_equipment_catalog():
    """Получение каталога оборудования"""
    conn = kb_db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM equipment_catalog ORDER BY manufacturer, model')
    rows = cursor.fetchall()
    conn.close()
    
    equipment = [kb_db._row_to_dict(row) for row in rows]
    
    return jsonify({
        'total': len(equipment),
        'equipment': equipment
    })


@app.route('/api/equipment/<manufacturer>/<model>', methods=['GET'])
def get_equipment_item(manufacturer, model):
    """Получение информации об оборудовании"""
    conn = kb_db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM equipment_catalog 
        WHERE manufacturer = ? AND model = ?
    ''', (manufacturer, model))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return jsonify({'error': 'Equipment not found'}), 404
    
    return jsonify(kb_db._row_to_dict(row))


# ======== API: Health check ========

@app.route('/api/health', methods=['GET'])
def health_check():
    """Проверка работоспособности"""
    return jsonify({
        'status': 'healthy',
        'service': 'knowledge-base',
        'timestamp': datetime.now().isoformat()
    })


if __name__ == '__main__':
    print("🚀 Запуск сервера базы знаний...")
    print("📚 API документация: http://localhost:8082/api/docs")
    print("🌐 Веб-интерфейс: http://localhost:8082")
    app.run(debug=True, host='0.0.0.0', port=8082)
