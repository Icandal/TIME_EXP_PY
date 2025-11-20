import pygame
from typing import List, Tuple, Dict, Any


class Trajectory:
    def __init__(self, points: List[Tuple[int, int]]):
        self.points = points
        self.color = (255, 0, 0)  # Красный цвет для траектории
        self.line_width = 2
        self.total_length = self._calculate_total_length()

    def _calculate_total_length(self) -> float:
        """Вычисляет общую длину траектории"""
        if len(self.points) < 2:
            return 0.0

        total_length = 0.0
        for i in range(len(self.points) - 1):
            total_length += self._segment_length(self.points[i], self.points[i + 1])
        return total_length

    def _segment_length(
        self, point1: Tuple[float, float], point2: Tuple[float, float]
    ) -> float:
        """Вычисляет длину сегмента"""
        return ((point2[0] - point1[0]) ** 2 + (point2[1] - point1[1]) ** 2) ** 0.5

    def get_total_length(self) -> float:
        """Возвращает общую длину траектории"""
        return self.total_length

    def calculate_duration(self, speed: float) -> float:
        """Рассчитывает продолжительность движения по траектории в миллисекундах"""
        if speed <= 0:
            return 0.0

        # ИСПРАВЛЕНИЕ: speed уже в px/кадр, поэтому расчет проще
        # Количество кадров = длина / скорость
        frames_count = self.total_length / speed
        # Время в секундах = количество кадров / FPS
        time_seconds = frames_count / 60.0
        return time_seconds * 1000  # мс

    def draw(self, screen: pygame.Surface) -> None:
        """Рисует ломаную линию на экране"""
        if len(self.points) > 1:
            pygame.draw.lines(screen, self.color, False, self.points, self.line_width)

    def draw_start_point(self, screen: pygame.Surface) -> None:
        """Рисует точку старта"""
        if self.points:
            start_point = self.points[0]
            pygame.draw.circle(
                screen, (0, 255, 0), start_point, 8
            )  # Зеленая точка старта

    def draw_target_zone(self, screen: pygame.Surface) -> None:
        """Рисует целевую зону (последний сегмент)"""
        if len(self.points) >= 2:
            end_point = self.points[-1]
            # Простой синий круг радиусом 15 пикселей
            pygame.draw.circle(screen, (0, 0, 255), end_point, 15)


class TrajectoryManager:
    def __init__(self, trajectories_data: Dict[str, Any]):
        self.trajectories_data = trajectories_data
        self.current_trajectory = None

    def load_trajectory(self, category: str, index: int) -> Trajectory:
        """Загружает траекторию по категории и индексу"""
        if category in self.trajectories_data and index < len(
            self.trajectories_data[category]
        ):
            points_data = self.trajectories_data[category][index]
            points = [(point["x"], point["y"]) for point in points_data]
            self.current_trajectory = Trajectory(points)
            return self.current_trajectory
        else:
            raise ValueError(f"Траектория {category}[{index}] не найдена")

    def draw_current(self, screen: pygame.Surface) -> None:
        """Рисует текущую траекторию"""
        if self.current_trajectory:
            self.current_trajectory.draw(screen)
            self.current_trajectory.draw_start_point(screen)
            self.current_trajectory.draw_target_zone(screen)

    def get_current_trajectory_info(self) -> Dict[str, Any]:
        """Возвращает информацию о текущей траектории"""
        if self.current_trajectory:
            return {
                "total_length": self.current_trajectory.get_total_length(),
                "point_count": len(self.current_trajectory.points),
                "points": self.current_trajectory.points,
            }
        return {}

    def get_trajectories_count(self, category: str) -> int:
        """Возвращает количество траекторий в категории"""
        if category in self.trajectories_data:
            return len(self.trajectories_data[category])
        return 0

    def get_available_categories(self) -> List[str]:
        """Возвращает список доступных категорий траекторий"""
        return list(self.trajectories_data.keys())
