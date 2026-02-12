"""
Интеграционный модуль для связи систем:
- Системы заявок (lift-repair-tickets) - порт 8081
- Складской системы (warehouse-management) - порт 8080
- Базы знаний - порт 8082
"""

import requests
import sqlite3
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from knowledge_db import KnowledgeBaseDB


class IntegrationManager:
    """Менеджер интеграции между системами"""
    
    def __init__(self):
        self.kb_db = KnowledgeBaseDB()
        self.tickets_base_url = "http://localhost:8081"
        self.warehouse_base_url = "http://localhost:8080"
        self.kb_base_url = "http://localhost:8082"
    
    # ======== Интеграция Заявки ↔ Склад ========
    
    def check_parts_availability(self, parts_list: List[str]) -> Dict:
        """
        Проверка наличия запчастей на складе
        
        Args:
            parts_list: список артикулов запчастей
            
        Returns:
            Словарь с результатами проверки
        """
        try:
            results = {}
            for article in parts_list:
                response = requests.get(
                    f"{self.warehouse_base_url}/api/products/{article}",
                    timeout=5
                )
                if response.status_code == 200:
                    product = response.json()
                    results[article] = {
                        'available': product.get('quantity', 0) > 0,
                        'quantity': product.get('quantity', 0),
                        'name': product.get('name', ''),
                        'location': product.get('location', {})
                    }
                else:
                    results[article] = {
                        'available': False,
                        'quantity': 0,
                        'error': 'Not found'
                    }
            return results
        except requests.exceptions.ConnectionError:
            return {'error': 'Warehouse system unavailable'}
        except Exception as e:
            return {'error': str(e)}
    
    def reserve_parts_for_ticket(self, ticket_id: int, parts: Dict[str, int]) -> Dict:
        """
        Резервирование запчастей для заявки
        
        Args:
            ticket_id: ID заявки
            parts: словарь {артикул: количество}
            
        Returns:
            Результат резервирования
        """
        try:
            # Проверяем наличие
            availability = self.check_parts_availability(list(parts.keys()))
            
            reserved = []
            not_available = []
            
            for article, qty in parts.items():
                if article in availability and availability[article].get('available', False):
                    if availability[article]['quantity'] >= qty:
                        # Здесь можно добавить логику резервирования в БД склада
                        reserved.append({
                            'article': article,
                            'quantity': qty,
                            'ticket_id': ticket_id
                        })
                    else:
                        not_available.append({
                            'article': article,
                            'requested': qty,
                            'available': availability[article]['quantity']
                        })
                else:
                    not_available.append({
                        'article': article,
                        'requested': qty,
                        'available': 0
                    })
            
            return {
                'success': len(not_available) == 0,
                'reserved': reserved,
                'not_available': not_available
            }
        except Exception as e:
            return {'error': str(e)}
    
    def consume_parts_for_ticket(self, ticket_id: int, parts: Dict[str, int]) -> Dict:
        """
        Списание запчастей по выполненной заявке
        
        Args:
            ticket_id: ID заявки
            parts: словарь {артикул: количество}
            
        Returns:
            Результат списания
        """
        try:
            consumed = []
            errors = []
            
            for article, qty in parts.items():
                # Обновляем количество на складе через API
                response = requests.put(
                    f"{self.warehouse_base_url}/api/products/{article}/stock",
                    json={'quantity_actual': f"-{qty}"},  # Уменьшаем на qty
                    timeout=5
                )
                
                if response.status_code == 200:
                    consumed.append({'article': article, 'quantity': qty})
                else:
                    errors.append({
                        'article': article,
                        'error': f'Failed to consume: {response.status_code}'
                    })
            
            return {
                'success': len(errors) == 0,
                'ticket_id': ticket_id,
                'consumed': consumed,
                'errors': errors
            }
        except requests.exceptions.ConnectionError:
            return {'error': 'Warehouse system unavailable'}
        except Exception as e:
            return {'error': str(e)}
    
    def get_parts_recommendations(self, problem_description: str) -> List[Dict]:
        """
        Получение рекомендаций по запчастям на основе описания проблемы
        
        Args:
            problem_description: описание проблемы
            
        Returns:
            Список рекомендуемых запчастей
        """
        # Ищем похожие решения в базе знаний
        solutions = self.kb_db.find_solutions_for_ticket(problem_description)
        
        recommendations = []
        for solution in solutions[:3]:  # Берем топ-3 решения
            parts_used = solution.get('parts_used', [])
            if parts_used:
                # Проверяем наличие на складе
                availability = self.check_parts_availability(parts_used)
                
                recommendations.append({
                    'solution_title': solution['title'],
                    'knowledge_id': solution['id'],
                    'parts': [
                        {
                            'article': article,
                            'available': availability.get(article, {}).get('available', False),
                            'quantity': availability.get(article, {}).get('quantity', 0),
                            'name': availability.get(article, {}).get('name', '')
                        }
                        for article in parts_used
                    ]
                })
        
        return recommendations
    
    # ======== Интеграция Заявки ↔ База знаний ========
    
    def get_ticket_context(self, ticket_id: int) -> Dict:
        """
        Получение контекста для заявки из базы знаний
        
        Args:
            ticket_id: ID заявки
            
        Returns:
            Контекст заявки с рекомендациями
        """
        try:
            # Получаем информацию о заявке
            response = requests.get(
                f"{self.tickets_base_url}/api/tickets/{ticket_id}",
                timeout=5
            )
            
            if response.status_code != 200:
                return {'error': 'Ticket not found'}
            
            ticket = response.json()
            
            # Ищем похожие решения
            similar_solutions = self.kb_db.find_solutions_for_ticket(
                ticket.get('problem_description', ''),
                ticket.get('elevator_model')
            )
            
            # Получаем историю объекта если есть
            object_history = []
            if ticket.get('address'):
                # Ищем объект по адресу
                conn = self.kb_db.get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT id FROM objects WHERE address = ?',
                    (ticket['address'],)
                )
                row = cursor.fetchone()
                conn.close()
                
                if row:
                    object_history = self.kb_db.get_object_history(row['id'], limit=5)
            
            return {
                'ticket': ticket,
                'similar_solutions': similar_solutions,
                'object_history': object_history
            }
        except requests.exceptions.ConnectionError:
            return {'error': 'Ticket system unavailable'}
        except Exception as e:
            return {'error': str(e)}
    
    def suggest_solutions_for_ticket(self, ticket_id: int) -> Dict:
        """
        Предложение решений для заявки
        
        Args:
            ticket_id: ID заявки
            
        Returns:
            Предложенные решения с запчастями
        """
        context = self.get_ticket_context(ticket_id)
        
        if 'error' in context:
            return context
        
        ticket = context['ticket']
        
        # Получаем рекомендации по запчастям
        parts_recommendations = self.get_parts_recommendations(
            ticket.get('problem_description', '')
        )
        
        # Связываем заявку с найденными решениями
        for solution in context['similar_solutions'][:3]:
            self.kb_db.link_ticket_to_knowledge(
                ticket_id,
                solution['id'],
                solution.get('relevance_score', 0.0)
            )
        
        return {
            'ticket_id': ticket_id,
            'solutions': context['similar_solutions'],
            'parts_recommendations': parts_recommendations,
            'object_history': context['object_history']
        }
    
    def create_knowledge_from_ticket(self, ticket_id: int, solution_data: Dict) -> Dict:
        """
        Создание статьи базы знаний из закрытой заявки
        
        Args:
            ticket_id: ID заявки
            solution_data: данные решения
            
        Returns:
            Результат создания
        """
        try:
            # Получаем информацию о заявке
            response = requests.get(
                f"{self.tickets_base_url}/api/tickets/{ticket_id}",
                timeout=5
            )
            
            if response.status_code != 200:
                return {'error': 'Ticket not found'}
            
            ticket = response.json()
            
            # Формируем данные для статьи
            article_data = {
                'category': solution_data.get('category', 'решение'),
                'title': solution_data.get(
                    'title',
                    f"Решение: {ticket.get('problem_description', 'Без описания')[:50]}"
                ),
                'content': solution_data.get('content', ticket.get('problem_description', '')),
                'equipment_type': ticket.get('elevator_type'),
                'manufacturer': ticket.get('manufacturer'),
                'model': ticket.get('elevator_model'),
                'symptoms': [ticket.get('problem_description', '')],
                'solution': solution_data.get('solution_text', ''),
                'parts_used': list(solution_data.get('parts_used', {}).keys()),
                'difficulty_level': solution_data.get('difficulty_level', 3),
                'estimated_time': solution_data.get('estimated_time'),
                'tags': solution_data.get('tags', [])
            }
            
            # Создаем статью
            article_id = self.kb_db.create_knowledge_article(article_data)
            
            # Связываем заявку с созданной статьей
            self.kb_db.link_ticket_to_knowledge(ticket_id, article_id, 1.0)
            
            return {
                'success': True,
                'article_id': article_id,
                'message': 'Knowledge article created successfully'
            }
        except Exception as e:
            return {'error': str(e)}
    
    # ======== Статистика и отчеты ========
    
    def get_integration_statistics(self) -> Dict:
        """Получение статистики интеграции"""
        try:
            # Получаем статистику из базы знаний
            kb_stats = self.kb_db.get_statistics()
            
            # Пытаемся получить статистику из системы заявок
            tickets_stats = {}
            try:
                # Получаем список заявок для статистики
                response = requests.get(
                    f"{self.tickets_base_url}/api/tickets",
                    timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    tickets_stats = {
                        'total_tickets': data.get('count', 0),
                        'status': 'online'
                    }
                else:
                    tickets_stats = {'status': 'error', 'code': response.status_code}
            except:
                tickets_stats = {'status': 'offline'}
            
            # Пытаемся получить статистику из склада
            warehouse_stats = {}
            try:
                response = requests.get(
                    f"{self.warehouse_base_url}/api/stats",
                    timeout=5
                )
                if response.status_code == 200:
                    warehouse_stats = response.json()
            except:
                pass
            
            return {
                'knowledge_base': kb_stats,
                'tickets': tickets_stats,
                'warehouse': warehouse_stats
            }
        except Exception as e:
            return {'error': str(e)}
    
    def generate_maintenance_report(self, object_id: int, date_from: Optional[str] = None,
                                   date_to: Optional[str] = None) -> Dict:
        """
        Генерация отчета по обслуживанию объекта
        
        Args:
            object_id: ID объекта
            date_from: дата начала периода
            date_to: дата окончания периода
            
        Returns:
            Отчет по обслуживанию
        """
        # Получаем историю обслуживания
        history = self.kb_db.get_object_history(object_id)
        
        if date_from:
            history = [h for h in history if h['date'] >= date_from]
        if date_to:
            history = [h for h in history if h['date'] <= date_to]
        
        # Считаем статистику
        total_visits = len(history)
        total_duration = sum(h.get('duration', 0) or 0 for h in history)
        total_cost = sum(float(h.get('cost', 0) or 0) for h in history)
        
        # Группируем по типам работ
        work_types = {}
        for h in history:
            work_type = h.get('work_type', 'unknown')
            work_types[work_type] = work_types.get(work_type, 0) + 1
        
        return {
            'object_id': object_id,
            'period': {
                'from': date_from,
                'to': date_to
            },
            'summary': {
                'total_visits': total_visits,
                'total_duration_hours': round(total_duration / 60, 2),
                'total_cost': round(total_cost, 2),
                'average_visit_duration': round(total_duration / total_visits, 2) if total_visits > 0 else 0
            },
            'work_types': work_types,
            'history': history
        }


# ======== Вспомогательные функции ========

def get_integration_manager() -> IntegrationManager:
    """Фабрика для получения экземпляра менеджера интеграции"""
    return IntegrationManager()


if __name__ == "__main__":
    # Тестирование интеграции
    manager = get_integration_manager()
    
    print("🔌 Тестирование интеграционного модуля")
    print("=" * 50)
    
    # Проверка статистики
    stats = manager.get_integration_statistics()
    print("\n📊 Статистика:")
    print(f"   Статьей в БЗ: {stats.get('knowledge_base', {}).get('total_articles', 0)}")
    print(f"   Объектов: {stats.get('knowledge_base', {}).get('total_objects', 0)}")
