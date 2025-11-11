import pygame
from typing import Tuple, List
from enum import Enum

class FixationShape(Enum):
    TRIANGLE = "triangle"
    RHOMBUS = "rhombus"
    STAR = "star"
    CROSS = "cross"
    CIRCLE = "circle"  # Добавляем круг для задач с оценкой времени

class FixationCross:
    def __init__(self, screen_width: int, screen_height: int, shape: FixationShape = FixationShape.TRIANGLE, size: int = 30):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.shape = shape
        self.size = size
        self.color: Tuple[int, int, int] = (0, 0, 0)  # Черный цвет
        
    def set_shape(self, shape: FixationShape) -> None:
        """Устанавливает форму фиксационной точки"""
        self.shape = shape
        
    def set_size(self, size: int) -> None:
        """Устанавливает размер фиксационной точки"""
        self.size = size
        
    def set_color(self, color: Tuple[int, int, int]) -> None:
        """Устанавливает цвет фиксационной точки"""
        self.color = color
        
    def draw(self, screen: pygame.Surface) -> None:
        """Рисует фиксационную точку в центре экрана"""
        center_x = self.screen_width // 2
        center_y = self.screen_height // 2
        
        if self.shape == FixationShape.TRIANGLE:
            self._draw_triangle(screen, center_x, center_y)
        elif self.shape == FixationShape.RHOMBUS:
            self._draw_rhombus(screen, center_x, center_y)
        elif self.shape == FixationShape.STAR:
            self._draw_star(screen, center_x, center_y)
        elif self.shape == FixationShape.CROSS:
            self._draw_cross(screen, center_x, center_y)
        elif self.shape == FixationShape.CIRCLE:
            self._draw_circle(screen, center_x, center_y)  # Добавляем отрисовку круга
    
    
    def _draw_circle(self, screen: pygame.Surface, center_x: int, center_y: int) -> None:
        """Рисует круг"""
        pygame.draw.circle(screen, self.color, (center_x, center_y), self.size)
        pygame.draw.circle(screen, self.color, (center_x, center_y), self.size, 2)  # Обводка


    def _draw_triangle(self, screen: pygame.Surface, center_x: int, center_y: int) -> None:
        """Рисует треугольник"""
        points = [
            (center_x, center_y - self.size),  # Верхняя вершина
            (center_x - self.size, center_y + self.size),  # Левая нижняя
            (center_x + self.size, center_y + self.size)   # Правая нижняя
        ]
        pygame.draw.polygon(screen, self.color, points)
        pygame.draw.polygon(screen, self.color, points, 2)  # Обводка
    
    def _draw_rhombus(self, screen: pygame.Surface, center_x: int, center_y: int) -> None:
        """Рисует ромб"""
        points = [
            (center_x, center_y - self.size),  # Верхняя
            (center_x + self.size, center_y),  # Правая
            (center_x, center_y + self.size),  # Нижняя
            (center_x - self.size, center_y)   # Левая
        ]
        pygame.draw.polygon(screen, self.color, points)
        pygame.draw.polygon(screen, self.color, points, 2)  # Обводка
    
    def _draw_star(self, screen: pygame.Surface, center_x: int, center_y: int) -> None:
        """Рисует звезду"""
        outer_radius = self.size
        inner_radius = self.size // 2
        points = []
        
        for i in range(10):
            angle = 2 * 3.14159 * i / 10 - 3.14159 / 2  # Смещаем чтобы верхний луч был вверху
            radius = outer_radius if i % 2 == 0 else inner_radius
            x = center_x + radius * pygame.math.Vector2(1, 0).rotate(angle * 180 / 3.14159).x
            y = center_y + radius * pygame.math.Vector2(1, 0).rotate(angle * 180 / 3.14159).y
            points.append((x, y))
        
        pygame.draw.polygon(screen, self.color, points)
        pygame.draw.polygon(screen, self.color, points, 2)  # Обводка
    
    def _draw_cross(self, screen: pygame.Surface, center_x: int, center_y: int) -> None:
        """Рисует крест"""
        # Вертикальная линия
        pygame.draw.line(screen, self.color, 
                        (center_x, center_y - self.size),
                        (center_x, center_y + self.size), 
                        3)
        # Горизонтальная линия
        pygame.draw.line(screen, self.color,
                        (center_x - self.size, center_y),
                        (center_x + self.size, center_y),
                        3)