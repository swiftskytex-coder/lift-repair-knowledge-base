import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple

class KnowledgeBaseDB:
    """База данных для системы знаний"""
    
    def __init__(self, db_path: str = "knowledge_base.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Инициализация структуры базы данных"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Таблица статей знаний
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                equipment_type TEXT,
                manufacturer TEXT,
                model TEXT,
                serial_number TEXT,
                photos TEXT,  -- JSON массив путей к фото
                symptoms TEXT,  -- JSON массив
                solution TEXT,
                parts_used TEXT,  -- JSON массив артикулов
                difficulty_level INTEGER CHECK(difficulty_level BETWEEN 1 AND 5),
                estimated_time INTEGER,  -- в минутах
                tags TEXT,  -- JSON массив
                views_count INTEGER DEFAULT 0,
                helpful_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица типовых неисправностей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS common_issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                issue_code TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                equipment_types TEXT,  -- JSON массив
                typical_causes TEXT,  -- JSON массив
                solutions TEXT,  -- JSON массив ID статей
                priority TEXT CHECK(priority IN ('срочный', 'высокий', 'обычный', 'низкий')),
                frequency INTEGER DEFAULT 0,  -- частота возникновения
                avg_repair_time INTEGER,  -- среднее время ремонта в минутах
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица объектов (адреса с лифтами)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS objects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT NOT NULL,
                client_name TEXT,
                client_phone TEXT,
                client_email TEXT,
                elevator_model TEXT,
                elevator_id TEXT,
                elevator_type TEXT,  -- пассажирский, грузовой, больничный
                manufacturer TEXT,
                installation_date DATE,
                last_maintenance DATE,
                next_maintenance DATE,
                status TEXT DEFAULT 'active' CHECK(status IN ('active', 'inactive', 'repair')),
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица истории обслуживания
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS maintenance_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                object_id INTEGER NOT NULL,
                ticket_id INTEGER,
                date DATE NOT NULL,
                work_type TEXT NOT NULL,  -- ремонт, обслуживание, модернизация
                description TEXT NOT NULL,
                technician TEXT,
                parts_used TEXT,  -- JSON {article: quantity}
                duration INTEGER,  -- в минутах
                cost DECIMAL(10,2),
                result TEXT,  -- результат работы
                recommendations TEXT,
                FOREIGN KEY (object_id) REFERENCES objects(id)
            )
        ''')
        
        # Таблица связи заявок со знаниями
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ticket_knowledge_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL,
                knowledge_id INTEGER NOT NULL,
                relevance_score REAL,
                was_helpful BOOLEAN,
                technician_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (knowledge_id) REFERENCES knowledge_articles(id)
            )
        ''')
        
        # Таблица справочника оборудования
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS equipment_catalog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipment_type TEXT NOT NULL,  -- лифт, эскалатор, подъемник
                manufacturer TEXT NOT NULL,
                model TEXT NOT NULL,
                specifications TEXT,  -- JSON
                manuals_urls TEXT,  -- JSON массив ссылок
                typical_parts TEXT,  -- JSON массив артикулов типовых запчастей
                maintenance_schedule TEXT,  -- JSON график ТО
                notes TEXT,
                UNIQUE(manufacturer, model)
            )
        ''')
        
        # Индексы для быстрого поиска
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_knowledge_category ON knowledge_articles(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_knowledge_equipment ON knowledge_articles(equipment_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_knowledge_manufacturer ON knowledge_articles(manufacturer)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_objects_address ON objects(address)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_maintenance_object ON maintenance_history(object_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_maintenance_date ON maintenance_history(date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_issues_code ON common_issues(issue_code)')
        
        conn.commit()
        conn.close()
    
    # ======== Методы для работы со статьями знаний ========
    
    def create_knowledge_article(self, data: Dict) -> int:
        """Создание статьи знаний"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO knowledge_articles 
            (category, title, content, equipment_type, manufacturer, model, serial_number, photos,
             symptoms, solution, parts_used, difficulty_level, estimated_time, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['category'],
            data['title'],
            data['content'],
            data.get('equipment_type'),
            data.get('manufacturer'),
            data.get('model'),
            data.get('serial_number'),
            json.dumps(data.get('photos', []), ensure_ascii=False),
            json.dumps(data.get('symptoms', []), ensure_ascii=False),
            data.get('solution'),
            json.dumps(data.get('parts_used', []), ensure_ascii=False),
            data.get('difficulty_level'),
            data.get('estimated_time'),
            json.dumps(data.get('tags', []), ensure_ascii=False)
        ))
        
        article_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return article_id if article_id is not None else 0
    
    def search_knowledge(self, query: Optional[str] = None, category: Optional[str] = None,
                        equipment_type: Optional[str] = None, manufacturer: Optional[str] = None,
                        limit: int = 20) -> List[Dict]:
        """Поиск по базе знаний"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        sql = "SELECT * FROM knowledge_articles WHERE 1=1"
        params = []
        
        if query:
            sql += " AND (title LIKE ? OR content LIKE ? OR solution LIKE ?)"
            params.extend([f"%{query}%", f"%{query}%", f"%{query}%"])
        
        if category:
            sql += " AND category = ?"
            params.append(category)
        
        if equipment_type:
            sql += " AND equipment_type = ?"
            params.append(equipment_type)
        
        if manufacturer:
            sql += " AND manufacturer = ?"
            params.append(manufacturer)
        
        sql += " ORDER BY views_count DESC, created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_dict(row) for row in rows]
    
    def get_knowledge_article(self, article_id: int) -> Optional[Dict]:
        """Получение статьи по ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE knowledge_articles 
            SET views_count = views_count + 1 
            WHERE id = ?
        ''', (article_id,))
        
        cursor.execute('SELECT * FROM knowledge_articles WHERE id = ?', (article_id,))
        row = cursor.fetchone()
        conn.commit()
        conn.close()
        
        if row:
            return self._row_to_dict(row)
        return None
    
    # ======== Методы для работы с объектами ========
    
    def create_object(self, data: Dict) -> int:
        """Создание объекта (адреса с лифтом)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO objects 
            (address, client_name, client_phone, client_email, elevator_model,
             elevator_id, elevator_type, manufacturer, installation_date, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['address'],
            data.get('client_name'),
            data.get('client_phone'),
            data.get('client_email'),
            data.get('elevator_model'),
            data.get('elevator_id'),
            data.get('elevator_type'),
            data.get('manufacturer'),
            data.get('installation_date'),
            data.get('notes')
        ))
        
        object_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return object_id if object_id is not None else 0
    
    def get_object_history(self, object_id: int, limit: int = 50) -> List[Dict]:
        """Получение истории обслуживания объекта"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM maintenance_history 
            WHERE object_id = ? 
            ORDER BY date DESC 
            LIMIT ?
        ''', (object_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_dict(row) for row in rows]
    
    def add_maintenance_record(self, data: Dict) -> int:
        """Добавление записи об обслуживании"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO maintenance_history 
            (object_id, ticket_id, date, work_type, description, technician,
             parts_used, duration, cost, result, recommendations)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['object_id'],
            data.get('ticket_id'),
            data['date'],
            data['work_type'],
            data['description'],
            data.get('technician'),
            json.dumps(data.get('parts_used', {}), ensure_ascii=False),
            data.get('duration'),
            data.get('cost'),
            data.get('result'),
            data.get('recommendations')
        ))
        
        record_id = cursor.lastrowid
        
        # Обновляем дату последнего обслуживания в объекте
        cursor.execute('''
            UPDATE objects 
            SET last_maintenance = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (data['date'], data['object_id']))
        
        conn.commit()
        conn.close()
        return record_id if record_id is not None else 0
    
    # ======== Методы для работы с типовыми неисправностями ========
    
    def create_common_issue(self, data: Dict) -> int:
        """Создание типовой неисправности"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO common_issues 
            (issue_code, title, description, equipment_types, typical_causes, 
             solutions, priority, avg_repair_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['issue_code'],
            data['title'],
            data['description'],
            json.dumps(data.get('equipment_types', []), ensure_ascii=False),
            json.dumps(data.get('typical_causes', []), ensure_ascii=False),
            json.dumps(data.get('solutions', []), ensure_ascii=False),
            data.get('priority', 'обычный'),
            data.get('avg_repair_time')
        ))
        
        issue_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return issue_id if issue_id is not None else 0
    
    def get_common_issues(self, equipment_type: Optional[str] = None,
                         priority: Optional[str] = None) -> List[Dict]:
        """Получение списка типовых неисправностей"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        sql = "SELECT * FROM common_issues WHERE 1=1"
        params = []
        
        if equipment_type:
            sql += " AND equipment_types LIKE ?"
            params.append(f'%"{equipment_type}"%')
        
        if priority:
            sql += " AND priority = ?"
            params.append(priority)
        
        sql += " ORDER BY frequency DESC, priority DESC"
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_dict(row) for row in rows]
    
    # ======== Методы для поиска решений ========
    
    def find_solutions_for_ticket(self, problem_description: str,
                                  elevator_model: Optional[str] = None) -> List[Dict]:
        """Поиск решений для заявки на основе описания проблемы"""
        # Ищем по ключевым словам в описании проблемы
        keywords = problem_description.lower().split()
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Простой поиск по ключевым словам
        results = []
        for keyword in keywords:
            if len(keyword) > 3:  # Игнорируем короткие слова
                cursor.execute('''
                    SELECT *, 
                        CASE 
                            WHEN title LIKE ? THEN 3
                            WHEN symptoms LIKE ? THEN 2
                            WHEN content LIKE ? THEN 1
                            ELSE 0
                        END as relevance
                    FROM knowledge_articles
                    WHERE title LIKE ? OR symptoms LIKE ? OR content LIKE ?
                ''', (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%",
                      f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"))
                
                rows = cursor.fetchall()
                for row in rows:
                    article = self._row_to_dict(row)
                    article['relevance_score'] = row['relevance']
                    results.append(article)
        
        conn.close()
        
        # Удаляем дубликаты и сортируем по релевантности
        seen_ids = set()
        unique_results = []
        for r in sorted(results, key=lambda x: x['relevance_score'], reverse=True):
            if r['id'] not in seen_ids:
                seen_ids.add(r['id'])
                unique_results.append(r)
        
        return unique_results[:10]
    
    def link_ticket_to_knowledge(self, ticket_id: int, knowledge_id: int,
                                 relevance_score: Optional[float] = None):
        """Связывание заявки со статьей знаний"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO ticket_knowledge_links 
            (ticket_id, knowledge_id, relevance_score)
            VALUES (?, ?, ?)
        ''', (ticket_id, knowledge_id, relevance_score))
        
        conn.commit()
        conn.close()
    
    # ======== Вспомогательные методы ========
    
    def _row_to_dict(self, row: sqlite3.Row) -> Dict:
        """Преобразование строки в словарь"""
        result = {}
        for key in row.keys():
            value = row[key]
            # Десериализация JSON полей
            if key in ['symptoms', 'parts_used', 'tags', 'equipment_types', 
                      'typical_causes', 'solutions', 'manuals_urls', 
                      'typical_parts', 'maintenance_schedule'] and value:
                try:
                    result[key] = json.loads(value)
                except:
                    result[key] = value
            else:
                result[key] = value
        return result
    
    def get_statistics(self) -> Dict:
        """Получение статистики базы знаний"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # Количество статей
        cursor.execute('SELECT COUNT(*) FROM knowledge_articles')
        stats['total_articles'] = cursor.fetchone()[0]
        
        # Количество по категориям
        cursor.execute('''
            SELECT category, COUNT(*) 
            FROM knowledge_articles 
            GROUP BY category
        ''')
        stats['by_category'] = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Количество объектов
        cursor.execute('SELECT COUNT(*) FROM objects')
        stats['total_objects'] = cursor.fetchone()[0]
        
        # Количество записей в истории
        cursor.execute('SELECT COUNT(*) FROM maintenance_history')
        stats['total_maintenance_records'] = cursor.fetchone()[0]
        
        # Типовые неисправности
        cursor.execute('SELECT COUNT(*) FROM common_issues')
        stats['total_common_issues'] = cursor.fetchone()[0]
        
        # Самые популярные статьи
        cursor.execute('''
            SELECT id, title, views_count 
            FROM knowledge_articles 
            ORDER BY views_count DESC 
            LIMIT 5
        ''')
        stats['top_articles'] = [
            {'id': row[0], 'title': row[1], 'views': row[2]}
            for row in cursor.fetchall()
        ]
        
        conn.close()
        return stats


# Инициализация базы данных при импорте
if __name__ == "__main__":
    db = KnowledgeBaseDB()
    print("✅ База данных инициализирована")
    
    # Демонстрация статистики
    stats = db.get_statistics()
    print("\n📊 Статистика:")
    print(f"   Всего статей: {stats['total_articles']}")
    print(f"   Объектов: {stats['total_objects']}")
    print(f"   Записей обслуживания: {stats['total_maintenance_records']}")
    print(f"   Типовых неисправностей: {stats['total_common_issues']}")
