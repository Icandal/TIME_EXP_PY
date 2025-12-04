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
        if speed <= 0 or len(self.points) < 2:
            return 0.0

        frames_count = self.total_length / speed
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
            pygame.draw.circle(screen, (0, 255, 0), start_point, 8)

    def draw_target_zone(self, screen: pygame.Surface) -> None:
        """Рисует целевую зону (последний сегмент)"""
        if len(self.points) >= 2:
            end_point = self.points[-1]
            pygame.draw.circle(screen, (0, 0, 255), end_point, 15)


class TrajectoryManager:
    def __init__(self, trajectories_data: Dict[str, Any]):
        self.trajectories_data = trajectories_data
        self.current_trajectory = None

    def load_trajectory(self, block_name: str, category: str, index: int) -> Trajectory:
        """Загружает траекторию по блоку, категории и индексу"""
        try:
            print(f"🔍 Загрузка траектории: {block_name}/{category}[{index}]")

            if (
                block_name in self.trajectories_data
                and category in self.trajectories_data[block_name]
            ):

                trajectories = self.trajectories_data[block_name][category]
                print(f"📊 Найдено траекторий в категории: {len(trajectories)}")

                # Если траектории пустые - создаем пустую траекторию
                if not trajectories or not isinstance(trajectories, list):
                    print(f"⚠️ Пустые траектории в {block_name}/{category}")
                    self.current_trajectory = Trajectory([])
                    return self.current_trajectory

                if index >= len(trajectories):
                    print(f"⚠️ Индекс {index} вне диапазона (0-{len(trajectories)-1})")
                    self.current_trajectory = Trajectory([])
                    return self.current_trajectory

                points_data = trajectories[index]
                print(f"📐 Тип данных точек: {type(points_data)}")
                print(f"📐 Данные точки: {points_data}")

                points = []

                # ОБРАБОТКА РАЗНЫХ ФОРМАТОВ ДАННЫХ:

                # Формат 1: список точек [{'x': 1, 'y': 2}, {'x': 3, 'y': 4}, ...]
                if isinstance(points_data, list):
                    print("📁 Формат: список точек")
                    for point in points_data:
                        if isinstance(point, dict) and "x" in point and "y" in point:
                            points.append((point["x"], point["y"]))
                        else:
                            print(f"⚠️ Некорректная точка в списке: {point}")

                # Формат 2: одна точка как словарь {'x': 1, 'y': 2}
                elif (
                    isinstance(points_data, dict)
                    and "x" in points_data
                    and "y" in points_data
                ):
                    print("📄 Формат: одиночная точка как словарь")
                    points.append((points_data["x"], points_data["y"]))

                else:
                    print(f"⚠️ Неизвестный формат данных: {type(points_data)}")
                    self.current_trajectory = Trajectory([])
                    return self.current_trajectory

                print(f"✅ Загружено точек: {len(points)}")
                for i, point in enumerate(points):
                    print(f"   Точка {i}: ({point[0]}, {point[1]})")

                self.current_trajectory = Trajectory(points)
                return self.current_trajectory
            else:
                print(f"❌ Блок '{block_name}' или категория '{category}' не найдены")
                self.current_trajectory = Trajectory([])
                return self.current_trajectory

        except Exception as e:
            print(f"❌ Ошибка загрузки траектории: {e}")
            import traceback

            traceback.print_exc()
            self.current_trajectory = Trajectory([])
            return self.current_trajectory

    def draw_current(self, screen: pygame.Surface) -> None:
        """Рисует текущую траекторию (только если есть точки)"""
        if self.current_trajectory and len(self.current_trajectory.points) > 1:
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
        return {"total_length": 0, "point_count": 0, "points": []}

    def has_trajectory(self) -> bool:
        """Проверяет, есть ли загруженная траектория с точками"""
        return (
            self.current_trajectory is not None
            and len(self.current_trajectory.points) >= 2
        )  # Минимум 2 точки для траектории
