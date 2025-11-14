import pygame
import sys
from fixation import FixationCross, FixationShape
from trajectory import TrajectoryManager
from moving_point import MovingPoint
from instruction_screen import InstructionScreen
from data_collector import DataCollector
from exp_config import ExperimentConfig
from utils import load_trajectories, save_experiment_data
from timing_estimation import TimingEstimationScreen
from reproduction_task import ReproductionTask
from block_manager import BlockManager


class ExperimentState:
    """Класс для управления состоянием эксперимента"""

    def __init__(self) -> None:
        self.waiting_for_initial_start = True
        self.waiting_for_instruction = False
        self.movement_started = False
        self.occlusion_started = False
        self.running = True
        self.instruction_delay_timer = 0
        self.INSTRUCTION_DELAY = 900


class KeyHandler:
    """Класс для обработки клавиш"""

    def __init__(self, experiment) -> None:
        self.experiment = experiment
        self.setup_key_handlers()

    def setup_key_handlers(self) -> None:
        """Настройка обработчиков клавиш"""
        self.key_handlers = {
            pygame.K_ESCAPE: self.handle_escape,
            pygame.K_SPACE: self.handle_space,
            pygame.K_h: self.handle_help,
            pygame.K_s: self.handle_save,
        }

    def handle_event(self, event) -> bool:
        """Обработка события клавиши"""
        # Скрытая комбинация Ctrl+M для переключения режима
        if (
            event.type == pygame.KEYDOWN
            and event.key == pygame.K_m
            and pygame.key.get_mods() & pygame.KMOD_CTRL
        ):
            self.experiment.toggle_minimal_mode()
            return True

        handler = self.key_handlers.get(event.key)
        if handler:
            handler()
            return True
        return False

    def handle_escape(self) -> None:
        """Обработка выхода"""
        self.experiment.state.running = False

    def handle_space(self) -> None:
        """Обработка пробела"""
        exp = self.experiment

        if (
            exp.state.waiting_for_initial_start
            and exp.initial_instruction_screen.is_active
        ):
            exp.initial_instruction_screen.deactivate()
            exp.state.waiting_for_initial_start = False
            print("Эксперимент начат!")

        elif exp.instruction_screen.is_active:
            if exp.instruction_screen.handle_event(
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)
            ):
                exp.handle_instruction_continue()

        elif self._can_stop_point():
            exp.stop_moving_point()

    def handle_help(self) -> None:
        """Показать справку"""
        if self._can_show_help():
            self.experiment.show_help_info()

    def handle_save(self) -> None:
        """Сохранить данные"""
        if self._can_save():
            self.experiment.save_current_data()

    def _can_stop_point(self):# -> Any | bool:
        """Проверка возможности остановки точки"""
        exp = self.experiment
        return (
            not exp.instruction_screen.is_active
            and not exp.state.waiting_for_instruction
            and not exp.state.waiting_for_initial_start
            and not exp.timing_screen.is_active
            and not exp.reproduction_task.is_active
            and exp.moving_point is not None
            and exp.moving_point.is_moving
            and not exp.moving_point.stopped_by_user
            and not exp.current_task.timing_estimation
            and not exp.current_task.reproduction_task
        )

    def _can_show_help(self) -> bool:
        """Проверка возможности показа справки"""
        exp = self.experiment
        return (
            not exp.instruction_screen.is_active
            and not exp.state.waiting_for_initial_start
            and not exp.timing_screen.is_active
            and not exp.reproduction_task.is_active
        )

    def _can_save(self) -> bool:
        """Проверка возможности сохранения"""
        return self._can_show_help()


class ScreenManager:
    """Класс для управления экранами"""

    def __init__(self, experiment) -> None:
        self.experiment = experiment
        self.screen_handlers = {
            "initial_instruction": self.draw_initial_instruction,
            "timing": self.draw_timing_screen,
            "reproduction": self.draw_reproduction_task,
            "main": self.draw_main_screen,
        }

    def get_current_screen_type(self):
        """Определение текущего типа экрана"""
        exp = self.experiment

        if (
            exp.state.waiting_for_initial_start
            and exp.initial_instruction_screen.is_active
        ):
            return "initial_instruction"
        elif exp.timing_screen.is_active:
            return "timing"
        elif exp.reproduction_task.is_active:
            return "reproduction"
        else:
            return "main"

    def draw_current_screen(self):
        """Отрисовка текущего экрана"""
        screen_type = self.get_current_screen_type()
        handler = self.screen_handlers.get(screen_type)
        if handler:
            handler()

        # Всегда рисуем индикатор поверх всего
        self.experiment.draw_indicator()

    def draw_initial_instruction(self):
        """Отрисовка начальной инструкции"""
        self.experiment.initial_instruction_screen.draw(self.experiment.screen)

    def draw_timing_screen(self):
        """Отрисовка экрана оценки времени"""
        self.experiment.timing_screen.draw(self.experiment.screen)

    def draw_reproduction_task(self):
        """Отрисовка задачи воспроизведения"""
        self.experiment.reproduction_task.draw(
            self.experiment.screen, self.experiment.fixation
        )

    def draw_main_screen(self):
        """Отрисовка основного экрана"""
        exp = self.experiment

        # Рисуем фиксационную точку
        exp.fixation.draw(exp.screen)

        # Отрисовка траектории и точки (только для задач 1-3)
        if not exp.current_task.reproduction_task:
            exp.trajectory_manager.draw_current(exp.screen)
            if exp.moving_point is not None:
                exp.moving_point.draw(exp.screen)

        # Отрисовка инструкции
        exp.instruction_screen.draw(exp.screen)

        # Отображение информации
        exp.draw_info_panel()


class Experiment:
    """Основной класс эксперимента"""

    def __init__(self):
        self.setup_pygame()
        self.state = ExperimentState()
        self.load_resources()
        self.setup_components()
        self.key_handler = KeyHandler(self)
        self.screen_manager = ScreenManager(self)

    def setup_pygame(self):
        """Настройка Pygame"""
        pygame.init()

        # Получаем информацию о дисплее
        display_info = pygame.display.Info()
        self.screen_width = display_info.current_w
        self.screen_height = display_info.current_h

        # Создаем полноэкранное окно без рамок
        self.screen = pygame.display.set_mode(
            (self.screen_width, self.screen_height), pygame.NOFRAME
        )
        pygame.mouse.set_visible(False)
        pygame.display.set_caption("Time_exp_v.0.1.0")

        self.BACKGROUND_COLOR = (255, 255, 255)
        self.clock = pygame.time.Clock()

    def load_resources(self):
        """Загрузка ресурсов"""
        self.trajectories_data = load_trajectories("trajectories.json")
        self.trajectory_manager = TrajectoryManager(self.trajectories_data)
        self.config = ExperimentConfig()

        self.block_manager = BlockManager(
            self.trajectories_data,
            self.config.blocks,
            self.config.available_speeds,
            self.config.available_durations,
        )

    def setup_components(self):
        """Настройка компонентов эксперимента"""
        self.update_progress_info()

        # Загружаем первую траекторию
        self.load_current_trajectory()

        # Получаем конфигурацию текущей задачи
        self.current_task = self.config.get_current_task_config(
            self.current_trial["task_type"]
        )

        # Создаем сборщик данных
        self.data_collector = DataCollector(
            self.config.participant_id, self.progress_info["block_number"]
        )

        # Рассчитываем параметры
        self.calculate_trajectory_parameters()

        # Создаем движущуюся точку
        self.create_moving_point()

        # Создаем экраны
        self.setup_screens()

        # Создаем фиксационную точку
        self.fixation = FixationCross(
            self.screen_width,
            self.screen_height,
            self.current_task.fixation_shape,
            self.config.fixation_size,
        )
        self.fixation.set_color(self.config.fixation_color)

        # Настройки фото-сенсора из конфига
        self.photo_sensor_radius = self.config.photo_sensor_radius
        self.photo_sensor_color_active = self.config.photo_sensor_color_active
        self.photo_sensor_color_passive = self.config.photo_sensor_color_passive

        # Позиция фото-сенсора (рассчитывается на основе смещений от правого нижнего угла)
        self.photo_sensor_position = (
            self.screen_width
            + self.config.photo_sensor_offset_x,  # Правая граница + смещение по X
            self.screen_height
            + self.config.photo_sensor_offset_y,  # Нижняя граница + смещение по Y
        )

        # Выводим информацию о положении фото-сенсора
        print(
            f"Фото-сенсор: позиция ({self.photo_sensor_position[0]}, {self.photo_sensor_position[1]}), "
            f"смещение ({self.config.photo_sensor_offset_x}, {self.config.photo_sensor_offset_y})"
        )

        # Скрытый переключатель для минималистичного режима (True = только необходимое)
        self.minimal_mode = True  # По умолчанию включен минималистичный режим

        # Инициализируем время
        self.start_time = pygame.time.get_ticks()
        self.space_press_time = 0

        # Начинаем первую попытку
        self.start_new_trial()

        self.print_current_trial_info()

    def update_progress_info(self):
        """Обновление информации о прогрессе"""
        self.progress_info = self.block_manager.get_progress_info()
        self.current_block = self.block_manager.get_current_block()
        self.current_trial = self.block_manager.get_current_trial()

    def load_current_trajectory(self):
        """Загрузка текущей траектории"""
        try:
            # Используем реальную категорию траектории (может отличаться от запрошенной для типа R)
            actual_category = self.current_trial.get(
                "actual_trajectory_category", self.current_block.trajectories_category
            )
            self.trajectory_manager.load_trajectory(
                actual_category, self.current_trial["trajectory_index"]
            )
        except ValueError as e:
            print(f"Ошибка загрузки траектории: {e}")
            sys.exit()

    def calculate_trajectory_parameters(self):
        """Расчет параметров траектории"""
        self.assigned_speed = (
            self.current_trial["speed"]
            if self.current_trial["speed"] is not None
            else self.config.available_speeds[0]
        )

        self.calculated_duration = 0.0
        if self.trajectory_manager.current_trajectory is not None and hasattr(
            self.trajectory_manager.current_trajectory, "calculate_duration"
        ):
            self.calculated_duration = (
                self.trajectory_manager.current_trajectory.calculate_duration(
                    self.assigned_speed
                )
            )

    def create_moving_point(self):
        """Создание движущейся точки"""
        if self.trajectory_manager.current_trajectory is not None:
            self.moving_point = MovingPoint(
                self.trajectory_manager.current_trajectory,
                speed=self.assigned_speed,
                occlusion_type=(
                    self.current_task.occlusion_type
                    if self.current_task.occlusion_enabled
                    else "none"
                ),
            )
            if not self.current_task.occlusion_enabled:
                self.moving_point.disable_occlusion()
        else:
            print(
                "Ошибка: Не удалось создать движущуюся точку - траектория не загружена"
            )
            sys.exit()

    def setup_screens(self):
        """Настройка экранов"""
        self.instruction_screen = InstructionScreen(
            self.screen_width, self.screen_height
        )

        self.initial_instruction_screen = InstructionScreen(
            self.screen_width, self.screen_height
        )
        self.initial_instruction_screen.set_custom_content(
            title="ЭКСПЕРИМЕНТ ПО ВОСПРИЯТИЮ ВРЕМЕНИ",
            instructions=[
                "В этом эксперименте вы будете наблюдать за движущейся точкой.",
                "Ваша задача - нажать ПРОБЕЛ в нужный момент времени.",
                "",
                "Эксперимент состоит из 8 блоков по 20 попыток в каждом.",
                "Условия задач меняются случайным образом.",
                "",
                "Управление:",
                "• ПРОБЕЛ - остановить точку / продолжить",
                "• H - справка",
                "• S - сохранить данные",
                "• ESC - выход",
                "",
                "Нажмите ПРОБЕЛ чтобы начать эксперимент",
            ],
        )
        self.initial_instruction_screen.activate()

        self.timing_screen = TimingEstimationScreen(
            self.screen_width, self.screen_height
        )
        self.reproduction_task = ReproductionTask(self.screen_width, self.screen_height)

    def calculate_reference_times(self):
        """Рассчитывает эталонные времена для анализа"""
        if not self.moving_point or not self.trajectory_manager.current_trajectory:
            return

        trajectory = self.trajectory_manager.current_trajectory
        total_length = trajectory.total_length
        speed = self.assigned_speed

        # ИСПОЛЬЗУЕМ ИСПРАВЛЕННЫЙ РАСЧЕТ
        fps = 60
        reference_response_time = (total_length / (speed * fps)) * 1000  # мс

        # Время предъявления стимула (если применимо)
        stimulus_presentation_time = 0.0

        # Время завершения траектории
        trajectory_completion_time = reference_response_time

        self.data_collector.record_reference_times(
            reference_response_time,
            stimulus_presentation_time,
            trajectory_completion_time,
        )

        # ДЛЯ ОТЛАДКИ - выводим информацию о расчете
        print(f"Расчет эталонного времени:")
        print(f"  Длина траектории: {total_length:.1f} px")
        print(f"  Скорость: {speed} px/кадр")
        print(f"  FPS: {fps}")
        print(
            f"  Эталонное время: {reference_response_time:.0f} мс ({reference_response_time/1000:.1f} сек)"
        )

    def start_new_trial(self):
        """Начало новой попытки"""
        condition_type = (
            f"occlusion_{self.current_task.occlusion_type}"
            if self.current_task.occlusion_enabled
            else "no_occlusion"
        )
        if self.current_task.timing_estimation:
            condition_type += "_timing_estimation"
        if self.current_task.reproduction_task:
            condition_type += "_reproduction"

        self.data_collector.start_new_trial(
            trajectory_type=self.current_block.trajectories_category,
            duration=self.calculated_duration,
            speed=self.assigned_speed,
            trajectory_number=self.current_trial["trajectory_index"],
            condition_type=condition_type,
            block_number=self.progress_info["block_number"],
            trial_in_block=self.progress_info["trial_in_block"],
            display_order=self.progress_info["display_order"],
            assigned_speed=self.current_trial["speed"],
            assigned_duration=self.current_trial["duration"],
        )

        # РАССЧИТЫВАЕМ ЭТАЛОННЫЕ ВРЕМЕНА
        self.calculate_reference_times()

    def print_current_trial_info(self):
        """Вывод информации о текущей попытке"""
        trajectory_info = self.trajectory_manager.get_current_trajectory_info()

        info_lines = [
            f"=== Блок {self.progress_info['block_number']}/{self.progress_info['total_blocks']}: {self.current_block.name} ===",
            f"=== {self.current_task.name} ===",
            f"Попытка: {self.progress_info['trial_in_block']}/{self.progress_info['total_trials_in_block']} (порядок: {self.progress_info['display_order']})",
            f"Загружена траектория {self.current_block.trajectories_category}[{self.current_trial['trajectory_index']}]",
            f"Длина траектории: {trajectory_info.get('total_length', 0):.1f} пикселей",
            f"Расчетная продолжительность: {self.calculated_duration:.0f} мс",
            f"Назначенная скорость: {self.assigned_speed} px/кадр",
            f"Фиксационная точка: {self.current_task.fixation_shape.value}",
            f"Окклюзия: {'ВКЛ' if self.current_task.occlusion_enabled else 'ВЫКЛ'}",
            f"Оценка времени: {'ДА' if self.current_task.timing_estimation else 'НЕТ'}",
            f"Воспроизведение времени: {'ДА' if self.current_task.reproduction_task else 'НЕТ'}",
            f"Разрешение экрана: {self.screen_width}x{self.screen_height}",
            f"Минималистичный режим: {'ВКЛ' if self.minimal_mode else 'ВЫКЛ'}",
        ]

        if self.current_trial["duration"] is not None:
            info_lines.insert(
                7, f"Назначенная длительность: {self.current_trial['duration']} мс"
            )
        if self.current_task.occlusion_enabled:
            info_lines.insert(9, f"Тип окклюзии: {self.current_task.occlusion_type}")

        print("\n".join(info_lines))

    def handle_instruction_continue(self):
        """Обработка продолжения после инструкции"""
        self.state.waiting_for_instruction = False
        self.data_collector.complete_trial(
            completed_normally=not self.moving_point.stopped_by_user
        )

        block_completed = self.block_manager.move_to_next_trial()

        if block_completed:
            self.handle_block_completion()
            if self.block_manager.is_experiment_complete():
                print("=== Эксперимент завершен! Все блоки пройдены. ===")
                self.state.running = False
                return

        self.setup_next_trial()

    def handle_block_completion(self):
        """Обработка завершения блока"""
        filename = save_experiment_data(
            self.config.participant_id,
            self.progress_info["block_number"],
            self.data_collector.get_all_data(),
        )
        print(
            f"Блок {self.progress_info['block_number']} завершен! Данные сохранены в: {filename}"
        )

        # Создаем новый сборщик данных для нового блока
        self.update_progress_info()
        self.data_collector = DataCollector(
            self.config.participant_id, self.progress_info["block_number"]
        )

    def setup_next_trial(self):
        """Настройка следующей попытки"""
        self.update_progress_info()
        self.current_task = self.config.get_current_task_config(
            self.current_trial["task_type"]
        )

        self.load_current_trajectory()
        self.calculate_trajectory_parameters()

        # Обновляем фиксационную точку
        self.fixation.set_shape(self.current_task.fixation_shape)

        # Сбрасываем движущуюся точку
        if self.trajectory_manager.current_trajectory is not None:
            self.moving_point.reset(self.trajectory_manager.current_trajectory)
            if self.current_task.occlusion_enabled:
                self.moving_point.set_occlusion_type(self.current_task.occlusion_type)
                self.moving_point.occlusion_enabled = True
            else:
                self.moving_point.disable_occlusion()

        # Сбрасываем состояние
        self.start_time = pygame.time.get_ticks()
        self.state.movement_started = False
        self.state.occlusion_started = False
        self.state.instruction_delay_timer = 0

        # Начинаем новую попытку
        self.start_new_trial()
        self.print_current_trial_info()

    def stop_moving_point(self):
        """Остановка движущейся точки пользователем"""
        self.moving_point.stop_by_user()
        self.space_press_time = pygame.time.get_ticks()

        # ЗАПИСЫВАЕМ ДАННЫЕ С ВРЕМЕНЕМ ОСТАНОВКИ
        was_visible = self.moving_point.is_visible
        self.data_collector.record_space_press(
            stopped_by_user=True, was_visible=was_visible
        )

        # ЗАПИСЫВАЕМ ФАКТИЧЕСКОЕ ВРЕМЯ ДВИЖЕНИЯ
        if (
            self.state.movement_started
            and self.data_collector.current_trial_data["movement_start_time"]
        ):
            movement_duration = (
                self.space_press_time
                - self.data_collector.current_trial_data["movement_start_time"]
            )
            self.data_collector.record_trajectory_duration(movement_duration)

        self.state.instruction_delay_timer = pygame.time.get_ticks()
        self.state.waiting_for_instruction = True

        reaction_time = self.space_press_time - self.start_time
        print(f"Пользователь остановил точку! Время реакции: {reaction_time}мс")
        print(f"Задержка 900 мс перед показом инструкции...")

    def show_help_info(self):
        """Показать информацию о управлении"""
        help_info = [
            "=== Управление ===",
            "ПРОБЕЛ: Остановить точку / продолжить",
            "H: Показать справку",
            "S: Сохранить данные",
            "ESC: Выход",
            f"Текущий блок: {self.progress_info['block_number']}/{self.progress_info['total_blocks']} - {self.current_block.name}",
            f"Текущая задача: {self.current_task.name}",
            f"Прогресс: {self.progress_info['trial_in_block']}/{self.progress_info['total_trials_in_block']} попыток",
            f"Порядок показа: {self.progress_info['display_order']}",
            f"Скорость: {self.assigned_speed} px/кадр",
            f"Фиксационная точка: {self.current_task.fixation_shape.value}",
            f"Окклюзия: {'ВКЛ' if self.current_task.occlusion_enabled else 'ВЫКЛ'}",
            f"Оценка времени: {'ДА' if self.current_task.timing_estimation else 'НЕТ'}",
            f"Воспроизведение времени: {'ДА' if self.current_task.reproduction_task else 'НЕТ'}",
            f"Разрешение экрана: {self.screen_width}x{self.screen_height}",
            f"Минималистичный режим: {'ВКЛ' if self.minimal_mode else 'ВЫКЛ'}",
        ]

        if self.current_trial["duration"] is not None:
            help_info.insert(10, f"Длительность: {self.current_trial['duration']} мс")
        if self.current_task.occlusion_enabled:
            help_info.insert(12, f"Тип окклюзии: {self.current_task.occlusion_type}")

        print("\n".join(help_info))

    def save_current_data(self):
        """Сохранение текущих данных"""
        filename = save_experiment_data(
            self.config.participant_id,
            self.progress_info["block_number"],
            self.data_collector.get_all_data(),
        )
        print(f"Данные текущего блока сохранены в файл: {filename}")

    def draw_indicator(self):
        """Рисует индикаторную окружность для фото-сенсора"""
        # Белый на начальном экране и экране инструкции, черный на остальных
        if (
            self.state.waiting_for_initial_start
            and self.initial_instruction_screen.is_active
        ) or self.instruction_screen.is_active:
            color = (
                self.photo_sensor_color_passive
            )  # Белый - начальный экран и инструкция
        else:
            color = self.photo_sensor_color_active  # Черный - все остальные экраны

        pygame.draw.circle(
            self.screen, color, self.photo_sensor_position, self.photo_sensor_radius
        )
        # Добавляем обводку для лучшей видимости
        pygame.draw.circle(
            self.screen,
            (0, 0, 0),
            self.photo_sensor_position,
            self.photo_sensor_radius,
            1,
        )

    def draw_info_panel(self):
        """Отрисовка информационной панели (скрывается в минималистичном режиме)"""
        # Не отображаем информацию в минималистичном режиме
        if self.minimal_mode:
            return

        font = pygame.font.Font(None, 24)

        info_texts = [
            f"Задача: {self.current_task.name}",
            f"Блок: {self.progress_info['block_number']}/{self.progress_info['total_blocks']} - {self.current_block.name}",
            f"Прогресс: {self.progress_info['trial_in_block']}/{self.progress_info['total_trials_in_block']} (порядок: {self.progress_info['display_order']})",
            f"Испытуемый: {self.config.participant_id}",
            f"Фиксация: {self.current_task.fixation_shape.value} | Окклюзия: {'ВКЛ' if self.current_task.occlusion_enabled else 'ВЫКЛ'} | Оценка: {'ДА' if self.current_task.timing_estimation else 'НЕТ'} | Воспроизведение: {'ДА' if self.current_task.reproduction_task else 'НЕТ'}",
            f"Разрешение: {self.screen_width}x{self.screen_height}",
        ]

        # Отображение задержки
        if (
            self.state.waiting_for_instruction
            and not self.instruction_screen.is_active
            and not self.current_task.timing_estimation
            and not self.current_task.reproduction_task
        ):
            time_left = self.state.INSTRUCTION_DELAY - (
                pygame.time.get_ticks() - self.state.instruction_delay_timer
            )
            if time_left > 0:
                delay_info = font.render(f"Задержка: {time_left} мс", True, (255, 0, 0))
                self.screen.blit(
                    delay_info, (self.screen_width - 150, self.screen_height - 25)
                )

        # Отображение основной информации
        y_positions = [
            self.screen_height - 120,
            self.screen_height - 95,
            self.screen_height - 70,
            self.screen_height - 45,
            self.screen_height - 20,
        ]

        for i, text in enumerate(info_texts[:5]):
            rendered_text = font.render(text, True, (0, 0, 0))
            self.screen.blit(rendered_text, (10, y_positions[i]))

        # Разрешение экрана
        resolution_text = font.render(info_texts[5], True, (0, 0, 0))
        self.screen.blit(
            resolution_text, (self.screen_width - 200, self.screen_height - 20)
        )

    def toggle_minimal_mode(self):
        """Переключает минималистичный режим (только для разработки)"""
        self.minimal_mode = not self.minimal_mode
        mode = "МИНИМАЛИСТИЧНЫЙ" if self.minimal_mode else "ПОЛНЫЙ"
        print(
            f"Режим переключен: {mode} - информация {'скрыта' if self.minimal_mode else 'отображается'}"
        )

    def handle_special_screens(self, event):
        """Обработка специальных экранов"""
        # Обработка экрана оценки времени
        if self.timing_screen.is_active:
            if self.timing_screen.handle_event(event):
                timing_results = self.timing_screen.get_results()
                self.data_collector.record_timing_estimation(timing_results)
                self.timing_screen.deactivate()
                self.data_collector.complete_trial(completed_normally=True)

                # ВСЕГДА показываем инструкцию после оценки времени
                self.instruction_screen.activate()
                print(
                    f"Оценка времени завершена! Фактическое: {timing_results['actual_duration']}мс, Оцененное: {timing_results['estimated_duration']}мс"
                )
                print("Показ инструкции 'Нажмите ПРОБЕЛ чтобы продолжить'...")
                return True

        # Обработка задачи воспроизведения
        elif self.reproduction_task.is_active:
            if self.reproduction_task.handle_event(event):
                reproduction_results = self.reproduction_task.get_results()
                self.data_collector.record_reproduction_results(reproduction_results)
                self.reproduction_task.deactivate()
                self.data_collector.complete_trial(completed_normally=True)
                self.instruction_screen.activate()
                print(
                    f"Воспроизведение завершено! Целевое: {reproduction_results['target_duration']}мс, Воспроизведенное: {reproduction_results['reproduced_duration']}мс"
                )
                print("Показ инструкции 'Нажмите ПРОБЕЛ чтобы продолжить'...")
                return True

        return False

    def update_moving_point(self, dt):
        """Обновление движущейся точки"""
        if not self._can_update_point():
            return

        self.moving_point.update(dt)
        current_time = pygame.time.get_ticks()

        # Запись начала движения
        if not self.state.movement_started and self.moving_point.is_moving:
            self.data_collector.record_movement_start()
            self.state.movement_started = True

        # Запись начала окклюзии
        if (
            not self.state.occlusion_started
            and self.moving_point.occlusion_enabled
            and not self.moving_point.is_visible
        ):
            self.data_collector.record_occlusion_start(self.moving_point)
            self.state.occlusion_started = True
            print("Точка вошла в зону окклюзии")

        # Проверка завершения траектории
        if (
            self.moving_point.should_switch_to_next()
            and not self.state.waiting_for_instruction
        ):
            self.handle_trajectory_completion(current_time)

    def _can_update_point(self):
        """Проверка возможности обновления точки"""
        return (
            not self.instruction_screen.is_active
            and not self.state.waiting_for_initial_start
            and not self.timing_screen.is_active
            and not self.reproduction_task.is_active
            and self.moving_point is not None
        )

    def handle_trajectory_completion(self, current_time):
        """Обработка завершения траектории"""
        actual_duration = current_time - self.start_time
        self.data_collector.record_movement_end()

        task_handlers = {
            "timing_estimation": self.handle_timing_task,
            "reproduction_task": self.handle_reproduction_task,
            "default": self.handle_regular_task,
        }

        handler_key = (
            "timing_estimation"
            if self.current_task.timing_estimation
            else (
                "reproduction_task"
                if self.current_task.reproduction_task
                else "default"
            )
        )

        handler = task_handlers[handler_key]
        handler(actual_duration, current_time)

    def handle_timing_task(self, actual_duration, current_time):
        """Обработка задачи оценки времени"""
        self.data_collector.record_trajectory_duration(actual_duration)
        self.timing_screen.activate(actual_duration)
        print(f"Траектория завершена! Фактическое время: {actual_duration}мс")
        print("Переходим к оценке времени...")

    def handle_reproduction_task(self, actual_duration, current_time):
        """Обработка задачи воспроизведения"""
        self.data_collector.record_trajectory_duration(actual_duration)
        assigned_duration = (
            self.current_trial["duration"]
            if self.current_trial["duration"] is not None
            else actual_duration
        )
        self.reproduction_task.activate(assigned_duration)
        print(f"Траектория завершена! Фактическое время: {actual_duration}мс")
        print(f"Используемое время для воспроизведения: {assigned_duration}мс")
        print("Переходим к воспроизведению времени...")

    def handle_regular_task(self, actual_duration, current_time):
        """Обработка регулярной задачи"""
        # ЗАПИСЫВАЕМ ВСЕ ВРЕМЕНА ПРИ АВТОМАТИЧЕСКОМ ЗАВЕРШЕНИИ
        self.data_collector.record_space_press(stopped_by_user=False, was_visible=True)
        self.data_collector.record_trajectory_duration(actual_duration)
        self.data_collector.record_movement_end()  # Убедимся, что время окончания записано

        self.state.instruction_delay_timer = current_time
        self.state.waiting_for_instruction = True
        print("Точка достигла финиша! Задержка 900 мс перед показом инструкции...")

    def check_instruction_delay(self, current_time):
        """Проверка задержки перед показом инструкции"""
        if (
            self.state.waiting_for_instruction
            and not self.instruction_screen.is_active
            and not self.timing_screen.is_active
            and not self.reproduction_task.is_active
            and current_time - self.state.instruction_delay_timer
            >= self.state.INSTRUCTION_DELAY
        ):

            self.instruction_screen.activate()
            self.state.waiting_for_instruction = False  # Сбрасываем флаг ожидания
            print("Показ инструкции 'Нажмите ПРОБЕЛ чтобы продолжить'...")

    def run(self):
        """Запуск основного цикла эксперимента"""
        print("=== Эксперимент запущен ===")

        while self.state.running:
            dt = self.clock.tick(60)
            current_time = pygame.time.get_ticks()

            # Обработка событий
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.state.running = False
                elif event.type == pygame.KEYDOWN:
                    # Отладочная информация
                    if event.key == pygame.K_SPACE:
                        print(
                            f"Нажат ПРОБЕЛ. Состояние: timing_screen.is_active={self.timing_screen.is_active}, instruction_screen.is_active={self.instruction_screen.is_active}"
                        )

                    # Обработка специальных экранов
                    if self.handle_special_screens(event):
                        print("Специальный экран обработан")
                    else:
                        # Обработка обычных клавиш
                        self.key_handler.handle_event(event)

            # Обновление задачи воспроизведения
            if self.reproduction_task.is_active:
                self.reproduction_task.update()

            # Обновление движущейся точки
            self.update_moving_point(dt)

            # Проверка задержки инструкции
            self.check_instruction_delay(current_time)

            # Отрисовка
            self.screen.fill(self.BACKGROUND_COLOR)
            self.screen_manager.draw_current_screen()
            pygame.display.flip()

        self.cleanup()

    def cleanup(self):
        """Очистка ресурсов"""
        if not self.block_manager.is_experiment_complete():
            print(f"\n=== Завершение эксперимента ===")
            filename = save_experiment_data(
                self.config.participant_id,
                self.progress_info["block_number"],
                self.data_collector.get_all_data(),
            )
            print(f"Данные текущего блока сохранены в файл: {filename}")

        pygame.mouse.set_visible(True)
        pygame.quit()
        sys.exit()


def main() -> None:
    """Основная функция"""
    experiment = Experiment()
    experiment.run()


if __name__ == "__main__":
    main()
