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
        self.target_duration = 0  # Декодированное время
        self.response_time = 0
        self.space_pressed = False

        # Задержка перед началом (200 или 400 мс)
        self.start_delays = [200, 400]
        self.start_delay = 0
        self.in_start_delay = False
        self.delay_start_time = 0

        # Создаем свой крестик
        self.fixation_cross = FixationCross(
            screen_width, screen_height, FixationShape.CROSS, size=30
        )
        self.fixation_cross.set_color((0, 0, 0))

    def activate(self, target_duration: int) -> None:
        """Активирует задачу воспроизведения времени"""
        self.is_active = True
        
        # Начинаем с первого крестика, который ждет пробела
        self.state = "first_cross_waiting"
        self.state_start_time = pygame.time.get_ticks()
        
        self.target_duration = target_duration
        self.space_pressed = False
        self.response_time = 0
        self.in_start_delay = False
        self.start_delay = 0

        print(f"=== АКТИВАЦИЯ ЗАДАЧИ ВОСПРОИЗВЕДЕНИЯ ===")
        print(f"Целевая длительность: {target_duration}мс")
        print(f"Начальное состояние: {self.state}")

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Обрабатывает события и возвращает True если задача завершена"""
        if not self.is_active:
            return False

        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            if self.state == "first_cross_waiting":
                # Начинаем задержку 200/400 мс
                import random
                self.start_delay = random.choice(self.start_delays)
                self.delay_start_time = pygame.time.get_ticks()
                self.state = "in_start_delay"
                print(f"Начата задержка: {self.start_delay}мс")
                
            elif self.state == "second_cross_waiting":
                # Переход от второго крестика к ответу
                self.state = "response_waiting"
                self.state_start_time = pygame.time.get_ticks()
                print(f"Переход: second_cross_waiting → response_waiting")
                
            elif self.state == "response_waiting" and not self.space_pressed:
                # Финальный ответ
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

        # Проверка завершения задержки 200/400 мс
        if self.state == "in_start_delay":
            if current_time - self.delay_start_time >= self.start_delay:
                # После задержки - круг на декодированное время (автоматически)
                self.state = "first_circle_auto"
                self.state_start_time = current_time
                self.in_start_delay = False
                print(f"Задержка завершена, начинается круг на {self.target_duration}мс")

        # Автоматический переход от круга ко второму крестику
        elif self.state == "first_circle_auto":
            elapsed_time = current_time - self.state_start_time
            if elapsed_time >= self.target_duration:
                self.state = "second_cross_waiting"
                self.state_start_time = current_time
                print(f"Круг завершен, показан второй крестик (ждет пробела)")

    def draw(self, screen: pygame.Surface, fixation_cross) -> None:
        """Рисует текущее состояние задачи"""
        if not self.is_active:
            return

        # Полностью очищаем экран
        screen.fill(self.background_color)

        if self.state == "first_cross_waiting":
            # Первый крестик (ждать пробел) - С ИНСТРУКЦИЕЙ
            self.fixation_cross.draw(screen)
            
            # Инструкция
            font = pygame.font.Font(None, 36)
            instruction = font.render(
                "Нажмите ПРОБЕЛ чтобы начать", True, (0, 0, 0)
            )
            text_rect = instruction.get_rect(
                center=(self.screen_width // 2, self.screen_height - 50)
            )
            screen.blit(instruction, text_rect)

        elif self.state == "in_start_delay":
            # Во время задержки просто крестик (без инструкции)
            self.fixation_cross.draw(screen)
            
            # БЕЗ инструкции "нажмите пробел"
            # Просто крестик

        elif self.state == "first_circle_auto":
            # Круг на декодированное время (автоматически)
            center_x = self.screen_width // 2
            center_y = self.screen_height // 2
            pygame.draw.circle(
                screen, self.circle_color, (center_x, center_y), self.circle_radius
            )
            
            # БЕЗ инструкции - круг показывается автоматически

        elif self.state == "second_cross_waiting":
            # Второй крестик (ждать пробел) - С НОВОЙ ИНСТРУКЦИЕЙ
            self.fixation_cross.draw(screen)
            
            # ДОБАВЛЯЕМ инструкцию для второго крестика
            font = pygame.font.Font(None, 36)
            instruction = font.render(
                "Нажмите ПРОБЕЛ, когда будете готовы", True, (0, 0, 0)
            )
            text_rect = instruction.get_rect(
                center=(self.screen_width // 2, self.screen_height - 50)
            )
            screen.blit(instruction, text_rect)

        elif self.state == "response_waiting":
            # Круг для ответа (ждать пробел) - С ИНСТРУКЦИЕЙ
            center_x = self.screen_width // 2
            center_y = self.screen_height // 2
            pygame.draw.circle(
                screen, self.circle_color, (center_x, center_y), self.circle_radius
            )

            # Инструкция для пользователя
            if not self.space_pressed:
                font = pygame.font.Font(None, 36)
                instruction = font.render(
                    "Нажмите ПРОБЕЛ, когда пройдет столько же времени", True, (0, 0, 0)
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
                if self.target_duration > 0
                else 0
            ),
            "start_delay": self.start_delay,  # Добавляем информацию о задержке
        }

    def deactivate(self) -> None:
        """Деактивирует задачу"""
        self.is_active = False
        self.state = "inactive"
        print("Задача воспроизведения деактивирована")

    def is_complete(self) -> bool:
        """Проверяет, завершена ли задача"""
        return self.space_pressed