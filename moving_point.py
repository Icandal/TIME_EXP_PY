# moving_point.py
import pygame
from typing import List, Tuple, Dict, Any
from trajectory import Trajectory

class MovingPoint:
    def __init__(self, trajectory: Trajectory, speed: float = 5.0, occlusion_type: str = "half"):
        self.trajectory = trajectory
        self.speed = speed  # пикселей в кадр
        self.current_segment = 0
        self.progress = 0.0  # прогресс по текущему сегменту (0.0 - 1.0)
        self.current_position = trajectory.points[0] if trajectory.points else (0, 0)
        self.is_moving = True
        self.is_finished = False
        self.finished_timer = 0
        self.finished_delay = 900  # мс
        self.stopped_by_user = False
        
        # Настройки скрытия точки
        self.occlusion_enabled = True
        self.occlusion_type = occlusion_type  # "half" или "third"
        self.occlusion_start_segment = 0
        self.occlusion_start_progress = 0.0
        self.occlusion_end_segment = 0
        self.occlusion_end_progress = 1.0
        self.is_visible = True
        
        # Автоматическая настройка окклюдера
        self._setup_automatic_occlusion()
        
    def set_occlusion_type(self, occlusion_type: str) -> None:
        """Устанавливает тип окклюзии: 'half' (половина) или 'third' (треть)"""
        self.occlusion_type = occlusion_type
        self._setup_automatic_occlusion()
        
    def _setup_automatic_occlusion(self) -> None:
        """Автоматически настраивает окклюдер в зависимости от типа"""
        total_segments = len(self.trajectory.points) - 1
        if total_segments <= 0:
            return
            
        # Определяем точку начала окклюзии в зависимости от типа
        if self.occlusion_type == "half":
            occlusion_start_progress = 0.5  # Начинаем с половины траектории
        else:  # "third"
            occlusion_start_progress = 2.0 / 3.0  # Начинаем с 2/3 траектории
        
        # Находим сегмент и прогресс для начала окклюзии
        self.occlusion_start_segment, self.occlusion_start_progress = (
            self._find_segment_and_progress(occlusion_start_progress)
        )
        
        # Окклюзия продолжается до конца траектории
        self.occlusion_end_segment = total_segments - 1
        self.occlusion_end_progress = 1.0
        
        # Включаем окклюзию по умолчанию
        self.occlusion_enabled = True
        
    def _find_segment_and_progress(self, target_progress: float) -> Tuple[int, float]:
        """Находит сегмент и прогресс для заданного общего прогресса по траектории"""
        if not self.trajectory.points or len(self.trajectory.points) < 2:
            return (0, 0.0)
            
        total_length = self.trajectory.total_length
        target_length = total_length * target_progress
        
        current_length = 0.0
        for segment in range(len(self.trajectory.points) - 1):
            segment_length = self._segment_length(
                self.trajectory.points[segment], 
                self.trajectory.points[segment + 1]
            )
            
            if current_length + segment_length >= target_length:
                # Нашли нужный сегмент
                progress_on_segment = (target_length - current_length) / segment_length
                return (segment, progress_on_segment)
            
            current_length += segment_length
        
        # Если не нашли (должно быть в последнем сегменте)
        return (len(self.trajectory.points) - 2, 1.0)
    
    def set_occlusion_zone(self, start_segment: int, start_progress: float, 
                          end_segment: int, end_progress: float) -> None:
        """Устанавливает зону скрытия точки"""
        self.occlusion_enabled = True
        self.occlusion_start_segment = start_segment
        self.occlusion_start_progress = start_progress
        self.occlusion_end_segment = end_segment
        self.occlusion_end_progress = end_progress
        
    def disable_occlusion(self) -> None:
        """Отключает скрытие точки"""
        self.occlusion_enabled = False
        self.is_visible = True
    
    def update(self, dt: float) -> None:
        """Обновляет позицию точки и видимость"""
        if not self.is_moving or self.is_finished:
            return
            
        points = self.trajectory.points
        if self.current_segment >= len(points) - 1:
            self.finish_movement()
            return
        
        # Обновляем видимость
        self._update_visibility()
            
        # Движение по сегменту
        start_point = points[self.current_segment]
        end_point = points[self.current_segment + 1]
        
        # Вычисляем новую позицию
        self.progress += self.speed / self._segment_length(start_point, end_point)
        
        if self.progress >= 1.0:
            # Переходим к следующему сегменту
            self.current_segment += 1
            self.progress = 0.0
            
            if self.current_segment >= len(points) - 1:
                self.finish_movement()
                return
                
            # Обновляем точки для нового сегмента
            start_point = points[self.current_segment]
            end_point = points[self.current_segment + 1]
        
        # Интерполяция позиции
        self.current_position = self._interpolate_points(start_point, end_point, self.progress)
    
    def _update_visibility(self) -> None:
        """Обновляет видимость точки на основе зоны скрытия"""
        if not self.occlusion_enabled:
            self.is_visible = True
            return
            
        current_pos = (self.current_segment, self.progress)
        occlusion_start = (self.occlusion_start_segment, self.occlusion_start_progress)
        occlusion_end = (self.occlusion_end_segment, self.occlusion_end_progress)
        
        # Проверяем, находится ли точка в зоне скрытия
        if self._is_position_in_range(current_pos, occlusion_start, occlusion_end):
            self.is_visible = False
        else:
            self.is_visible = True
    
    def _is_position_in_range(self, current: Tuple[int, float], 
                            start: Tuple[int, float], end: Tuple[int, float]) -> bool:
        """Проверяет, находится ли текущая позиция в заданном диапазоне"""
        current_segment, current_progress = current
        start_segment, start_progress = start
        end_segment, end_progress = end
        
        # Если текущий сегмент до начала зоны скрытия
        if current_segment < start_segment:
            return False
            
        # Если текущий сегмент после конца зоны скрытия
        if current_segment > end_segment:
            return False
            
        # Если текущий сегмент совпадает с начальным
        if current_segment == start_segment:
            if current_progress < start_progress:
                return False
                
        # Если текущий сегмент совпадает с конечным
        if current_segment == end_segment:
            if current_progress > end_progress:
                return False
                
        return True
    
    def finish_movement(self) -> None:
        """Завершает движение точки"""
        self.is_moving = False
        self.is_finished = True
        self.finished_timer = pygame.time.get_ticks()
        # Устанавливаем позицию на последней точке
        self.current_position = self.trajectory.points[-1]
        # Гарантируем, что точка видима в конце
        self.is_visible = True
    
    def stop_by_user(self) -> None:
        """Останавливает точку по команде пользователя"""
        if self.is_moving and not self.is_finished:
            self.is_moving = False
            self.is_finished = True
            self.finished_timer = pygame.time.get_ticks()
            self.stopped_by_user = True
            # Гарантируем, что точка видима после остановки
            self.is_visible = True
    
    def should_switch_to_next(self) -> bool:
        """Проверяет, нужно ли переключаться на следующую траекторию"""
        if self.is_finished:
            current_time = pygame.time.get_ticks()
            return current_time - self.finished_timer >= self.finished_delay
        return False
    
    def draw(self, screen: pygame.Surface) -> None:
        """Рисует движущуюся точку (если она видима)"""
        if self.trajectory.points and self.is_visible:
            color = (255, 0, 0)  # Красная точка
            radius = 8
            
            # Если остановлена пользователем - другой цвет
            if self.stopped_by_user:
                color = (255, 165, 0)  # Оранжевый
            
            pygame.draw.circle(screen, color, 
                             (int(self.current_position[0]), int(self.current_position[1])), 
                             radius)
    
    def _segment_length(self, point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
        """Вычисляет длину сегмента"""
        return ((point2[0] - point1[0])**2 + (point2[1] - point1[1])**2)**0.5
    
    def _interpolate_points(self, point1: Tuple[float, float], point2: Tuple[float, float], 
                          progress: float) -> Tuple[float, float]:
        """Интерполирует позицию между двумя точками"""
        x = point1[0] + (point2[0] - point1[0]) * progress
        y = point1[1] + (point2[1] - point1[1]) * progress
        return (x, y)
    
    def reset(self, new_trajectory: Trajectory) -> None:
        """Сбрасывает точку для новой траектории"""
        self.trajectory = new_trajectory
        self.current_segment = 0
        self.progress = 0.0
        self.current_position = new_trajectory.points[0] if new_trajectory.points else (0, 0)
        self.is_moving = True
        self.is_finished = False
        self.finished_timer = 0
        self.stopped_by_user = False
        # Сбрасываем настройки скрытия и настраиваем автоматический окклюдер
        self.occlusion_enabled = True
        self.is_visible = True
        self._setup_automatic_occlusion()
    
    def get_occlusion_info(self) -> Dict[str, Any]:
        """Возвращает информацию о настройках окклюзии"""
        return {
            "enabled": self.occlusion_enabled,
            "type": self.occlusion_type,
            "start_segment": self.occlusion_start_segment,
            "start_progress": self.occlusion_start_progress,
            "end_segment": self.occlusion_end_segment,
            "end_progress": self.occlusion_end_progress,
            "is_visible": self.is_visible
        }