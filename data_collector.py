import pygame
from typing import Dict, Any, List, Optional
from datetime import datetime

class DataCollector:
    def __init__(self, participant_id: str, block_number: int):
        self.participant_id = participant_id  # Идентификатор испытуемого (строка)
        self.block_number = block_number      # Номер текущего блока (целое число)
        self.current_trial_data: Dict[str, Any] = {}  # Данные текущей попытки
        self.all_trials_data: List[Dict[str, Any]] = []  # Все собранные данные
        self.trial_number = 0                 # Счетчик попыток
        
    def start_new_trial(self, trajectory_type: str, duration: float, speed: float, 
                       trajectory_number: int, condition_type: str, 
                       block_number: int, trial_in_block: int, display_order: int,
                       assigned_speed: float, assigned_duration: int) -> None:
        """Начинает запись данных для новой попытки"""
        self.trial_number += 1
        self.current_trial_data = {
            # Основная информация о попытке
            "trial_number": self.trial_number,                    # Номер попытки в эксперименте (целое число)
            "block_number": block_number,                         # Номер блока (целое число)
            "trial_in_block": trial_in_block,                     # Номер попытки в блоке (целое число)
            "display_order": display_order,                       # Порядок показа в блоке после перемешивания (целое число)
            
            # Информация о траектории
            "trajectory_type": trajectory_type,                   # Категория траектории (строка: "T", "H1", и т.д.)
            "duration": duration,                                 # Расчетная длительность траектории в мс (число с плавающей точкой)
            "speed": speed,                                       # Расчетная скорость точки в px/кадр (число с плавающей точкой)
            "assigned_speed": assigned_speed,                     # Назначенная скорость из конфига (число с плавающей точкой или None)
            "assigned_duration": assigned_duration,               # Назначенная длительность из конфига (целое число или None)
            "trajectory_number": trajectory_number,               # Индекс траектории в категории (целое число)
            "condition_type": condition_type,                     # Тип условия (строка: "occlusion_half", "no_occlusion", и т.д.)
            
            # Временные метки
            "start_time": pygame.time.get_ticks(),                # Время начала попытки в мс (целое число)
            "movement_start_time": None,                          # Время начала движения точки в мс (целое число или None)
            "stimulus_start_time": None,                          # Время начала предъявления стимула в мс (целое число или None)
            "movement_end_time": None,                            # Время окончания движения точки в мс (целое число или None)
            "occlusion_start_time": None,                         # Время начала окклюзии в мс (целое число или None)
            
            # Эталонные времена (для анализа)
            "reference_response_time": None,                      # Эталонное время до цели в мс (число с плавающей точкой или None)
            "stimulus_presentation_time": None,                   # Время предъявления стимула в мс (число с плавающей точкой или None)
            "trajectory_completion_time": None,                   # Время завершения траектории в мс (число с плавающей точкой или None)
            
            # Времена реакции
            "actual_response_time_movement": None,                # Фактическое время от движения до ответа в мс (целое число или None)
            "actual_response_time_stimulus": None,                # Фактическое время от стимула до ответа в мс (целое число или None)
            "space_press_time": None,                             # Время нажатия пробела в мс (целое число или None)
            "reaction_time": None,                                # Общее время реакции в мс (целое число или None)
            
            # Флаги состояния
            "stopped_by_user": False,                             # Остановлена ли точка пользователем (булево)
            "completed_normally": False,                          # Завершена ли попытка нормально (булево)
            
            # Дополнительные данные
            "actual_trajectory_duration": None,                   # Фактическое время прохождения траектории в мс (целое число или None)
            "timing_estimation": None,                            # Результаты оценки времени (словарь или None)
            "reproduction_results": None,                         # Результаты воспроизведения времени (словарь или None)
            "occlusion_zone": None                                # Информация о зоне окклюзии (словарь или None)
        }
    
    def record_movement_start(self) -> None:
        """Записывает время начала движения"""
        self.current_trial_data["movement_start_time"] = pygame.time.get_ticks()  # Текущее время в мс
    
    def record_stimulus_start(self) -> None:
        """Записывает время начала предъявления стимула"""
        self.current_trial_data["stimulus_start_time"] = pygame.time.get_ticks()  # Текущее время в мс
    
    def record_movement_end(self) -> None:
        """Записывает время окончания движения"""
        self.current_trial_data["movement_end_time"] = pygame.time.get_ticks()  # Текущее время в мс
    
    def record_space_press(self, stopped_by_user: bool = True) -> None:
        """Записывает время нажатия пробела"""
        current_time = pygame.time.get_ticks()  # Текущее время в мс
        self.current_trial_data["space_press_time"] = current_time
        self.current_trial_data["stopped_by_user"] = stopped_by_user  # Булево значение
        
        # Вычисляем время реакции
        if self.current_trial_data["movement_start_time"]:
            self.current_trial_data["actual_response_time_movement"] = (
                current_time - self.current_trial_data["movement_start_time"]  # Разница во времени в мс
            )
        
        if self.current_trial_data["stimulus_start_time"]:
            self.current_trial_data["actual_response_time_stimulus"] = (
                current_time - self.current_trial_data["stimulus_start_time"]  # Разница во времени в мс
            )
        
        self.current_trial_data["reaction_time"] = (
            current_time - self.current_trial_data["movement_start_time"]
            if self.current_trial_data["movement_start_time"] else None  # Разница во времени в мс или None
        )
    
    def record_reference_times(self, movement_to_target: float, stimulus_presentation: float, 
                              trajectory_completion: float) -> None:
        """Записывает эталонные времена"""
        self.current_trial_data["reference_response_time"] = movement_to_target        # Число с плавающей точкой (мс)
        self.current_trial_data["stimulus_presentation_time"] = stimulus_presentation  # Число с плавающей точкой (мс)
        self.current_trial_data["trajectory_completion_time"] = trajectory_completion  # Число с плавающей точкой (мс)
    
    def record_timing_estimation(self, timing_results: dict) -> None:
        """Записывает результаты оценки времени"""
        # timing_results: словарь с ключами:
        # - "actual_duration": фактическое время в мс (число)
        # - "estimated_duration": оцененное время в мс (число) 
        # - "estimation_error": ошибка оценки в мс (число)
        # - "estimation_error_abs": абсолютная ошибка в мс (число)
        # - "estimation_ratio": отношение оцененного к фактическому (число с плавающей точкой)
        self.current_trial_data["timing_estimation"] = timing_results
    
    def record_reproduction_results(self, reproduction_results: dict) -> None:
        """Записывает результаты воспроизведения времени"""
        # reproduction_results: словарь с ключами:
        # - "target_duration": целевая длительность в мс (число)
        # - "reproduced_duration": воспроизведенная длительность в мс (число)
        # - "reproduction_error": ошибка воспроизведения в мс (число)
        # - "reproduction_error_abs": абсолютная ошибка в мс (число)
        # - "reproduction_ratio": отношение воспроизведенного к целевому (число с плавающей точкой)
        self.current_trial_data["reproduction_results"] = reproduction_results
    
    def record_trajectory_duration(self, actual_duration: float) -> None:
        """Записывает фактическое время прохождения траектории"""
        self.current_trial_data["actual_trajectory_duration"] = actual_duration  # Число с плавающей точкой (мс)
    
    def complete_trial(self, completed_normally: bool = False) -> None:
        """Завершает запись попытки"""
        self.current_trial_data["completed_normally"] = completed_normally  # Булево значение
        if completed_normally and not self.current_trial_data["movement_end_time"]:
            self.current_trial_data["movement_end_time"] = pygame.time.get_ticks()  # Текущее время в мс
        
        # Добавляем попытку в общий список
        self.all_trials_data.append(self.current_trial_data.copy())
        
        # Выводим информацию о попытке в консоль
        self._print_trial_summary()
    
    def _print_trial_summary(self) -> None:
        """Выводит сводку по завершенной попытке"""
        trial = self.current_trial_data
        print(f"\n=== Попытка {trial['trial_number']} завершена ===")
        print(f"Траектория: {trial['trajectory_type']}[{trial['trajectory_number']}]")
        print(f"Условие: {trial['condition_type']}")
        
        if trial['reaction_time']:
            print(f"Время реакции: {trial['reaction_time']}мс")
        
        if trial['stopped_by_user']:
            print("Остановлено пользователем")
        else:
            print("Завершено автоматически")
        
        if trial['actual_response_time_movement']:
            print(f"Время от движения до ответа: {trial['actual_response_time_movement']}мс")
        
        if trial['actual_response_time_stimulus']:
            print(f"Время от стимула до ответа: {trial['actual_response_time_stimulus']}мс")
        
        # Добавляем информацию об оценке времени, если она есть
        if trial.get('timing_estimation'):
            timing = trial['timing_estimation']
            print(f"Оценка времени:")
            print(f"  Фактическое время: {timing['actual_duration']}мс")
            print(f"  Оцененное время: {timing['estimated_duration']}мс")
            print(f"  Ошибка: {timing['estimation_error']}мс")
            print(f"  Абсолютная ошибка: {timing['estimation_error_abs']}мс")
            print(f"  Отношение: {timing['estimation_ratio']:.2f}")
        
        # Добавляем информацию о воспроизведении времени, если она есть
        if trial.get('reproduction_results'):
            reproduction = trial['reproduction_results']
            print(f"Воспроизведение времени:")
            print(f"  Целевая длительность: {reproduction['target_duration']}мс")
            print(f"  Воспроизведенная длительность: {reproduction['reproduced_duration']}мс")
            print(f"  Ошибка: {reproduction['reproduction_error']}мс")
            print(f"  Абсолютная ошибка: {reproduction['reproduction_error_abs']}мс")
            print(f"  Отношение: {reproduction['reproduction_ratio']:.2f}")
    
    def get_all_data(self) -> List[Dict[str, Any]]:
        """Возвращает все собранные данные"""
        return self.all_trials_data  # Список словарей с данными всех попыток
    
    def get_current_trial_number(self) -> int:
        """Возвращает номер текущей попытки"""
        return self.trial_number  # Целое число
    
    def reset_block(self, new_block_number: int) -> None:
        """Сбрасывает данные для нового блока"""
        self.block_number = new_block_number  # Целое число
        self.all_trials_data = []             # Очищаем список данных
        self.trial_number = 0                 # Сбрасываем счетчик
        self.current_trial_data = {}          # Очищаем текущие данные

    def record_occlusion_start(self, moving_point) -> None:
        """Записывает время начала окклюзии и информацию о зоне"""
        current_time = pygame.time.get_ticks()  # Текущее время в мс
        self.current_trial_data["occlusion_start_time"] = current_time
        
        # Записываем информацию о зоне окклюзии
        occlusion_info = moving_point.get_occlusion_info()  # Словарь с информацией об окклюзии
        self.current_trial_data["occlusion_zone"] = {
            "start_segment": occlusion_info["start_segment"],      # Номер сегмента начала (целое число)
            "start_progress": occlusion_info["start_progress"],    # Прогресс в сегменте начала (число с плавающей точкой)
            "end_segment": occlusion_info["end_segment"],          # Номер сегмента окончания (целое число)
            "end_progress": occlusion_info["end_progress"]         # Прогресс в сегменте окончания (число с плавающей точкой)
        }