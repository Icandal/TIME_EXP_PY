import pygame
from typing import Dict, Any


class BlockSummaryScreen:
    """Экран сводки по завершенному блоку"""

    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        data_collector,
        current_block,
        block_number: int,
    ):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.data_collector = data_collector
        self.current_block = current_block
        self.block_number = block_number
        self.is_active = False

        # Цвета
        self.background_color = (255, 255, 255)
        self.text_color = (0, 0, 0)
        self.highlight_color = (50, 150, 255)
        self.input_color = (200, 230, 255)
        self.cursor_color = (0, 0, 0)
        self.placeholder_color = (150, 150, 150)

        # Шрифты - будем создавать их сразу
        self.title_font = self._create_safe_font(48)
        self.text_font = self._create_safe_font(32)
        self.input_font = self._create_safe_font(36)

        # Данные точности
        self.accuracy_score = 0

        # Ввод ответа о длительности
        self.duration_input = ""
        self.input_active = True
        self.input_rect = None
        self.cursor_visible = True
        self.cursor_timer = 0
        self.cursor_blink_interval = 500

        # Защита от дублирования ввода
        self.last_key_pressed = None
        self.last_key_time = 0
        self.key_repeat_delay = 200  # 200ms задержка между нажатиями одной клавиши
        self.key_debounce_time = 50  # 50ms защита от дребезга

        # Состояние
        self.state = "showing_score"
        self.completed = False

    def _create_safe_font(self, size):
        """Создает гарантированно работающий шрифт"""
        # ВАЖНО: Не используем pygame.font.Font(None, size) - он может вернуть None

        # Способ 1: Пробуем создать шрифт через SysFont
        font_names = [
            "arial",
            "tahoma",
            "verdana",
            "helvetica",
            "couriernew",
            "freesans",
            "freeserif",
            "dejavusans",
        ]

        for font_name in font_names:
            try:
                font = pygame.font.SysFont(font_name, size)
                # Проверяем, что шрифт создан и работает
                if font:
                    test_surface = font.render("Test", True, (0, 0, 0))
                    if test_surface and test_surface.get_width() > 0:
                        return font
            except:
                continue

        # Способ 2: Если SysFont не сработал, создаем собственный класс шрифта
        # который НИКОГДА не вернет None
        print(f"Создаем безопасный шрифт размера {size}")
        return self._create_fallback_font(size)

    def _create_fallback_font(self, size):
        """Создает шрифт-заглушку который гарантированно работает"""

        class SafeFont:
            def __init__(self, size):
                self.size = size
                self.char_width = size // 2
                self.char_height = size

            def render(self, text, antialias, color):
                try:
                    # Пробуем создать настоящий шрифт
                    font = pygame.font.Font(pygame.font.get_default_font(), self.size)
                    if font:
                        result = font.render(text, antialias, color)
                        if result:
                            return result
                except:
                    pass

                # Если не получилось, создаем простую поверхность
                width = max(len(text) * self.char_width, 10)
                height = self.char_height
                surface = pygame.Surface((width, height), pygame.SRCALPHA)

                # Заполняем прозрачным цветом
                surface.fill((255, 255, 255, 0))

                return surface

            def get_height(self):
                return self.char_height

        return SafeFont(size)

    def activate(self):
        """Активирует экран сводки"""
        self.is_active = True
        self.state = "showing_score"
        self.completed = False

        # Расчет точности
        self.calculate_accuracy()

        # Настройка поля ввода
        self.setup_input_field()

        # Таймер для курсора
        self.cursor_timer = pygame.time.get_ticks()

        # Сбрасываем защиту от дублирования
        self.last_key_pressed = None
        self.last_key_time = pygame.time.get_ticks()

        print(f"=== СВОДКА БЛОКА {self.block_number} ===")
        print(f"Точность: {self.accuracy_score:.1f}%")
        print("Нажмите ПРОБЕЛ чтобы продолжить")

    def deactivate(self):
        """Деактивирует экран сводки"""
        self.is_active = False
        self.completed = False
        self.duration_input = ""

    def calculate_accuracy(self):
        """Рассчитывает точность ответов в блоке"""
        trials_data = self.data_collector.get_all_data()

        if not trials_data:
            self.accuracy_score = 0
            return

        total_score = 0
        for trial in trials_data:
            trial_score = self.calculate_trial_accuracy(trial)
            total_score += trial_score

        self.accuracy_score = total_score / len(trials_data) if trials_data else 0

    def calculate_trial_accuracy(self, trial: Dict[str, Any]) -> float:
        """Упрощенный расчет точности"""
        condition_type = trial.get("condition_type", "")

        if "occlusion" in condition_type or "timing_estimation" in condition_type:
            if trial.get("stopped_by_user", False):
                actual_time = trial.get("actual_trajectory_duration", 0)
                reference_time = trial.get("reference_response_time", 1)
                if reference_time > 0:
                    actual_position = min(actual_time / reference_time, 1.0)
                    accuracy = 1.0 - abs(actual_position - 1.0)
                    return max(0.0, accuracy * 100)
            return 100.0
        elif "reproduction" in condition_type:
            reproduction_data = trial.get("reproduction_results")
            if reproduction_data:
                target = reproduction_data.get("target_duration", 0)
                reproduced = reproduction_data.get("reproduced_duration", 0)
                if target > 0:
                    accuracy = 1.0 - abs(reproduced - target) / target
                    return max(0.0, accuracy * 100)
        return 0.0

    def setup_input_field(self):
        """Настраивает поле ввода"""
        input_width = 400
        input_height = 50
        input_x = self.screen_width // 2 - input_width // 2
        input_y = self.screen_height // 2 + 30

        self.input_rect = pygame.Rect(input_x, input_y, input_width, input_height)
        self.input_active = True
        self.duration_input = ""
        self.cursor_visible = True

    def handle_event(self, event) -> bool:
        """Обрабатывает события с защитой от дублирования"""
        current_time = pygame.time.get_ticks()

        # Мигание курсора
        if current_time - self.cursor_timer > self.cursor_blink_interval:
            self.cursor_visible = not self.cursor_visible
            self.cursor_timer = current_time

        if event.type == pygame.KEYDOWN:
            current_time = pygame.time.get_ticks()

            # Проверяем, не слишком ли быстро повторяется нажатие
            time_since_last_key = current_time - self.last_key_time

            # Защита от дребезга - игнорируем события слишком близкие по времени
            if time_since_last_key < self.key_debounce_time:
                return False

            # Для повторяющихся нажатий одной клавиши - дополнительная задержка
            if (
                event.key == self.last_key_pressed
                and time_since_last_key < self.key_repeat_delay
            ):
                return False

            # Обновляем время и клавишу
            self.last_key_time = current_time
            self.last_key_pressed = event.key

            if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                # Переход между состояниями или завершение
                if self.state == "showing_score":
                    self.state = "asking_duration"
                    self.input_active = True
                    self.cursor_visible = True
                    self.cursor_timer = current_time
                    print("Введите время в секундах и нажмите ENTER")
                    return False
                elif self.state == "asking_duration" and self.duration_input:
                    self.completed = True
                    return True

            elif event.key == pygame.K_ESCAPE:
                if self.state == "asking_duration":
                    self.duration_input = "пропущено"
                    self.completed = True
                    return True

            elif self.state == "asking_duration" and self.input_active:
                # Обработка ввода текста
                if event.key == pygame.K_BACKSPACE:
                    self.duration_input = self.duration_input[:-1]
                    self.cursor_visible = True
                    self.cursor_timer = current_time
                    return False  # Не завершаем, просто обрабатываем

                elif event.unicode and len(event.unicode) > 0:
                    # Проверяем, что символ допустим
                    char = event.unicode
                    if char.isdigit() or char in [".", ","]:
                        if len(self.duration_input) < 10:
                            self.duration_input += char
                            self.cursor_visible = True
                            self.cursor_timer = current_time
                    return False  # Не завершаем, просто обрабатываем ввод

        elif event.type == pygame.KEYUP:
            # Сбрасываем last_key_pressed при отпускании клавиши
            # Это помогает с повторными нажатиями
            if event.key == self.last_key_pressed:
                self.last_key_pressed = None

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.state == "asking_duration" and self.input_rect:
                self.input_active = self.input_rect.collidepoint(event.pos)
                if self.input_active:
                    self.cursor_visible = True
                    self.cursor_timer = current_time

        return False

    def get_duration_response(self) -> Dict[str, Any]:
        """Возвращает ответ пользователя"""
        return {
            "block_number": self.block_number,
            "block_name": self.current_block.name if self.current_block else "Unknown",
            "perceived_duration": self.duration_input,
            "accuracy_score": self.accuracy_score,
            "timestamp": pygame.time.get_ticks(),
        }

    def draw(self, screen: pygame.Surface):
        """Рисует экран сводки"""
        if not self.is_active:
            return

        screen.fill(self.background_color)

        if self.state == "showing_score":
            self.draw_score_screen(screen)
        elif self.state == "asking_duration":
            self.draw_duration_question_screen(screen)

    def draw_score_screen(self, screen: pygame.Surface):
        """Рисует экран с баллом точности"""
        # Заголовок - БЕЗОПАСНО используем шрифт
        title_text = f"Блок {self.block_number} завершен"
        title_surface = self.title_font.render(title_text, True, self.text_color)
        # Проверяем что surface создана
        if title_surface:
            screen.blit(
                title_surface,
                (self.screen_width // 2 - title_surface.get_width() // 2, 100),
            )
        else:
            # Резервный вариант - рисуем прямоугольник
            pygame.draw.rect(
                screen,
                self.highlight_color,
                (self.screen_width // 2 - 150, 100, 300, 50),
                2,
            )

        # Балл точности
        score_text = f"Ваша точность: {self.accuracy_score:.1f}%"
        score_surface = self.text_font.render(score_text, True, self.highlight_color)
        if score_surface:
            screen.blit(
                score_surface,
                (self.screen_width // 2 - score_surface.get_width() // 2, 200),
            )
        else:
            pygame.draw.rect(
                screen,
                self.highlight_color,
                (self.screen_width // 2 - 100, 200, 200, 40),
            )

        # Пояснение
        explanation_lines = [
            "Точность рассчитывается как процент от правильного выполнения задач в блоке",

            "Нажмите ПРОБЕЛ для продолжения",
        ]

        y_offset = 280
        for line in explanation_lines:
            text_surface = self.text_font.render(line, True, self.text_color)
            if text_surface:
                screen.blit(
                    text_surface,
                    (self.screen_width // 2 - text_surface.get_width() // 2, y_offset),
                )
            y_offset += 35

    def draw_duration_question_screen(self, screen: pygame.Surface):
        """Рисует экран с вопросом о длительности блока"""
        # Заголовок
        title_text = "Вопрос о восприятии времени"
        title_surface = self.title_font.render(title_text, True, self.text_color)
        if title_surface:
            screen.blit(
                title_surface,
                (self.screen_width // 2 - title_surface.get_width() // 2, 100),
            )
        else:
            pygame.draw.rect(
                screen,
                self.highlight_color,
                (self.screen_width // 2 - 150, 100, 300, 50),
                2,
            )

        # Вопрос
        question = "Как вы оцениваете длительность только что завершенного блока?"
        question_surface = self.text_font.render(question, True, self.text_color)
        if question_surface:
            screen.blit(
                question_surface,
                (self.screen_width // 2 - question_surface.get_width() // 2, 180),
            )
        else:
            pygame.draw.rect(
                screen, self.text_color, (self.screen_width // 2 - 250, 180, 500, 40), 2
            )

        # Инструкции по вводу
        instructions = [
            "Введите вашу оценку в секундах (например: 45.5)",
            "или нажмите ESC чтобы пропустить этот вопрос",
        ]

        y_offset = 230
        for line in instructions:
            text_surface = self.text_font.render(line, True, self.text_color)
            if text_surface:
                screen.blit(
                    text_surface,
                    (self.screen_width // 2 - text_surface.get_width() // 2, y_offset),
                )
            y_offset += 35

        # Поле ввода
        if self.input_rect:
            border_color = (
                self.highlight_color if self.input_active else self.text_color
            )
            border_width = 3 if self.input_active else 2

            # Фон поля
            pygame.draw.rect(screen, self.input_color, self.input_rect, border_radius=5)
            pygame.draw.rect(
                screen, border_color, self.input_rect, border_width, border_radius=5
            )

            # Текст в поле ввода
            if self.duration_input:
                input_surface = self.input_font.render(
                    self.duration_input, True, self.text_color
                )
            else:
                input_surface = self.input_font.render(
                    "введите время...", True, self.placeholder_color
                )

            if input_surface:
                text_width = input_surface.get_width()
                max_width = self.input_rect.width - 30

                if text_width <= max_width:
                    text_x = self.input_rect.x + 15
                else:
                    text_x = self.input_rect.x + self.input_rect.width - text_width - 15

                text_y = (
                    self.input_rect.y
                    + (self.input_rect.height - input_surface.get_height()) // 2
                )
                screen.blit(input_surface, (text_x, text_y))

                # Курсор
                if self.input_active and self.cursor_visible:
                    cursor_x = text_x + input_surface.get_width()
                    cursor_y = text_y
                    cursor_height = input_surface.get_height()
                    pygame.draw.line(
                        screen,
                        self.cursor_color,
                        (cursor_x, cursor_y),
                        (cursor_x, cursor_y + cursor_height),
                        2,
                    )

        # Кнопка продолжения
        if self.duration_input and self.duration_input != "пропущено":
            continue_text = "Нажмите ENTER для сохранения ответа"
            continue_surface = self.text_font.render(
                continue_text, True, self.highlight_color
            )
            if continue_surface:
                screen.blit(
                    continue_surface,
                    (
                        self.screen_width // 2 - continue_surface.get_width() // 2,
                        self.screen_height - 100,
                    ),
                )

    def update(self):
        """Обновляет состояние (для мигания курсора)"""
        if self.is_active and self.state == "asking_duration" and self.input_active:
            current_time = pygame.time.get_ticks()
            if current_time - self.cursor_timer > self.cursor_blink_interval:
                self.cursor_visible = not self.cursor_visible
                self.cursor_timer = current_time
