import pygame
from typing import Tuple, List


class InstructionScreen:
    def __init__(self, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.is_active = False
        self.background_color = (240, 240, 240)  # Светло-серый фон
        self.text_color = (0, 0, 0)  # Черный текст

        # Адаптивные размеры шрифтов
        base_font_size = max(24, min(screen_width, screen_height) // 40)
        self.font_large = pygame.font.Font(None, int(base_font_size * 2))
        self.font_medium = pygame.font.Font(None, int(base_font_size * 1.5))
        self.font_small = pygame.font.Font(None, base_font_size)

        # Пользовательское содержимое
        self.custom_title = ""
        self.custom_instructions = []

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

    def set_custom_content(self, title: str, instructions: List[str]) -> None:
        """Устанавливает пользовательское содержимое для инструкции"""
        self.custom_title = title
        self.custom_instructions = instructions

    def draw(self, screen: pygame.Surface) -> None:
        """Рисует экран с инструкцией - полноэкранный режим"""
        if not self.is_active:
            return

        # Полностью заполняем экран фоном инструкции
        screen.fill(self.background_color)

        # Отступы от краев экрана
        padding = min(self.screen_width, self.screen_height) // 20

        # Если установлено пользовательское содержимое, рисуем его
        if hasattr(self, "custom_title") and self.custom_title:
            self._draw_custom_content(screen, padding)
        else:
            self._draw_default_content(screen)

    def _draw_custom_content(self, screen: pygame.Surface, padding: int) -> None:
        """Рисует пользовательское содержимое инструкции на весь экран"""
        current_y = padding

        # Заголовок
        if self.custom_title:
            title_lines = self._wrap_text(
                self.custom_title, self.font_large, self.screen_width - 2 * padding
            )
            for line in title_lines:
                title_surface = self.font_large.render(line, True, self.text_color)
                title_rect = title_surface.get_rect(
                    center=(self.screen_width // 2, current_y)
                )
                screen.blit(title_surface, title_rect)
                current_y += title_surface.get_height() + padding

        current_y += padding  # Дополнительный отступ после заголовка

        # Инструкции
        for instruction in self.custom_instructions:
            if instruction.strip() == "":
                current_y += padding  # Пустая строка - дополнительный отступ
                continue

            instruction_lines = self._wrap_text(
                instruction, self.font_small, self.screen_width - 2 * padding
            )
            for line in instruction_lines:
                instruction_surface = self.font_small.render(
                    line, True, self.text_color
                )
                instruction_rect = instruction_surface.get_rect(
                    midleft=(padding, current_y)
                )
                screen.blit(instruction_surface, instruction_rect)
                current_y += instruction_surface.get_height() + (padding // 2)

        # Инструкция для продолжения (внизу экрана)
        continue_text = "Нажмите ПРОБЕЛ чтобы продолжить"
        continue_surface = self.font_medium.render(continue_text, True, self.text_color)
        continue_rect = continue_surface.get_rect(
            center=(self.screen_width // 2, self.screen_height - padding * 2)
        )
        screen.blit(continue_surface, continue_rect)

    def _draw_default_content(self, screen: pygame.Surface) -> None:
        """Рисует содержимое инструкции по умолчанию на весь экран"""
        # Текст инструкции по центру экрана
        instruction_text = "Нажмите ПРОБЕЛ чтобы продолжить"
        instruction_surface = self.font_large.render(
            instruction_text, True, self.text_color
        )
        instruction_rect = instruction_surface.get_rect(
            center=(self.screen_width // 2, self.screen_height // 2)
        )
        screen.blit(instruction_surface, instruction_rect)

    def _wrap_text(
        self, text: str, font: pygame.font.Font, max_width: int
    ) -> List[str]:
        """Переносит текст по словам, чтобы он помещался в указанную ширину"""
        words = text.split(" ")
        lines = []
        current_line = []

        for word in words:
            # Проверяем ширину текущей строки с добавленным словом
            test_line = " ".join(current_line + [word])
            test_surface = font.render(test_line, True, self.text_color)

            if test_surface.get_width() <= max_width:
                current_line.append(word)
            else:
                if current_line:  # Если текущая строка не пустая, добавляем ее
                    lines.append(" ".join(current_line))
                current_line = [word]  # Начинаем новую строку с текущим словом

        # Добавляем последнюю строку
        if current_line:
            lines.append(" ".join(current_line))

        return lines
