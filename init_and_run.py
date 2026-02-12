#!/usr/bin/env python3
"""
Скрипт инициализации и запуска базы знаний
"""

import subprocess
import sys
import os
from pathlib import Path

def check_dependencies():
    """Проверка установленных зависимостей"""
    print("📦 Проверка зависимостей...")
    try:
        import flask
        import flask_cors
        import requests
        print("✅ Все зависимости установлены")
        return True
    except ImportError as e:
        print(f"⚠️ Отсутствует модуль: {e}")
        print("Установите зависимости: pip install -r requirements.txt")
        return False

def init_database():
    """Инициализация базы данных"""
    print("\n🗄️ Инициализация базы данных...")
    try:
        from knowledge_db import KnowledgeBaseDB
        db = KnowledgeBaseDB()
        print("✅ База данных инициализирована")
        return True
    except Exception as e:
        print(f"❌ Ошибка инициализации БД: {e}")
        return False

def seed_data():
    """Заполнение базы начальными данными"""
    print("\n🌱 Заполнение базы данных...")
    try:
        from seed_data import seed_database
        seed_database()
        return True
    except Exception as e:
        print(f"❌ Ошибка заполнения данных: {e}")
        return False

def start_servers():
    """Запуск серверов"""
    print("\n🚀 Запуск системы базы знаний...")
    print("=" * 60)
    print("📚 База знаний будет доступна по адресам:")
    print("   Веб-интерфейс: http://localhost:8082")
    print("   API: http://localhost:8082/api/")
    print("=" * 60)
    print("\nДля остановки нажмите Ctrl+C\n")
    
    try:
        from knowledge_base import app
        app.run(debug=True, host='0.0.0.0', port=8082)
    except KeyboardInterrupt:
        print("\n\n🛑 Сервер остановлен")
    except Exception as e:
        print(f"\n❌ Ошибка запуска сервера: {e}")

def show_menu():
    """Показать меню выбора"""
    print("\n" + "=" * 60)
    print("🎛️  БАЗА ЗНАНИЙ - МЕНЮ УПРАВЛЕНИЯ")
    print("=" * 60)
    print("1. Полная инициализация (создать БД + заполнить данными)")
    print("2. Только инициализация базы данных")
    print("3. Только запуск сервера")
    print("4. Проверить статус системы")
    print("5. Выход")
    print("=" * 60)

def check_status():
    """Проверка статуса системы"""
    print("\n🔍 Проверка статуса системы...")
    
    # Проверка базы данных
    if os.path.exists('knowledge_base.db'):
        print("✅ Файл базы данных существует")
        try:
            from knowledge_db import KnowledgeBaseDB
            db = KnowledgeBaseDB()
            stats = db.get_statistics()
            print(f"   📊 Статистика БД:")
            print(f"      - Статей: {stats['total_articles']}")
            print(f"      - Объектов: {stats['total_objects']}")
            print(f"      - Типовых неисправностей: {stats['total_common_issues']}")
        except Exception as e:
            print(f"⚠️ Ошибка чтения БД: {e}")
    else:
        print("❌ Файл базы данных не найден")
    
    # Проверка зависимостей
    try:
        import flask
        import flask_cors
        import requests
        print("✅ Все зависимости установлены")
    except ImportError as e:
        print(f"⚠️ Отсутствует зависимость: {e}")

def main():
    """Главная функция"""
    print("\n🏗️  БАЗА ЗНАНИЙ ОРГАНИЗАЦИИ ПО РЕМОНТУ ЛИФТОВ")
    print("=" * 60)
    print("📦 Система интегрирует:")
    print("   • Систему заявок (порт 8081)")
    print("   • Складское управление (порт 8080)")
    print("   • Базу знаний (порт 8082)")
    print("=" * 60)
    
    while True:
        show_menu()
        choice = input("\nВыберите действие (1-5): ").strip()
        
        if choice == '1':
            # Полная инициализация
            if not check_dependencies():
                print("\n⚠️ Сначала установите зависимости!")
                continue
            
            if init_database():
                seed_data()
                input("\n✅ Инициализация завершена. Нажмите Enter для запуска сервера...")
                start_servers()
            break
            
        elif choice == '2':
            # Только инициализация
            if check_dependencies() and init_database():
                print("\n✅ База данных инициализирована")
            
        elif choice == '3':
            # Только запуск
            if check_dependencies():
                start_servers()
            break
            
        elif choice == '4':
            # Проверка статуса
            check_status()
            
        elif choice == '5':
            print("\n👋 До свидания!")
            break
            
        else:
            print("\n❌ Неверный выбор. Попробуйте снова.")

if __name__ == "__main__":
    main()
