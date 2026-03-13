"""
Интеграция с OpenRouter AI для умного поиска в базе знаний
"""

import os
import json
import requests
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

class OpenRouterAI:
    """Клиент для работы с OpenRouter API"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        self.base_url = "https://openrouter.ai/api/v1"
        self.model = os.getenv('OPENROUTER_MODEL', 'meta-llama/llama-3.1-8b-instruct:free')
        
        if not self.api_key:
            raise ValueError("OpenRouter API key not found. Set OPENROUTER_API_KEY environment variable.")
    
    def search_knowledge_intelligent(self, query: str, articles: List[Dict]) -> Dict:
        """
        Интеллектуальный поиск по базе знаний с помощью AI
        
        Args:
            query: Запрос пользователя
            articles: Список статей для анализа
            
        Returns:
            AI-анализ с рекомендациями
        """
        # Формируем контекст из статей
        context = self._format_articles_context(articles)
        
        prompt = f"""Ты - эксперт по ремонту лифтового оборудования. 
Проанализируй запрос пользователя и предоставленные статьи из базы знаний.

ЗАПРОС ПОЛЬЗОВАТЕЛЯ:
{query}

ДОСТУПНЫЕ СТАТЬИ ИЗ БАЗЫ ЗНАНИЙ:
{context}

Проанализируй:
1. Какие статьи наиболее релевантны запросу (перечисли ID)
2. Какое решение рекомендуешь
3. Какие запчасти могут понадобиться
4. Оцени сложность работы (1-5)
5. Оцени время ремонта

Ответь в формате JSON:
{{
    "relevant_article_ids": [1, 2, 3],
    "recommended_solution": "описание решения",
    "parts_needed": ["артикул1", "артикул2"],
    "difficulty_level": 3,
    "estimated_time_minutes": 60,
    "additional_notes": "дополнительные рекомендации"
}}"""

        try:
            response = self._chat_completion(prompt)
            # Пытаемся распарсить JSON из ответа
            result = self._extract_json(response)
            return {
                'success': True,
                'ai_analysis': result,
                'raw_response': response
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'raw_response': response if 'response' in locals() else None
            }
    
    def analyze_problem(self, problem_description: str) -> Dict:
        """
        Анализ проблемы с лифтом и рекомендации
        
        Args:
            problem_description: Описание проблемы
            
        Returns:
            Анализ проблемы
        """
        prompt = f"""Ты - опытный техник по обслуживанию лифтов. 
Проанализируй описание проблемы и дай профессиональную оценку.

ОПИСАНИЕ ПРОБЛЕМЫ:
{problem_description}

Проанализируй:
1. Возможные причины (перечисли 3-5)
2. Вероятность каждой причины (%)
3. Необходимые проверки и диагностика
4. Категория сложности (простая/средняя/сложная)
5. Приоритет (низкий/средний/высокий/критический)
6. Необходимые инструменты
7. Меры безопасности

Ответь в формате JSON:
{{
    "possible_causes": [
        {{"cause": "описание", "probability": 80}}
    ],
    "diagnostic_steps": ["шаг 1", "шаг 2"],
    "difficulty": "средняя",
    "priority": "высокий",
    "tools_needed": ["инструмент 1", "инструмент 2"],
    "safety_notes": "меры безопасности",
    "estimated_time": "1-2 часа"
}}"""

        try:
            response = self._chat_completion(prompt)
            result = self._extract_json(response)
            return {
                'success': True,
                'analysis': result,
                'raw_response': response
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def suggest_parts(self, problem_description: str, elevator_model: str = None) -> Dict:
        """
        Рекомендации по запчастям на основе проблемы
        
        Args:
            problem_description: Описание проблемы
            elevator_model: Модель лифта (опционально)
            
        Returns:
            Список рекомендуемых запчастей
        """
        model_info = f"\nМОДЕЛЬ ЛИФТА: {elevator_model}" if elevator_model else ""
        
        prompt = f"""Ты - складской менеджер лифтовой компании.
На основе описания проблемы рекомендуй необходимые запчасти.

ОПИСАНИЕ ПРОБЛЕМЫ:
{problem_description}
{model_info}

Рекомендуй запчасти в формате JSON:
{{
    "parts": [
        {{
            "name": "название запчасти",
            "category": "категория",
            "urgency": "обязательно/рекомендуется/опционально",
            "estimated_price_range": "1000-2000 руб",
            "notes": "примечания"
        }}
    ],
    "alternative_solutions": ["альтернатива 1", "альтернатива 2"],
    "total_estimate": "примерная стоимость"
}}"""

        try:
            response = self._chat_completion(prompt)
            result = self._extract_json(response)
            return {
                'success': True,
                'parts_recommendation': result,
                'raw_response': response
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _chat_completion(self, prompt: str, temperature: float = 0.7) -> str:
        """Отправка запроса к OpenRouter API"""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': os.getenv('OPENROUTER_HTTP_REFERER', 'https://localhost'),
            'X-Title': os.getenv('OPENROUTER_APP_NAME', 'LiftRepairKnowledgeBase')
        }
        
        data = {
            'model': self.model,
            'messages': [
                {'role': 'user', 'content': prompt}
            ],
            'temperature': temperature,
            'max_tokens': 2000
        }
        
        response = requests.post(
            f'{self.base_url}/chat/completions',
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"API Error: {response.status_code} - {response.text}")
        
        result = response.json()
        return result['choices'][0]['message']['content']
    
    def _format_articles_context(self, articles: List[Dict]) -> str:
        """Форматирование статей для контекста"""
        context_parts = []
        for article in articles:
            context_parts.append(f"""
СТАТЬЯ ID: {article.get('id')}
Название: {article.get('title')}
Категория: {article.get('category')}
Оборудование: {article.get('equipment_type', 'N/A')}
Производитель: {article.get('manufacturer', 'N/A')}
Симптомы: {', '.join(article.get('symptoms', []))}
Решение: {article.get('solution', 'N/A')[:200]}...
""")
        return '\n---\n'.join(context_parts)
    
    def _extract_json(self, text: str) -> Dict:
        """Извлечение JSON из ответа AI"""
        # Ищем JSON в блоке кода
        import re
        
        # Пробуем найти JSON в ```json ... ```
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        
        # Пробуем найти JSON в ``` ... ```
        json_match = re.search(r'```\s*(\{.*?)\s*```', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        
        # Пробуем найти JSON напрямую
        json_match = re.search(r'(\{.*\})', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        
        raise ValueError("JSON not found in response")


# Пример использования
if __name__ == "__main__":
    try:
        ai = OpenRouterAI()
        
        # Тест анализа проблемы
        result = ai.analyze_problem("Лифт не вызывается с первого этажа, кнопка не светится")
        print("AI Analysis:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"Error: {e}")
