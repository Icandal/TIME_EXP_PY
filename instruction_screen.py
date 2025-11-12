import pygame
from typing import Tuple


class InstructionScreen:
    def __init__(self, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.is_active = False
        self.background_color = (240, 240, 240)  # Светло-серый фон
        self.text_color = (0, 0, 0)  # Черный текст
        self.border_color = (100, 100, 100)  # Серая обводка
        self.font_large = pygame.font.Font(None, 48)
        self.font_small = pygame.font.Font(None, 36)

    def activate(self) -> None:
        """Активирует экран с инструкцией"""
        self.is_active = True

    def deactivate(self) -> None:
        """Деактивирует экран с инструкцией"""
        self.is_active = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Обрабатывает события и возвращает True если нужно продолжить"""
        if self.is_active and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self.deactivate()
                return True
        return False

    def set_custom_content(self, title: str, instructions: list[str]) -> None:
        """Устанавливает пользовательское содержимое для инструкции"""
        self.custom_title = title
        self.custom_instructions = instructions

    def draw(self, screen: pygame.Surface) -> None:
        """Рисует экран с инструкцией"""
        if not self.is_active:
            return

        # Полупрозрачный фон поверх всего
        overlay = pygame.Surface(
            (self.screen_width, self.screen_height), pygame.SRCALPHA
        )
        overlay.fill((0, 0, 0, 128))  # Полупрозрачный черный
        screen.blit(overlay, (0, 0))

        # Параметры окна инструкции
        window_width = 1920
        window_height = 1080
        window_x = (self.screen_width - window_width) // 2
        window_y = (self.screen_height - window_height) // 2

        # Рисуем окно
        window_rect = pygame.Rect(window_x, window_y, window_width, window_height)
        pygame.draw.rect(screen, self.background_color, window_rect)
        pygame.draw.rect(screen, self.border_color, window_rect, 3)

        # Текст инструкции
        instruction_text = self.font_large.render(
            "Нажмите ПРОБЕЛ чтобы продолжить", True, self.text_color
        )
        text_rect = instruction_text.get_rect(
            center=(self.screen_width // 2, self.screen_height // 2 - 20)
        )
        screen.blit(instruction_text, text_rect)
