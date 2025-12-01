import json
import os
from datetime import datetime
from typing import Dict, Any, List


def load_trajectories(filename: str = "traj_lib.json") -> Dict[str, Any]:
    """Загрузка траекторий из JSON файла с сохранением структуры блоков"""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        print("=" * 60)
        print("ЗАГРУЖЕНЫ ТРАЕКТОРИИ С БЛОКАМИ:")
        print("=" * 60)
        
        # Просто возвращаем данные как есть, сохраняя структуру блоков
        for block_name in sorted(data.keys()):
            trajectories_count = sum(len(trajs) for trajs in data[block_name].values())
            print(f"📦 {block_name}: {trajectories_count} траекторий")
            
        return data
            
    except FileNotFoundError:
        print(f"Файл {filename} не найден!")
        return {}
    except json.JSONDecodeError as e:
        print(f"Ошибка чтения JSON: {e}")
        return {}


def save_experiment_data(
    participant_id: str, block_number: int, data: List[Dict[str, Any]]
) -> str:
    """Сохраняет данные эксперимента в JSON файл"""
    try:
        # Создаем имя файла с временной меткой
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"data/{participant_id}_block_{block_number}_{timestamp}.json"
        
        # Создаем структуру данных
        experiment_data = {
            "participant_id": participant_id,
            "block_number": block_number,
            "export_timestamp": timestamp,
            "export_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_trials": len(data),
            "trials": data
        }
        
        # Сохраняем в файл
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(experiment_data, f, ensure_ascii=False, indent=2)
        
        return filename
    except Exception as e:
        print(f"❌ Ошибка сохранения данных: {e}")
        # Пытаемся сохранить в альтернативное место
        try:
            alt_filename = f"experiment_data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(alt_filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return alt_filename
        except Exception as e2:
            print(f"💥 Критическая ошибка сохранения: {e2}")
            return ""


def get_current_time() -> float:
    """Получение текущего времени в миллисекундах"""
    return pygame.time.get_ticks() if "pygame" in globals() else 0


def format_time(milliseconds: float) -> str:
    """Форматирование времени из миллисекунд в строку"""
    seconds = milliseconds / 1000.0
    return f"{seconds:.3f}"


# Проверяем, доступен ли pygame для функций времени
try:
    import pygame
except ImportError:
    print("Pygame не установлен, некоторые функции utils.py могут не работать")
