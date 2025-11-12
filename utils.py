import json
import os
from datetime import datetime
from typing import Dict, Any, List


def load_trajectories(filename: str = "trajectories.json") -> Dict[str, Any]:
    """Загрузка траекторий из JSON файла"""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Файл {filename} не найден!")
        return {}
    except json.JSONDecodeError as e:
        print(f"Ошибка чтения JSON: {e}")
        return {}


def save_experiment_data(
    participant_id: str, block_number: int, data: List[Dict[str, Any]]
) -> str:
    """Сохранение данных эксперимента в JSON файл"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"experiment_data_{participant_id}_block{block_number}_{timestamp}.json"

    experiment_data = {
        "participant_id": participant_id,
        "block_number": block_number,
        "timestamp": timestamp,
        "total_trials": len(data),
        "trials": data,
    }

    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(experiment_data, f, ensure_ascii=False, indent=2)

        print(f"Данные сохранены в файл: {filename}")
        return filename

    except Exception as e:
        print(f"Ошибка при сохранении данных: {e}")
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
