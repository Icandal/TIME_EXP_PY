import pygame
from typing import Tuple
from fixation import FixationCross, FixationShape


class ReproductionTask:
    def __init__(self, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.is_active = False

        # Цвета
        self.background_color = (255, 255, 255)
        self.circle_color = (0, 0, 0)
        self.circle_radius = 15

        # Состояния задачи
        self.state = "inactive"
        self.state_start_time = 0
        self.target_duration = 0
        self.response_time = 0
        self.space_pressed = False

        # Время для крестиков (фиксированное)
        self.cross_duration = 900  # 900 мс

        # Создаем свой крестик
        self.fixation_cross = FixationCross(
            screen_width, screen_height, FixationShape.CROSS, size=30
        )
        self.fixation_cross.set_color((0, 0, 0))

    def activate(self, target_duration: int) -> None:
        """Активирует задачу воспроизведения времени"""
        self.is_active = True
        self.state = "first_cross"
        self.state_start_time = pygame.time.get_ticks()
        self.target_duration = target_duration
        self.space_pressed = False
        self.response_time = 0
        
        print(f"=== АКТИВАЦИЯ ЗАДАЧИ ВОСПРОИЗВЕДЕНИЯ ===")
        print(f"Целевая длительность: {target_duration}мс")
        print(f"Начальное состояние: {self.state}")

    def deactivate(self) -> None:
        """Деактивирует задачу"""
        self.is_active = False
        self.state = "inactive"
        print("Задача воспроизведения деактивирована")

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Обрабатывает события и возвращает True если задача завершена"""
        if not self.is_active:
            return False

        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            if self.state == "response" and not self.space_pressed:
                self.space_pressed = True
                self.response_time = pygame.time.get_ticks() - self.state_start_time
                print(f"Ответ зарегистрирован: {self.response_time}мс")
                return True
                
        return False

    def update(self) -> None:
        """Обновляет состояние задачи - автоматические переходы"""
        if not self.is_active:
            return

        current_time = pygame.time.get_ticks()
        elapsed_time = current_time - self.state_start_time

        # Автоматические переходы между состояниями
        if self.state == "first_cross":
            if elapsed_time >= self.cross_duration:
                self.state = "first_circle"
                self.state_start_time = current_time
                print(f"Переход: first_cross → first_circle")

        elif self.state == "first_circle":
            if elapsed_time >= self.target_duration:
                self.state = "second_cross"
                self.state_start_time = current_time
                print(f"Переход: first_circle → second_cross")

        elif self.state == "second_cross":
            if elapsed_time >= self.cross_duration:
                self.state = "response"
                self.state_start_time = current_time
                print(f"Переход: second_cross → response")

    def draw(self, screen: pygame.Surface, fixation_cross) -> None:
        """Рисует текущее состояние задачи"""
        if not self.is_active:
            return

        # Полностью очищаем экран
        screen.fill(self.background_color)

        if self.state == "first_cross":
            # Первый крестик (900 мс)
            self.fixation_cross.draw(screen)

        elif self.state == "first_circle":
            # Первый кружок для запоминания времени
            center_x = self.screen_width // 2
            center_y = self.screen_height // 2
            pygame.draw.circle(screen, self.circle_color, (center_x, center_y), self.circle_radius)

        elif self.state == "second_cross":
            # Второй крестик (900 мс)
            self.fixation_cross.draw(screen)

        elif self.state == "response":
            # Второй кружок для ответа
            center_x = self.screen_width // 2
            center_y = self.screen_height // 2
            pygame.draw.circle(screen, self.circle_color, (center_x, center_y), self.circle_radius)

            # Инструкция для пользователя
            if not self.space_pressed:
                font = pygame.font.Font(None, 36)
                instruction = font.render(
                    "Нажмите ПРОБЕЛ, когда пройдет столько же времени", 
                    True, (0, 0, 0)
                )
                text_rect = instruction.get_rect(
                    center=(self.screen_width // 2, self.screen_height - 50)
                )
                screen.blit(instruction, text_rect)

    def get_results(self) -> dict:
        """Возвращает результаты задачи"""
        return {
            "target_duration": self.target_duration,
            "reproduced_duration": self.response_time,
            "reproduction_error": self.response_time - self.target_duration,
            "reproduction_error_abs": abs(self.response_time - self.target_duration),
            "reproduction_ratio": (
                self.response_time / self.target_duration 
                if self.target_duration > 0 else 0
            ),
        }

    def is_complete(self) -> bool:
        """Проверяет, завершена ли задача"""
        return self.space_pressed
    
