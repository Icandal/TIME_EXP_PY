import pygame
from typing import Tuple


class TimingEstimationScreen:
    def __init__(self, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.is_active = False
        self.background_color = (255, 255, 255)  # Белый фон
        self.circle_color = (0, 0, 0)  # Черный кружок
        self.circle_radius = 15
        self.start_time = 0
        self.space_pressed = False
        self.press_time = 0
        self.actual_duration = 0  # Фактическое время прохождения траектории

    def activate(self, actual_duration: float) -> None:
        """Активирует экран оценки времени"""
        self.is_active = True
        self.space_pressed = False
        self.press_time = 0
        self.actual_duration = actual_duration
        self.start_time = pygame.time.get_ticks()

    def deactivate(self) -> None:
        """Деактивирует экран оценки времени"""
        self.is_active = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Обрабатывает события и возвращает True если пробел нажат"""
        if self.is_active and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE and not self.space_pressed:
                self.space_pressed = True
                self.press_time = pygame.time.get_ticks() - self.start_time
                print(f"Пробел нажат в оценке времени! Время: {self.press_time}мс")
                return True
        return False

    def draw(self, screen: pygame.Surface) -> None:
        """Рисует экран оценки времени"""
        if not self.is_active:
            return

        # Белый фон
        screen.fill(self.background_color)

        # Черный кружок в центре
        center_x = self.screen_width // 2
        center_y = self.screen_height // 2
        pygame.draw.circle(
            screen, self.circle_color, (center_x, center_y), self.circle_radius
        )

        # УБРАНА инструкция "Нажмите ПРОБЕЛ, когда пройдет столько же времени"
        # Просто черный кружок без текста
        # if current_time < 2000:  # Показываем инструкцию 2 секунды
        #     font = pygame.font.Font(None, 36)
        #     instruction_text = font.render(
        #         "Нажмите ПРОБЕЛ, когда пройдет столько же времени", True, (0, 0, 0)
        #     )
        #     text_rect = instruction_text.get_rect(
        #         center=(self.screen_width // 2, self.screen_height - 50)
        #     )
        #     screen.blit(instruction_text, text_rect)

    def get_results(self) -> dict:
        """Возвращает результаты оценки времени"""
        return {
            "actual_duration": self.actual_duration,
            "estimated_duration": self.press_time,
            "estimation_error": self.press_time - self.actual_duration,
            "estimation_error_abs": abs(self.press_time - self.actual_duration),
            "estimation_ratio": (
                self.press_time / self.actual_duration
                if self.actual_duration > 0
                else 0
            ),
        }

    def is_complete(self) -> bool:
        """Проверяет, завершена ли оценка времени"""
        return self.space_pressed
