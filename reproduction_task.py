import pygame
from typing import Tuple, List

class ReproductionTask:
    def __init__(self, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.is_active = False
        
        # Цвета
        self.background_color = (255, 255, 255)  # Белый фон
        self.circle_color = (0, 0, 0)  # Черный кружок
        self.circle_radius = 15
        
        # Состояния задачи
        self.state = "first_stimulus"  # first_stimulus, interval, second_stimulus, response
        self.start_time = 0
        self.first_stimulus_duration = 0
        self.interval_duration = 900  # 900 мс интервал
        self.response_time = 0
        self.space_pressed = False
        
        # Для хранения времени первого стимула (будет браться из траектории)
        self.target_duration = 0
        
    def activate(self, target_duration: float) -> None:
        """Активирует задачу воспроизведения времени"""
        self.is_active = True
        self.state = "first_stimulus"
        self.start_time = pygame.time.get_ticks()
        self.target_duration = target_duration
        self.first_stimulus_duration = target_duration
        self.space_pressed = False
        self.response_time = 0
        
    def deactivate(self) -> None:
        """Деактивирует задачу"""
        self.is_active = False
        
    def handle_event(self, event: pygame.event.Event) -> bool:
        """Обрабатывает события и возвращает True если пробел нажат в фазе ответа"""
        if self.is_active and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE and self.state == "response" and not self.space_pressed:
                self.space_pressed = True
                self.response_time = pygame.time.get_ticks() - (self.start_time + self.first_stimulus_duration + self.interval_duration)
                return True
        return False
        
    def update(self) -> None:
        """Обновляет состояние задачи"""
        if not self.is_active:
            return
            
        current_time = pygame.time.get_ticks() - self.start_time
        
        if self.state == "first_stimulus" and current_time >= self.first_stimulus_duration:
            self.state = "interval"
            
        elif self.state == "interval" and current_time >= self.first_stimulus_duration + self.interval_duration:
            self.state = "response"
    
    def draw(self, screen: pygame.Surface, fixation_cross) -> None:
        """Рисует текущее состояние задачи"""
        if not self.is_active:
            return
            
        # Белый фон
        screen.fill(self.background_color)
        
        current_time = pygame.time.get_ticks() - self.start_time
        
        if self.state == "first_stimulus":
            # Показываем первый стимул (кружок)
            center_x = self.screen_width // 2
            center_y = self.screen_height // 2
            pygame.draw.circle(screen, self.circle_color, (center_x, center_y), self.circle_radius)
            
            # Отображаем инструкцию
            font = pygame.font.Font(None, 36)
            instruction_text = font.render("Запомните длительность показа кружка", True, (0, 0, 0))
            text_rect = instruction_text.get_rect(center=(self.screen_width // 2, self.screen_height - 50))
            screen.blit(instruction_text, text_rect)
            
        elif self.state == "interval":
            # Показываем крестик на время интервала
            fixation_cross.draw(screen)
            
        elif self.state == "response":
            # Показываем второй стимул (кружок) и ждем ответа
            center_x = self.screen_width // 2
            center_y = self.screen_height // 2
            pygame.draw.circle(screen, self.circle_color, (center_x, center_y), self.circle_radius)
            
            # Отображаем инструкцию
            font = pygame.font.Font(None, 36)
            if not self.space_pressed:
                instruction_text = font.render("Нажмите ПРОБЕЛ, когда пройдет столько же времени", True, (0, 0, 0))
                text_rect = instruction_text.get_rect(center=(self.screen_width // 2, self.screen_height - 50))
                screen.blit(instruction_text, text_rect)
            else:
                instruction_text = font.render("Ответ зарегистрирован", True, (0, 0, 0))
                text_rect = instruction_text.get_rect(center=(self.screen_width // 2, self.screen_height - 50))
                screen.blit(instruction_text, text_rect)
    
    def get_results(self) -> dict:
        """Возвращает результаты задачи воспроизведения"""
        return {
            "target_duration": self.target_duration,
            "reproduced_duration": self.response_time,
            "reproduction_error": self.response_time - self.target_duration,
            "reproduction_error_abs": abs(self.response_time - self.target_duration),
            "reproduction_ratio": self.response_time / self.target_duration if self.target_duration > 0 else 0
        }
    
    def is_complete(self) -> bool:
        """Проверяет, завершена ли задача"""
        return self.space_pressed