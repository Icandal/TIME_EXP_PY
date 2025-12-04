import pygame
import sys
from typing import Dict, Any, Optional
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


class FixationPreviewScreen:
    """Экран предварительного показа фиксационной точки перед траекторией"""

    def __init__(self, screen_width: int, screen_height: int, fixation_size: int = 15):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.fixation_size = fixation_size
        self.showing = False  # Флаг: показываем ли мы экран
        self.background_color = (255, 255, 255)
        self.instruction_shown = True  # Всегда показываем инструкцию
        self.show_trajectory = True  # По умолчанию показывать траекторию

        # Создаем фиксационную точку
        self.fixation_preview = FixationCross(
            screen_width, screen_height, FixationShape.TRIANGLE, fixation_size
        )
        self.fixation_preview.set_color((0, 0, 0))

    def show(self, fixation_shape: FixationShape, show_trajectory: bool = True) -> None:
        """Показывает фиксационную точку и траекторию (если нужно)"""
        self.showing = True
        self.show_trajectory = show_trajectory  # Сохраняем флаг
        # Устанавливаем форму фиксационной точки
        self.fixation_preview.set_shape(fixation_shape)

        if show_trajectory:
            print(
                f"Показана фиксационная точка {fixation_shape.value} и траектория (ожидание пробела)"
            )
        else:
            print(
                f"Показана фиксационная точка {fixation_shape.value} (ожидание пробела)"
            )

    def hide(self) -> None:
        """Скрывает экран"""
        self.showing = False
        print(f"Скрыта фиксационная точка")

    def draw(self, screen: pygame.Surface, trajectory_manager=None) -> None:
        """Рисует экран с фиксационной точкой и траекторией"""
        if not self.showing:
            return

        # Белый фон
        screen.fill(self.background_color)

        # Рисуем траекторию только если нужно и она есть
        if (
            self.show_trajectory
            and trajectory_manager
            and trajectory_manager.has_trajectory()
        ):
            trajectory_manager.draw_current(screen)

        # Рисуем фиксационную точку в центре
        self.fixation_preview.draw(screen)

        # Инструкция для пользователя
        if self.instruction_shown:
            font = pygame.font.Font(None, 36)

            # Разные инструкции в зависимости от типа задачи
            current_shape = getattr(self.fixation_preview, "shape", None)
            if current_shape == FixationShape.CROSS:
                instruction_text = font.render(
                    "Нажмите ПРОБЕЛ чтобы начать задачу", True, (0, 0, 0)
                )
            else:
                instruction_text = font.render(
                    "Нажмите ПРОБЕЛ чтобы начать движение точки", True, (0, 0, 0)
                )

            text_rect = instruction_text.get_rect(
                center=(self.screen_width // 2, self.screen_height - 50)
            )
            screen.blit(instruction_text, text_rect)


class ExperimentState:
    """Класс для управления состоянием эксперимента"""

    def __init__(self) -> None:
        self.waiting_for_initial_start = True
        self.waiting_for_movement_start = (
            False  # Ожидание нажатия пробела для начала движения
        )
        self.in_start_delay = False  # НОВОЕ: находимся в задержке перед стартом
        self.movement_started = False
        self.occlusion_started = False
        self.running = True


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

        # Обычные обработчики клавиш
        if event.type == pygame.KEYDOWN:
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

        # ВАЖНО: Если задача воспроизведения активна, НЕ обрабатываем пробел здесь
        if exp.reproduction_task.is_active:
            print(
                f"[C3 KeyHandler] Пропускаем пробел, т.к. задача воспроизведения уже активна"
            )
            return

        if (
            exp.state.waiting_for_initial_start
            and exp.initial_instruction_screen.is_active
        ):
            exp.initial_instruction_screen.deactivate()
            exp.state.waiting_for_initial_start = False
            print("Эксперимент начат!")

            # После начальной инструкции показываем фиксационную точку и траекторию
            exp.start_trial_preparation()

        elif exp.state.waiting_for_movement_start:
            # Нажатие пробела для начала
            print(f"Нажатие пробела для начала задачи")

            if exp.current_task.reproduction_task:
                # Для задачи воспроизведения СРАЗУ начинаем задачу
                exp.state.waiting_for_movement_start = False
                exp.fixation_preview_screen.hide()  # Скрываем превью

                # Получаем назначенную длительность
                assigned_duration = (
                    exp.current_trial["duration"]
                    if exp.current_trial["duration"] is not None
                    else exp.config.available_durations[0]
                )

                print(
                    f"Запуск задачи воспроизведения с длительностью {assigned_duration}мс"
                )

                # СРАЗУ активируем задачу, она сама покажет первый крестик
                exp.reproduction_task.activate(assigned_duration)

            else:
                # Для задач с траекторией: начинаем движение с задержкой
                print(f"Запуск задачи с траекторией")
                exp.start_movement_with_delay()

        elif self._can_stop_point():
            print(f"Остановка точки")
            exp.stop_moving_point()

    def handle_help(self) -> None:
        """Показать справку"""
        if self._can_show_help():
            self.experiment.show_help_info()

    def handle_save(self) -> None:
        """Сохранить данные"""
        if self._can_save():
            self.experiment.save_current_data()

    def _can_stop_point(self) -> bool:
        """Проверка возможности остановки точки"""
        exp = self.experiment
        return (
            not exp.state.waiting_for_initial_start
            and not exp.state.waiting_for_movement_start
            and not exp.state.in_start_delay  # Нельзя останавливать во время задержки
            and not exp.timing_screen.is_active
            and not exp.reproduction_task.is_active
            and exp.moving_point is not None
            and exp.moving_point.is_moving
            and not exp.moving_point.stopped_by_user
            and exp.current_task.has_trajectory
            and not exp.current_task.reproduction_task
        )

    def _can_show_help(self) -> bool:
        """Проверка возможности показа справки"""
        exp = self.experiment
        return (
            not exp.state.waiting_for_initial_start
            and not exp.state.waiting_for_movement_start
            and not exp.state.in_start_delay
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
            "cross_for_star": self.draw_cross_for_star,
            "waiting_for_start": self.draw_waiting_for_start,
            "start_delay": self.draw_start_delay,
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
        elif exp.showing_cross_for_star:
            print(
                f"[ScreenManager] Экран: cross_for_star (showing_cross_for_star={exp.showing_cross_for_star})"
            )
            return "cross_for_star"
        elif exp.state.waiting_for_movement_start:
            print(f"[ScreenManager] Экран: waiting_for_start")
            return "waiting_for_start"
        elif exp.state.in_start_delay:
            return "start_delay"
        else:
            return "main"

    def draw_current_screen(self):
        """Отрисовка текущего экрана"""
        screen_type = self.get_current_screen_type()
        handler = self.screen_handlers.get(screen_type)
        if handler:
            handler()
        else:
            print(f"ОШИБКА: Нет обработчика для типа экрана {screen_type}")

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
        self.experiment.reproduction_task.draw(self.experiment.screen, None)

    def draw_cross_for_star(self):
        """Отрисовка крестика для задачи со звездочкой"""
        exp = self.experiment

        # Белый фон
        exp.screen.fill(exp.BACKGROUND_COLOR)

        # Рисуем крестик
        if exp.cross_for_star:
            exp.cross_for_star.draw(exp.screen)

        # Инструкция
        font = pygame.font.Font(None, 36)
        instruction = font.render("Нажмите ПРОБЕЛ для оценки времени", True, (0, 0, 0))
        text_rect = instruction.get_rect(
            center=(exp.screen_width // 2, exp.screen_height - 50)
        )
        exp.screen.blit(instruction, text_rect)

    def draw_waiting_for_start(self):
        """Отрисовка экрана ожидания начала движения"""
        exp = self.experiment

        # Используем fixation_preview_screen для отрисовки
        if exp.current_task.has_trajectory:
            exp.fixation_preview_screen.draw(exp.screen, exp.trajectory_manager)
        else:
            exp.fixation_preview_screen.draw(exp.screen, None)

    def draw_start_delay(self):
        """Отрисовка экрана задержки перед стартом"""
        exp = self.experiment

        # Белый фон
        exp.screen.fill(exp.BACKGROUND_COLOR)

        # Рисуем фиксационную точку
        exp.fixation.draw(exp.screen)

        # Рисуем траекторию (если есть)
        if exp.current_task.has_trajectory and exp.trajectory_manager.has_trajectory():
            exp.trajectory_manager.draw_current(exp.screen)

        # УБРАНО: показываем, что идет задержка перед стартом
        # Только крестик и траектория без текста
        # font = pygame.font.Font(None, 36)
        # delay_text = font.render(f"Задержка перед стартом...", True, (0, 0, 0))
        # text_rect = delay_text.get_rect(
        #     center=(exp.screen_width // 2, exp.screen_height - 50)
        # )
        # exp.screen.blit(delay_text, text_rect)

    def draw_main_screen(self):
        """Отрисовка основного экрана"""
        exp = self.experiment

        # Рисуем фиксационную точку
        exp.fixation.draw(exp.screen)

        # Рисуем траекторию и точку только для задач с траекторией
        if exp.current_task.has_trajectory and exp.trajectory_manager.has_trajectory():
            exp.trajectory_manager.draw_current(exp.screen)
            if exp.moving_point is not None:
                exp.moving_point.draw(exp.screen)

        exp.draw_info_panel()


class Experiment:
    """Основной класс эксперимента"""

    def __init__(self):
        self.delay_start_time = 0
        self.setup_pygame()
        self.state = ExperimentState()
        self.load_resources()
        self.setup_components()
        self.key_handler = KeyHandler(self)
        self.screen_manager = ScreenManager(self)

        # Объявляем переменные
        self.current_block = None
        self.current_trial: Dict[str, Any] = {}
        self.progress_info: Dict[str, Any] = {}

        # Для C2: крестик перед оценкой времени
        self.showing_cross_for_star = False
        self.cross_for_star = None
        self.cross_for_star_start_time = 0
        self.pending_timing_duration = 0

    def record_start_delay(self, delay_ms: int):
        """Записывает информацию о задержке перед стартом"""
        if hasattr(self, "data_collector") and self.data_collector:
            self.data_collector.current_trial_data["start_delay"] = delay_ms
            print(f"Записана задержка перед стартом: {delay_ms}мс")

    def setup_pygame(self):
        """Настройка Pygame"""
        pygame.init()

        display_info = pygame.display.Info()
        self.screen_width = display_info.current_w
        self.screen_height = display_info.current_h

        self.screen = pygame.display.set_mode(
            (self.screen_width, self.screen_height), pygame.NOFRAME
        )
        pygame.mouse.set_visible(False)
        pygame.display.set_caption("Time_exp_v.0.1.0")

        self.BACKGROUND_COLOR = (255, 255, 255)
        self.clock = pygame.time.Clock()

    def load_resources(self):
        """Загрузка ресурсов"""
        self.trajectories_data = load_trajectories("traj_lib.json")
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

        # Получаем конфигурацию текущей задачи
        self.current_task = self.config.get_current_task_config(
            self.current_trial["task_type"]
        )

        # Создаем сборщик данных
        self.data_collector = DataCollector(
            self.config.participant_id, self.progress_info["block_number"]
        )

        # Загружаем траекторию ТОЛЬКО для задач с траекторией
        if self.current_task.has_trajectory:
            self.load_current_trajectory()
            self.calculate_trajectory_parameters()
            self.create_moving_point()
        else:
            self.moving_point = None
            print("Задача без траектории - пропускаем создание движущейся точки")

        # Создаем экраны
        self.setup_screens()

        # Создаем задачу воспроизведения
        self.reproduction_task = ReproductionTask(self.screen_width, self.screen_height)

        # Создаем экран предпоказа фиксационной точки
        self.fixation_preview_screen = FixationPreviewScreen(
            self.screen_width, self.screen_height, self.config.fixation_size
        )

        # Создаем фиксационную точку
        self.fixation = FixationCross(
            self.screen_width,
            self.screen_height,
            self.current_task.fixation_shape,
            self.config.fixation_size,
        )
        self.fixation.set_color(self.config.fixation_color)

        # Настройки фото-сенсора
        self.photo_sensor_radius = self.config.photo_sensor_radius
        self.photo_sensor_color_active = self.config.photo_sensor_color_active
        self.photo_sensor_color_passive = self.config.photo_sensor_color_passive
        self.photo_sensor_color_occlusion = self.config.photo_sensor_color_occlusion
        self.photo_sensor_position = (
            self.screen_width + self.config.photo_sensor_offset_x,
            self.screen_height + self.config.photo_sensor_offset_y,
        )

        # Состояние фотосенсора: active, passive, occlusion
        self.photo_sensor_state = "passive"

        print(
            f"Фото-сенсор: позиция ({self.photo_sensor_position[0]}, {self.photo_sensor_position[1]})"
        )

        # Скрытый переключатель для минималистичного режима
        self.minimal_mode = True

        # Инициализируем время
        self.start_time = pygame.time.get_ticks()
        self.space_press_time = 0

        # Начинаем первую попытку
        self.start_new_trial()

        self.print_current_trial_info()

    def update_progress_info(self):
        """Обновление информации о прогрессе"""
        if self.block_manager.is_experiment_complete():
            print("Эксперимент завершен, нет активных блоков")
            self.progress_info = {
                "block_number": 0,
                "total_blocks": len(self.block_manager.blocks),
                "trial_in_block": 0,
                "display_order": 0,
                "total_trials_in_block": 0,
                "block_name": "Эксперимент завершен",
                "task_type": 0,
                "trajectory_category": "none",
                "actual_trajectory_category": "none",
                "trajectory_index": 0,
                "speed": None,
                "duration": None,
            }
            self.current_block = None
            self.current_trial = {}
        else:
            self.progress_info = self.block_manager.get_progress_info()
            self.current_block = self.block_manager.get_current_block()
            self.current_trial = self.block_manager.get_current_trial()

    def load_current_trajectory(self):
        """Загрузка текущей траектории (только для задач с траекторией)"""
        try:
            if self.current_block is None:
                print("❌ Ошибка: текущий блок не определен")
                return

            if self.current_task.has_trajectory:
                block_name = self.current_trial["block_name"]
                actual_category = self.current_trial["actual_trajectory_category"]
                trajectory_index = self.current_trial["trajectory_index"]

                print(f"🔄 Загрузка траектории для задачи с траекторией:")
                print(f"   Блок: {block_name}")
                print(f"   Категория: {actual_category}")
                print(f"   Индекс: {trajectory_index}")

                self.trajectory_manager.load_trajectory(
                    block_name, actual_category, trajectory_index
                )

                if self.trajectory_manager.has_trajectory():
                    info = self.trajectory_manager.get_current_trajectory_info()
                    print(
                        f"✅ Траектория загружена: {info['point_count']} точек, длина: {info['total_length']:.1f}px"
                    )
                else:
                    print(f"⚠️  Пустая траектория для задачи с траекторией")
            else:
                self.trajectory_manager.current_trajectory = None
                print("ℹ️ Задача без траектории - пропускаем загрузку")

        except Exception as e:
            print(f"❌ Ошибка загрузки траектории: {e}")
            self.trajectory_manager.current_trajectory = None

    def calculate_trajectory_parameters(self):
        """Расчет параметров траектории (только для задач с траекторией)"""
        if not self.current_task.has_trajectory:
            self.assigned_speed = 0
            self.calculated_duration = 0
            print("ℹ️ Задача без траектории - пропускаем расчет параметров")
            return

        decoded_params = self.current_trial.get("decoded_params", {})

        self.assigned_speed = (
            decoded_params.get("speed")
            if decoded_params.get("speed") is not None
            else (
                self.current_trial["speed"]
                if self.current_trial["speed"] is not None
                else self.config.available_speeds[0]
            )
        )

        self.calculated_duration = 0.0
        if (
            self.trajectory_manager.current_trajectory is not None
            and self.trajectory_manager.has_trajectory()
        ):
            self.calculated_duration = (
                self.trajectory_manager.current_trajectory.calculate_duration(
                    self.assigned_speed
                )
            )
            print(f"📏 Расчет длительности: {self.calculated_duration:.0f} мс")
        else:
            print("⚠️ Невозможно рассчитать длительность - нет траектории")

    def create_moving_point(self):
        """Создание движущейся точки (только для задач с траекторией и непустой траекторией)"""
        if (
            not self.current_task.has_trajectory
            or self.trajectory_manager.current_trajectory is None
            or len(self.trajectory_manager.current_trajectory.points) < 2
        ):

            self.moving_point = None
            print(
                "Задача без траектории или пустая траектория - пропускаем создание точки"
            )
            return

        # Создаем точку только если есть траектория с точками
        self.moving_point = MovingPoint(
            self.trajectory_manager.current_trajectory,
            speed=self.assigned_speed,
            occlusion_type=(
                self.current_task.occlusion_type
                if self.current_task.occlusion_enabled
                else "none"
            ),
            occlusion_range=self.current_task.occlusion_range,
            occlusion_delay=500,
        )

        if not self.current_task.occlusion_enabled:
            self.moving_point.disable_occlusion()

    def setup_screens(self):
        """Настройка экранов"""
        self.initial_instruction_screen = InstructionScreen(
            self.screen_width, self.screen_height
        )

        # Адаптивное содержимое для начальной инструкции
        instruction_lines = [
            "ЭКСПЕРИМЕНТ ПО ВОСПРИЯТИЮ ВРЕМЕНИ",
            "",
            "В этом эксперименте вы будете наблюдать за движущейся точкой.",
            "",
            "Типы задач:",
            "1. Окклюзия: точка скрывается на части траектории",
            "2. Оценка времени: остановите точку и оцените время движения",
            "3. Воспроизведение: запомните и воспроизведите время",
            "",
            "Управление:",
            "• ПРОБЕЛ - начать движение / остановить точку / продолжить",
            "• ESC - выход",
            "",
            "Нажмите ПРОБЕЛ чтобы начать эксперимент",
        ]

        self.initial_instruction_screen.set_custom_content(
            title=instruction_lines[0], instructions=instruction_lines[1:]
        )
        self.initial_instruction_screen.activate()

        self.timing_screen = TimingEstimationScreen(
            self.screen_width, self.screen_height
        )

    def calculate_reference_times(self):
        """ИСПРАВЛЕННЫЙ РАСЧЕТ: Рассчитывает эталонные времена для анализа"""
        if not self.moving_point or not self.trajectory_manager.current_trajectory:
            return

        trajectory = self.trajectory_manager.current_trajectory
        total_length = trajectory.total_length
        speed_px_per_frame = self.assigned_speed

        # ТОЧНЫЙ расчет
        frames_required = total_length / speed_px_per_frame
        reference_response_time = frames_required * (1000 / 60)

        print(f"РАСЧЕТ ЭТАЛОННОГО ВРЕМЕНИ:")
        print(f"  Длина траектории: {total_length:.1f} px")
        print(f"  Скорость: {speed_px_per_frame} px/кадр")
        print(f"  Требуется кадров: {frames_required:.1f}")
        print(f"  Эталонное время: {reference_response_time:.0f} мс")

        stimulus_presentation_time = 0.0
        trajectory_completion_time = reference_response_time

        self.data_collector.record_reference_times(
            reference_response_time,
            stimulus_presentation_time,
            trajectory_completion_time,
        )

    def start_trial_preparation(self):
        """Подготовка к началу попытки (после начальной инструкции)"""
        if self.current_task.has_trajectory:
            # Показываем фиксационную точку и траекторию, ожидаем пробела
            self.state.waiting_for_movement_start = True
            self.fixation_preview_screen.show(
                self.current_task.fixation_shape,
                show_trajectory=self.current_task.has_trajectory,
            )
            print(
                "Показана фиксационная точка и траектория. Ожидание нажатия ПРОБЕЛ для начала движения."
            )
        elif self.current_task.reproduction_task:
            # Для задач воспроизведения НЕ показываем FixationPreviewScreen
            print("Задача воспроизведения (C3) - пропускаем фиксационный превью")
            self.setup_next_trial()  # Переходим сразу к настройке
        else:
            # Для других задач без траектории
            self.start_new_trial()

    def start_new_trial(self):
        """Начало новой попытки"""
        # Проверяем, что текущий блок существует
        if self.current_block is None:
            print("Ошибка: нет активного блока")
            return

        # Используем декодированные параметры для определения типа условия
        decoded_params = self.current_trial.get("decoded_params", {})

        # Определяем тип условия на основе декодированной задачи
        if decoded_params.get("task_index") == 2:  # C3 - воспроизведение времени
            condition_type = "reproduction"
        elif decoded_params.get("task_index") == 1:  # C2 - оценка времени
            condition_type = "timing_estimation"
        else:  # C1 - окклюзия или по умолчанию
            condition_type = (
                f"occlusion_{self.current_task.occlusion_type}"
                if self.current_task.occlusion_enabled
                else "no_occlusion"
            )

        # Получаем информацию о задержке из moving_point (если она существует)
        start_delay = 0
        if self.moving_point is not None and hasattr(self.moving_point, "start_delay"):
            start_delay = self.moving_point.start_delay
            print(f"Сохраняем информацию о задержке: {start_delay}мс")

        # Записываем данные о попытке
        self.data_collector.start_new_trial(
            trajectory_type=(
                self.current_block.trajectories_category
                if self.current_task.has_trajectory
                else "none"
            ),
            duration=(
                self.calculated_duration if self.current_task.has_trajectory else 0
            ),
            speed=(self.assigned_speed if self.current_task.has_trajectory else 0),
            trajectory_number=(
                self.current_trial["trajectory_index"]
                if self.current_task.has_trajectory
                else 0
            ),
            condition_type=condition_type,
            block_number=self.progress_info["block_number"],
            trial_in_block=self.progress_info["trial_in_block"],
            display_order=self.progress_info["display_order"],
            assigned_speed=self.current_trial["speed"],
            assigned_duration=self.current_trial["duration"],
            start_delay=start_delay,
        )

        # Для задач с траекторией рассчитываем эталонные времена
        if self.current_task.has_trajectory:
            self.calculate_reference_times()

    def print_current_trial_info(self):
        """Вывод информации о текущей попытке"""
        block_name = self.current_block.name if self.current_block else "N/A"
        trajectory_category = (
            self.current_block.trajectories_category if self.current_block else "N/A"
        )

        # Получаем декодированные параметры
        decoded_params = self.current_trial.get("decoded_params", {})
        decoded_category = decoded_params.get("decoded_category", "N/A")

        info_lines = [
            f"=== Блок {self.progress_info['block_number']}/{self.progress_info['total_blocks']}: {block_name} ===",
            f"=== {self.current_task.name} ===",
            f"Декодированная категория: {decoded_category}",
            f"Попытка: {self.progress_info['trial_in_block']}/{self.progress_info['total_trials_in_block']} (порядок: {self.progress_info['display_order']})",
            f"Тип задачи: {'С траекторией' if self.current_task.has_trajectory else 'Без траектории'}",
            f"Фиксационная точка: {self.current_task.fixation_shape.value}",
        ]

        if self.current_task.has_trajectory:
            trajectory_info = self.trajectory_manager.get_current_trajectory_info()
            info_lines.extend(
                [
                    f"Загружена траектория {trajectory_category}[{self.current_trial['trajectory_index']}]",
                    f"Длина траектории: {trajectory_info.get('total_length', 0):.1f} пикселей",
                    f"Расчетная продолжительность: {self.calculated_duration:.0f} мс",
                    f"Назначенная скорость: {self.assigned_speed} px/кадр",
                    f"Окклюзия: {'ВКЛ' if self.current_task.occlusion_enabled else 'ВЫКЛ'}",
                ]
            )

            if self.current_task.occlusion_enabled:
                info_lines.append(f"Тип окклюзии: {self.current_task.occlusion_type}")

        if self.current_task.timing_estimation:
            info_lines.append("Оценка времени после остановки: ДА")

        if self.current_task.reproduction_task:
            info_lines.extend(
                [
                    "Воспроизведение времени: ДА",
                    f"Назначенная длительность: {self.current_trial['duration']} мс",
                ]
            )

        if hasattr(self, "moving_point") and self.moving_point is not None:
            info_lines.append(
                f"Задержка перед стартом: {self.moving_point.start_delays} мс (случайный выбор)"
            )

        print("\n".join(info_lines))

    def handle_block_completion(self):
        """Обработка завершения блока"""
        self.save_current_data()
        self.update_progress_info()
        self.data_collector = DataCollector(
            self.config.participant_id, self.progress_info["block_number"]
        )

    def setup_next_trial(self):
        """Настройка следующей попытки"""
        self.update_progress_info()

        # Проверяем, не завершен ли эксперимент
        if self.block_manager.is_experiment_complete():
            print("Эксперимент завершен, нет следующих попыток")
            return

        # Используем декодированные параметры из категории траектории
        decoded_params = self.current_trial.get("decoded_params", {})
        if decoded_params:
            # Переопределяем тип задачи и параметры на основе декодированной категории
            task_type = decoded_params.get(
                "task_index", self.current_trial["task_type"]
            )
            speed = decoded_params.get("speed")
            duration = decoded_params.get("duration")

            # ОБНОВЛЯЕМ параметры в текущем испытании
            self.current_trial["task_type"] = task_type
            self.current_trial["speed"] = speed
            self.current_trial["duration"] = duration

            print(
                f"Применены параметры из категории: задача={task_type}, скорость={speed}, длительность={duration}"
            )

        self.current_task = self.config.get_current_task_config(
            self.current_trial["task_type"]
        )

        # ОБНОВЛЯЕМ назначенную скорость на основе декодированных параметров
        decoded_params = self.current_trial.get("decoded_params", {})
        self.assigned_speed = (
            decoded_params.get(
                "speed"
            )  # Используем скорость из декодированных параметров
            if decoded_params.get("speed") is not None
            else (
                self.current_trial["speed"]  # Резервный вариант
                if self.current_trial["speed"] is not None
                else self.config.available_speeds[0]
            )
        )

        print(f"ФИНАЛЬНАЯ СКОРОСТЬ ДЛЯ ТОЧКИ: {self.assigned_speed} px/кадр")

        # Сбрасываем состояние фотосенсора при начале новой попытки
        self.photo_sensor_state = "passive"
        print("Фотосенсор: белый (начало задачи)")

        # Обновляем фиксационную точку
        self.fixation.set_shape(self.current_task.fixation_shape)

        # ДЛЯ ЗАДАЧ С ТРАЕКТОРИЕЙ: загружаем траекторию и создаем/обновляем точку
        if self.current_task.has_trajectory:
            self.load_current_trajectory()
            self.calculate_trajectory_parameters()

            if self.trajectory_manager.current_trajectory is not None:
                if self.moving_point is None:
                    self.create_moving_point()
                else:
                    self.moving_point.reset(self.trajectory_manager.current_trajectory)
                    # Явно обновляем скорость после reset
                    print(f"=== ЯВНОЕ ОБНОВЛЕНИЕ СКОРОСТИ ===")
                    print(
                        f"  Скорость до обновления: {self.moving_point.speed} px/кадр"
                    )
                    print(f"  Новая скорость: {self.assigned_speed} px/кадр")
                    self.moving_point.speed = self.assigned_speed
                    print(
                        f"  Скорость после обновления: {self.moving_point.speed} px/кадр"
                    )

                # Проверяем, что moving_point не None перед вызовом методов
                if self.moving_point is not None:
                    if self.current_task.occlusion_enabled:
                        self.moving_point.set_occlusion_type(
                            self.current_task.occlusion_type
                        )
                        self.moving_point.occlusion_enabled = True
                    else:
                        self.moving_point.disable_occlusion()
        else:
            # ДЛЯ ЗАДАЧ БЕЗ ТРАЕКТОРИИ (крестик C3):
            # Очищаем движущуюся точку и траекторию
            self.moving_point = None
            self.trajectory_manager.current_trajectory = None
            print("Задача без траектории (крестик) - очищены данные о траектории")

        # Сбрасываем состояние
        self.start_time = pygame.time.get_ticks()
        self.state.movement_started = False
        self.state.occlusion_started = False
        self.state.waiting_for_movement_start = False
        self.state.in_start_delay = False
        self.fixation_preview_screen.hide()

        # ИСПРАВЛЕНИЕ: РАЗНАЯ ЛОГИКА ДЛЯ ЗАДАЧ С ТРАЕКТОРИЕЙ И ЗАДАЧ ВОСПРОИЗВЕДЕНИЯ
        if self.current_task.has_trajectory:
            # Для задач С ТРАЕКТОРИЕЙ: показываем фиксационную точку и ожидаем ПРОБЕЛ
            self.state.waiting_for_movement_start = True

            # Определяем, показывать ли траекторию
            show_trajectory = True

            # Показываем экран предпоказа
            self.fixation_preview_screen.show(
                self.current_task.fixation_shape, show_trajectory=show_trajectory
            )

            print(
                f"Ожидание ПРОБЕЛ для начала ({self.current_task.fixation_shape.value})"
            )
            print("Траектория будет показана")

        elif self.current_task.reproduction_task:
            # Для задач ВОСПРОИЗВЕДЕНИЯ (C3): НЕ показываем FixationPreviewScreen
            # СРАЗУ активируем задачу воспроизведения
            print(f"=== НАЧАЛО ЗАДАЧИ ВОСПРОИЗВЕДЕНИЯ (C3) ===")

            # Получаем назначенную длительность
            assigned_duration = (
                self.current_trial["duration"]
                if self.current_trial["duration"] is not None
                else self.config.available_durations[0]
            )

            print(
                f"Запуск задачи воспроизведения с длительностью {assigned_duration}мс"
            )

            # Сразу начинаем задачу воспроизведения
            self.start_new_trial()
            self.reproduction_task.activate(assigned_duration)

        else:
            # Для других задач без траектории (если такие есть)
            self.start_new_trial()

        self.print_current_trial_info()

    def start_movement_with_delay(self):
        """Начинает задержку перед движением точки"""
        # Для всех типов задач с траекторией

        if self.current_task.has_trajectory and self.moving_point is not None:
            # Скрываем превью
            self.fixation_preview_screen.hide()

            # Устанавливаем состояние задержки
            self.state.in_start_delay = True
            self.state.waiting_for_movement_start = False

            # Фотосенсор белый во время задержки
            self.photo_sensor_state = "passive"
            print(f"Начата случайная задержка: {self.moving_point.start_delay}мс")
            print("Фотосенсор: белый (во время задержки перед стартом)")

            # Запускаем задержку в точке
            self.moving_point.start_movement_with_delay()

            # Записываем информацию о задержке
            if hasattr(self.moving_point, "start_delay"):
                self.record_start_delay(self.moving_point.start_delay)

            # Запускаем новую попытку (запись данных)
            self.start_new_trial()

    def stop_moving_point(self):
        """Остановка движущейся точки пользователем (только для задач с траекторией)"""
        if self.moving_point is None:
            return

        self.moving_point.stop_by_user()
        self.space_press_time = pygame.time.get_ticks()

        was_visible = self.moving_point.is_visible
        self.data_collector.record_space_press(
            stopped_by_user=True, was_visible=was_visible
        )

        # Записываем фактическое время движения до остановки
        actual_duration = 0
        if (
            self.state.movement_started
            and self.data_collector.current_trial_data["movement_start_time"]
        ):
            actual_duration = (
                self.space_press_time
                - self.data_collector.current_trial_data["movement_start_time"]
            )
            self.data_collector.record_trajectory_duration(actual_duration)

        # ДЛЯ ВСЕХ ТИПОВ ЗАДАЧ: определяем дальнейшие действия
        if self.current_task.timing_estimation:
            # Для задач с оценкой времени (звездочка) - показываем крестик
            print(
                f"[C2] Задача со звездочкой: показываем крестик. Фактическое время движения: {actual_duration}мс"
            )

            # Сохраняем фактическое время для оценки
            self.pending_timing_duration = actual_duration

            # Создаем крестик для показа
            self.cross_for_star = FixationCross(
                self.screen_width,
                self.screen_height,
                FixationShape.CROSS,
                self.config.fixation_size,
            )
            self.cross_for_star.set_color(self.config.fixation_color)

            # Устанавливаем флаг показа крестика
            self.showing_cross_for_star = True
            self.cross_for_star_start_time = pygame.time.get_ticks()

            # Фотосенсор белый для крестика
            self.photo_sensor_state = "passive"

            print(
                "[C2] Показан крестик для задачи со звездочкой. Нажмите ПРОБЕЛ для оценки времени."
            )
            print("[C2] Фотосенсор: белый (крестик перед оценкой)")

        else:
            # Для задач БЕЗ оценки времени (треугольник)
            # СРАЗУ переходим к следующей попытке
            self.complete_and_continue()

        reaction_time = self.space_press_time - self.start_time
        print(f"Пользователь остановил точку! Время реакции: {reaction_time}мс")

    def complete_and_continue(self):
        """Завершает текущую попытку и сразу переходит к следующей"""
        self.data_collector.complete_trial(completed_normally=True)

        # Переходим к следующей попытке
        block_completed = self.block_manager.move_to_next_trial()

        if block_completed:
            if self.block_manager.is_experiment_complete():
                print("=== Эксперимент завершен! Все блоки пройдены. ===")
                # СОХРАНЯЕМ ДАННЫЕ ПОСЛЕДНЕГО БЛОКА ПЕРЕД ВЫХОДОМ
                self.save_current_data()
                self.state.running = False
                return
            else:
                self.handle_block_completion()

        self.setup_next_trial()

    def show_help_info(self):
        """Показать информацию о управлении"""
        block_name = self.current_block.name if self.current_block else "N/A"

        help_info = [
            "=== Управление ===",
            "ПРОБЕЛ: Начать движение / остановить точку / продолжить",
            "H: Показать справку",
            "S: Сохранить данные",
            "ESC: Выход",
            f"Текущий блок: {self.progress_info['block_number']}/{self.progress_info['total_blocks']} - {block_name}",
            f"Текущая задача: {self.current_task.name}",
            f"Тип: {'С траекторией' if self.current_task.has_trajectory else 'Без траектории'}",
            f"Прогресс: {self.progress_info['trial_in_block']}/{self.progress_info['total_trials_in_block']} попыток",
        ]

        print("\n".join(help_info))

    def save_current_data(self):
        """Сохранение текущих данных блока"""
        if self.data_collector and self.data_collector.get_all_data():
            filename = save_experiment_data(
                self.config.participant_id,
                self.progress_info["block_number"],
                self.data_collector.get_all_data(),
            )
            print(
                f"Данные блока {self.progress_info['block_number']} сохранены в файл: {filename}"
            )
            return filename
        else:
            print(
                f"Нет данных для сохранения в блоке {self.progress_info['block_number']}"
            )
            return ""

    def draw_indicator(self):
        """Рисует индикаторную окружность для фото-сенсора"""
        # Определяем цвет в зависимости от состояния
        if self.photo_sensor_state == "passive":
            color = self.photo_sensor_color_passive  # Белый - пассивное состояние
            state_name = "БЕЛЫЙ"
        elif self.photo_sensor_state == "occlusion":
            color = self.photo_sensor_color_occlusion  # Красный при окклюзии
            state_name = "КРАСНЫЙ"
        else:
            color = self.photo_sensor_color_active  # Черный в активном режиме
            state_name = "ЧЕРНЫЙ"

        # Отладочный вывод
        screen_type = (
            self.screen_manager.get_current_screen_type()
            if hasattr(self, "screen_manager")
            else "unknown"
        )
        print(f"[ИНДИКАТОР] Цвет: {state_name}, Экран: {screen_type}")

        # Рисуем индикатор
        pygame.draw.circle(
            self.screen,
            color,
            self.photo_sensor_position,
            self.photo_sensor_radius,
        )
        pygame.draw.circle(
            self.screen,
            (0, 0, 0),  # Черная обводка для контраста
            self.photo_sensor_position,
            self.photo_sensor_radius,
            1,
        )

    def draw_info_panel(self):
        """Отрисовка информационной панели"""
        if self.minimal_mode:
            return

        font = pygame.font.Font(None, 24)

        block_name = self.current_block.name if self.current_block else "N/A"

        info_texts = [
            f"Задача: {self.current_task.name}",
            f"Блок: {self.progress_info['block_number']}/{self.progress_info['total_blocks']} - {block_name}",
            f"Прогресс: {self.progress_info['trial_in_block']}/{self.progress_info['total_trials_in_block']}",
            f"Тип: {'С траекторией' if self.current_task.has_trajectory else 'Без траектории'}",
        ]

        y_positions = [
            self.screen_height - 120,
            self.screen_height - 95,
            self.screen_height - 70,
            self.screen_height - 45,
        ]

        for i, text in enumerate(info_texts):
            rendered_text = font.render(text, True, (0, 0, 0))
            self.screen.blit(rendered_text, (10, y_positions[i]))

    def toggle_minimal_mode(self):
        """Переключает минималистичный режим"""
        self.minimal_mode = not self.minimal_mode
        mode = "МИНИМАЛИСТИЧНЫЙ" if self.minimal_mode else "ПОЛНЫЙ"
        print(f"Режим переключен: {mode}")

    def handle_special_screens(self, event):
        """Обработка специальных экранов"""
        # Обработка крестика для задачи со звездочкой (C2)
        if self.showing_cross_for_star:
            print(
                f"[C2 handle_special_screens] showing_cross_for_star=True, событие: {event}"
            )
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                print(f"[C2] Нажат пробел на крестике")
                # Нажатие пробела - начинаем оценку времени
                self.showing_cross_for_star = False
                self.cross_for_star = None

                # Меняем фотосенсор на черный для оценки времени
                self.photo_sensor_state = "active"
                print(
                    f"[C2] Начинаем оценку времени после крестика. Фактическое время: {self.pending_timing_duration}мс"
                )
                print("[C2] Фотосенсор: черный (оценка времени)")

                self.timing_screen.activate(self.pending_timing_duration)
                return True
            return False

        # Обработка экрана оценки времени (C2)
        if self.timing_screen.is_active:
            print(f"[C2] Обработка оценки времени, событие: {event}")
            if self.timing_screen.handle_event(event):
                timing_results = self.timing_screen.get_results()
                self.data_collector.record_timing_estimation(timing_results)
                self.timing_screen.deactivate()

                # После оценки времени сразу переходим к следующей попытке
                self.complete_and_continue()
                print(
                    f"[C2] Оценка времени завершена! Фактическое: {timing_results['actual_duration']}мс, Оцененное: {timing_results['estimated_duration']}мс"
                )
                return True

        # Обработка задачи воспроизведения (C3) - ИСПРАВЛЕНИЕ ЗДЕСЬ
        elif self.reproduction_task.is_active:
            print(f"[C3] Обработка задачи воспроизведения, событие: {event}")

            # ВАЖНОЕ ИСПРАВЛЕНИЕ:
            # Если задача воспроизведения уже активна, пробел должен обрабатываться только в ней,
            # а не в основном обработчике KeyHandler
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                print(f"[C3] Пробел обрабатывается в handle_special_screens")
                if hasattr(self.reproduction_task, "state"):
                    current_state = self.reproduction_task.state
                    print(f"[C3] Текущее состояние: {current_state}")

                    # В этих состояниях пробел НЕ должен пропускаться в KeyHandler
                    states_to_handle = [
                        "first_cross_waiting",
                        "second_cross_waiting",
                        "response_waiting",
                    ]
                    if current_state in states_to_handle:
                        print(f"[C3] Пробел обрабатывается только в reproduction_task")
                        if self.reproduction_task.handle_event(event):
                            reproduction_results = self.reproduction_task.get_results()

                            # Добавляем задержку из data_collector в результаты
                            if hasattr(self.data_collector, "get_start_delay"):
                                reproduction_results["start_delay_from_data"] = (
                                    self.data_collector.get_start_delay()
                                )

                            self.data_collector.record_reproduction_results(
                                reproduction_results
                            )

                            if hasattr(self.reproduction_task, "deactivate"):
                                self.reproduction_task.deactivate()
                            else:
                                self.reproduction_task.is_active = False

                            self.complete_and_continue()
                            print(
                                f"[C3] Воспроизведение завершено! Целевое: {reproduction_results['target_duration']}мс, Воспроизведенное: {reproduction_results['reproduced_duration']}мс"
                            )
                            if reproduction_results.get("start_delay"):
                                print(
                                    f"[C3] Задержка C3: {reproduction_results['start_delay']}мс"
                                )
                            return True
            return False

        return False

    def update_moving_point(self, dt):
        """Обновление движущейся точки (только для задач с траекторией)"""
        if not self._can_update_point():
            return

        if self.moving_point is not None:
            # ВСЕГДА обновляем точку - она сама решит, что делать в своем состоянии
            self.moving_point.update(dt)

            current_time = pygame.time.get_ticks()

            # Запись начала окклюзии и изменение цвета фотосенсора
            if (
                not self.state.occlusion_started
                and self.moving_point.occlusion_enabled
                and not self.moving_point.is_visible
            ):
                self.data_collector.record_occlusion_start(self.moving_point)
                self.state.occlusion_started = True
                self.photo_sensor_state = "occlusion"  # Устанавливаем красный цвет
                print("Точка вошла в зону окклюзии - фотосенсор красный")

            # Сброс цвета фотосенсора когда точка снова становится видимой
            elif (
                self.state.occlusion_started
                and self.moving_point.is_visible
                and self.photo_sensor_state == "occlusion"
            ):
                self.photo_sensor_state = "active"  # Возвращаем черный цвет
                print("Точка вышла из зоны окклюзии - фотосенсор черный")

            # Проверка завершения траектории
            if self.moving_point.should_switch_to_next():
                self.handle_trajectory_completion(current_time)

    def _can_update_point(self):
        """Проверка возможности обновления точки"""
        return (
            not self.state.waiting_for_initial_start
            and not self.state.waiting_for_movement_start
            and not self.timing_screen.is_active
            and not self.reproduction_task.is_active
            and not self.showing_cross_for_star
            and self.moving_point is not None
            and self.current_task.has_trajectory
        )

    def handle_trajectory_completion(self, current_time):
        """Обработка завершения траектории"""
        actual_duration = current_time - self.start_time
        self.data_collector.record_movement_end()

        # Сбрасываем состояние фотосенсора при завершении траектории
        if self.photo_sensor_state == "occlusion":
            self.photo_sensor_state = "active"
            print("Траектория завершена - сброс фотосенсора в черный цвет")

        if self.current_task.timing_estimation:
            # Для задач с оценкой времени при автоматическом завершении
            print(
                f"[C2] Траектория завершена автоматически! Время: {actual_duration}мс"
            )
            self.pending_timing_duration = actual_duration

            # Создаем крестик для показа
            self.cross_for_star = FixationCross(
                self.screen_width,
                self.screen_height,
                FixationShape.CROSS,
                self.config.fixation_size,
            )
            self.cross_for_star.set_color(self.config.fixation_color)

            # Устанавливаем флаг показа крестика
            self.showing_cross_for_star = True
            self.cross_for_star_start_time = current_time

            # Фотосенсор белый для крестика
            self.photo_sensor_state = "passive"

            print(
                "[C2] Траектория завершена автоматически. Показан крестик для задачи со звездочкой."
            )
            print("[C2] Фотосенсор: белый (крестик C2)")
        else:
            self.handle_regular_task(actual_duration, current_time)

    def handle_regular_task(self, actual_duration, current_time):
        """Обработка регулярной задачи (автоматическое завершение траектории)"""
        self.data_collector.record_space_press(stopped_by_user=False, was_visible=True)
        self.data_collector.record_trajectory_duration(actual_duration)
        self.data_collector.record_movement_end()

        # ДЛЯ ВСЕХ ТИПОВ ЗАДАЧ: сразу переходим к следующей попытке
        self.complete_and_continue()
        print(
            f"Траектория завершена автоматически! Время: {actual_duration}мс - сразу переходим к следующей"
        )

    def update_moving_point_logic(self, dt):
        """Логика для движущейся точки"""
        if self.moving_point is None:
            return

        current_time = pygame.time.get_ticks()

        # Запись начала окклюзии
        if (
            not self.state.occlusion_started
            and self.moving_point.occlusion_enabled
            and not self.moving_point.is_visible
        ):
            if hasattr(self, "data_collector") and self.data_collector:
                self.data_collector.record_occlusion_start(self.moving_point)
            self.state.occlusion_started = True
            self.photo_sensor_state = "occlusion"
            print("Точка вошла в окклюзию")

        # Сброс окклюзии
        elif (
            self.state.occlusion_started
            and self.moving_point.is_visible
            and self.photo_sensor_state == "occlusion"
        ):
            self.photo_sensor_state = "active"
            print("Точка вышла из окклюзии")

        # Если точка движется и не в окклюзии - фотосенсор черный
        elif self.moving_point.is_moving and self.photo_sensor_state != "occlusion":
            self.photo_sensor_state = "active"

        # Проверка завершения траектории
        if self.moving_point.should_switch_to_next():
            self.handle_trajectory_completion(current_time)

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
                    if self.handle_special_screens(event):
                        continue
                    else:
                        self.key_handler.handle_event(event)

            # Обновляем состояния
            if self.moving_point is not None and self.current_task.has_trajectory:
                self.moving_point.update(dt)

                # Проверяем, завершилась ли задержка
                if (
                    self.state.in_start_delay
                    and not self.moving_point.is_in_start_delay
                ):
                    self.state.in_start_delay = False
                    print("✓ Состояние: задержка завершена")

                    # Меняем фотосенсор на черный при начале движения
                    self.photo_sensor_state = "active"
                    print("Фотосенсор: черный (начало движения)")

                # Проверяем, началось ли движение
                if not self.state.movement_started and self.moving_point.is_moving:
                    self.state.movement_started = True
                    if hasattr(self, "data_collector") and self.data_collector:
                        self.data_collector.record_movement_start()
                    print("✓ Состояние: движение началось")

                # Если точка движется, выполняем дополнительную логику
                if self.moving_point.is_moving:
                    self.update_moving_point_logic(dt)

                    # Обновление состояния для задачи воспроизведения (C3)
            if self.reproduction_task.is_active:
                self.reproduction_task.update()

                # ИСПРАВЛЕНИЕ: ДЛЯ C3 - правильная логика индикатора
                if hasattr(self.reproduction_task, "state"):
                    current_state = self.reproduction_task.state

                    # Состояния с КРЕСТИКОМ - БЕЛЫЙ индикатор:
                    # - first_cross_waiting (первый крестик с инструкцией)
                    # - in_start_delay (задержка - крестик без инструкции)
                    # - second_cross_waiting (второй крестик с инструкцией)
                    if current_state in [
                        "first_cross_waiting",
                        "in_start_delay",
                        "second_cross_waiting",
                    ]:
                        self.photo_sensor_state = "passive"  # Белый
                        print(
                            f"[C3] Фотосенсор: белый (крестик, состояние: {current_state})"
                        )

                    # Состояния с КРУГОМ - ЧЕРНЫЙ индикатор:
                    # - first_circle_auto (круг на декодированное время)
                    # - response_waiting (круг для ответа с инструкцией)
                    elif current_state in ["first_circle_auto", "response_waiting"]:
                        self.photo_sensor_state = "active"  # Черный
                        print(
                            f"[C3] Фотосенсор: черный (круг, состояние: {current_state})"
                        )

            # Отрисовка
            self.screen.fill(self.BACKGROUND_COLOR)
            self.screen_manager.draw_current_screen()

            pygame.display.flip()

        self.cleanup()

    def cleanup(self):
        """Очистка ресурсов"""
        try:
            if (
                hasattr(self, "data_collector")
                and self.data_collector
                and self.data_collector.get_all_data()
            ):
                block_number = 1
                if (
                    hasattr(self, "progress_info")
                    and self.progress_info
                    and "block_number" in self.progress_info
                ):
                    block_number = self.progress_info["block_number"]
                elif (
                    hasattr(self, "block_manager")
                    and self.block_manager
                    and not self.block_manager.is_experiment_complete()
                ):
                    block_number = self.block_manager.current_block_index + 1

                filename = save_experiment_data(
                    self.config.participant_id,
                    block_number,
                    self.data_collector.get_all_data(),
                )
                print(f"✅ Данные сохранены в файл: {filename}")
            else:
                print("ℹ️ Нет данных для сохранения")

        except Exception as e:
            print(f"❌ Ошибка при сохранении данных: {e}")
            try:
                if (
                    hasattr(self, "data_collector")
                    and self.data_collector
                    and self.data_collector.get_all_data()
                ):
                    filename = save_experiment_data(
                        "unknown",
                        1,
                        self.data_collector.get_all_data(),
                    )
                    print(f"✅ Данные экстренно сохранены в: {filename}")
            except Exception as e2:
                print(f"💥 Критическая ошибка сохранения: {e2}")

        pygame.mouse.set_visible(True)
        pygame.quit()
        sys.exit()


def main() -> None:
    """Основная функция"""
    experiment = Experiment()
    experiment.run()


if __name__ == "__main__":
    main()
