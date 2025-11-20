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
        self.is_active = False
        self.start_time = 0
        self.duration = 900  # 900 мс
        self.background_color = (255, 255, 255)

        # Создаем фиксационную точку (будет установлена форма позже)
        self.fixation_preview = FixationCross(
            screen_width, screen_height, FixationShape.TRIANGLE, fixation_size
        )
        self.fixation_preview.set_color((0, 0, 0))

    def activate(self, fixation_shape: FixationShape) -> None:
        """Активирует экран предпоказа фиксационной точки"""
        self.is_active = True
        self.start_time = pygame.time.get_ticks()
        # Устанавливаем форму фиксационной точки
        self.fixation_preview.set_shape(fixation_shape)
        print(f"Активирован экран предпоказа {fixation_shape.value} (900 мс)")

    def deactivate(self) -> None:
        """Деактивирует экран"""
        self.is_active = False

    def update(self) -> bool:
        """Обновляет состояние и возвращает True если время истекло"""
        if not self.is_active:
            return False

        current_time = pygame.time.get_ticks()
        if current_time - self.start_time >= self.duration:
            self.deactivate()
            print(f"Экран предпоказа {self.fixation_preview.shape.value} завершен")
            return True
        return False

    def draw(self, screen: pygame.Surface) -> None:
        """Рисует экран с фиксационной точкой"""
        if not self.is_active:
            return

        # Белый фон
        screen.fill(self.background_color)

        # Рисуем фиксационную точку в центре
        self.fixation_preview.draw(screen)


class ExperimentState:
    """Класс для управления состоянием эксперимента"""

    def __init__(self) -> None:
        self.waiting_for_initial_start = True
        self.waiting_for_instruction = False
        self.waiting_for_timing_delay = False
        self.movement_started = False
        self.occlusion_started = False
        self.running = True
        self.instruction_delay_timer = 0
        self.timing_delay_timer = 0
        self.INSTRUCTION_DELAY = 900
        self.TIMING_DELAY = 900


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

    def _can_stop_point(self) -> bool:
        """Проверка возможности остановки точки"""
        exp = self.experiment
        return (
            not exp.instruction_screen.is_active
            and not exp.state.waiting_for_initial_start
            and not exp.timing_screen.is_active
            and not exp.reproduction_task.is_active
            and not exp.state.waiting_for_timing_delay
            and not exp.fixation_preview_screen.is_active  # Нельзя останавливать во время показа фиксации
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
            not exp.instruction_screen.is_active
            and not exp.state.waiting_for_initial_start
            and not exp.timing_screen.is_active
            and not exp.reproduction_task.is_active
            and not exp.fixation_preview_screen.is_active
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
            "fixation_preview": self.draw_fixation_preview,
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
        elif exp.fixation_preview_screen.is_active:
            return "fixation_preview"
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

    def draw_fixation_preview(self):
        """Отрисовка экрана предпоказа фиксационной точки"""
        self.experiment.fixation_preview_screen.draw(self.experiment.screen)

    def draw_main_screen(self):
        """Отрисовка основного экрана"""
        exp = self.experiment

        # Если активна специальная задача - НЕ рисуем основной интерфейс
        if (
            exp.reproduction_task.is_active
            or exp.timing_screen.is_active
            or exp.fixation_preview_screen.is_active
        ):
            return

        # Рисуем фиксационную точку
        exp.fixation.draw(exp.screen)

        # Рисуем траекторию и точку только для задач с траекторией
        if exp.current_task.has_trajectory:
            exp.trajectory_manager.draw_current(exp.screen)
            if exp.moving_point is not None:
                exp.moving_point.draw(exp.screen)

        exp.instruction_screen.draw(exp.screen)
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

        # Объявляем переменные
        self.current_block = None
        self.current_trial: Dict[str, Any] = {}
        self.progress_info: Dict[str, Any] = {}

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
        self.photo_sensor_state = "active"

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
                print("Ошибка: текущий блок не определен")
                return

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
        """Расчет параметров траектории (только для задач с траекторией)"""
        # ИСПРАВЛЕНИЕ: Используем декодированные параметры для получения правильной скорости
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

        self.calculated_duration = 0.0
        if self.trajectory_manager.current_trajectory is not None and hasattr(
            self.trajectory_manager.current_trajectory, "calculate_duration"
        ):
            self.calculated_duration = (
                self.trajectory_manager.current_trajectory.calculate_duration(
                    self.assigned_speed
                )
            )
            print(f"РАСЧЕТ ДЛИТЕЛЬНОСТИ В MAIN: {self.calculated_duration:.0f} мс")

    def create_moving_point(self):
        """Создание движущейся точки (только для задач с траекторией)"""
        if self.trajectory_manager.current_trajectory is not None:
            # ИСПОЛЬЗУЕМ ОБНОВЛЕННУЮ СКОРОСТЬ
            print(f"=== CREATE MOVING POINT ===")
            print(f"  assigned_speed: {self.assigned_speed} px/кадр")
            print(f"  type: {type(self.assigned_speed)}")

            # ПРОВЕРКА: убедимся, что assigned_speed правильный
            if hasattr(self, "current_trial") and self.current_trial:
                print(f"  Скорость из current_trial: {self.current_trial.get('speed')}")

            self.moving_point = MovingPoint(
                self.trajectory_manager.current_trajectory,
                speed=self.assigned_speed,  # Используем обновленное значение
                occlusion_type=(
                    self.current_task.occlusion_type
                    if self.current_task.occlusion_enabled
                    else "none"
                ),
                occlusion_range=self.current_task.occlusion_range,
                occlusion_delay=500,
            )

            # ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА: убедимся, что скорость установлена правильно
            print(f"  Скорость в созданной точке: {self.moving_point.speed} px/кадр")
            print(f"  Тип скорости в точке: {type(self.moving_point.speed)}")

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
            "• ПРОБЕЛ - остановить точку / продолжить",
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

        # ПРОВЕРКА: Расчет времени через разные методы
        time_method1 = reference_response_time
        time_method2 = (total_length / (speed_px_per_frame * 60)) * 1000  # через px/сек
        time_method3 = trajectory.calculate_duration(speed_px_per_frame)

        print(f"  Проверка расчетов:")
        print(f"    Метод 1 (кадры): {time_method1:.0f} мс")
        print(f"    Метод 2 (px/сек): {time_method2:.0f} мс")
        print(f"    Метод 3 (trajectory): {time_method3:.0f} мс")

        stimulus_presentation_time = 0.0
        trajectory_completion_time = reference_response_time

        self.data_collector.record_reference_times(
            reference_response_time,
            stimulus_presentation_time,
            trajectory_completion_time,
        )

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

        # ПРОВЕРКА СКОРОСТИ ПЕРЕД ЗАПИСЬЮ ДАННЫХ
        print(f"ПРОВЕРКА СКОРОСТИ ПЕРЕД START_NEW_TRIAL:")
        print(f"  current_trial speed: {self.current_trial.get('speed')}")
        print(f"  assigned_speed: {self.assigned_speed}")
        print(f"  decoded_params speed: {decoded_params.get('speed')}")

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
            speed=(
                self.assigned_speed if self.current_task.has_trajectory else 0
            ),  # Используем assigned_speed
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
        )

        # Для задач с траекторией рассчитываем эталонные времена
        if self.current_task.has_trajectory:
            self.calculate_reference_times()

        # ДЛЯ ЗАДАЧ ВОСПРОИЗВЕДЕНИЯ: сразу активируем задачу
        if self.current_task.reproduction_task:
            assigned_duration = (
                self.current_trial["duration"]
                if self.current_trial["duration"] is not None
                else self.config.available_durations[0]
            )
            print(
                f"Непосредственный запуск задачи воспроизведения с длительностью {assigned_duration}мс"
            )
            self.reproduction_task.activate(assigned_duration)

        # ДЛЯ ВСЕХ ЗАДАЧ С ТРАЕКТОРИЕЙ: активируем предпоказ фиксационной точки
        elif self.current_task.has_trajectory:
            self.fixation_preview_screen.activate(self.current_task.fixation_shape)
            print(
                f"Активирован предпоказ {self.current_task.fixation_shape.value} перед траекторией"
            )

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
                if self.current_task.occlusion_type == "timed":
                    info_lines.append(
                        "Окклюзия по времени: через 500мс после начала движения"
                    )
                elif self.current_task.occlusion_range:
                    info_lines.append(
                        f"Диапазон окклюзии: [{self.current_task.occlusion_range[0]:.1f}, {self.current_task.occlusion_range[1]:.1f}]"
                    )

        if self.current_task.timing_estimation:
            info_lines.append("Оценка времени после остановки: ДА")

        if self.current_task.reproduction_task:
            info_lines.extend(
                [
                    "Воспроизведение времени: ДА",
                    f"Назначенная длительность: {self.current_trial['duration']} мс",
                ]
            )

        print("\n".join(info_lines))

    def handle_instruction_continue(self):
        """Обработка продолжения после инструкции"""
        self.state.waiting_for_instruction = False

        # Определяем, завершена ли попытка нормально
        completed_normally = True
        if self.current_task.has_trajectory and self.moving_point is not None:
            completed_normally = not self.moving_point.stopped_by_user

        self.data_collector.complete_trial(completed_normally=completed_normally)

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

    def handle_block_completion(self):
        """Обработка завершения блока"""
        # Сохраняем данные текущего блока
        self.save_current_data()

        # Создаем новый сборщик данных для нового блока
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
        self.photo_sensor_state = "active"

        # Обновляем фиксационную точку
        self.fixation.set_shape(self.current_task.fixation_shape)

        # Для задач с траекторией: загружаем траекторию и создаем/обновляем точку
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
            # Для задач без траектории: освобождаем движущуюся точку
            self.moving_point = None

        # Сбрасываем состояние
        self.start_time = pygame.time.get_ticks()
        self.state.movement_started = False
        self.state.occlusion_started = False
        self.state.instruction_delay_timer = 0
        self.state.waiting_for_timing_delay = False
        self.state.timing_delay_timer = 0

        # Начинаем новую попытку
        self.start_new_trial()
        self.print_current_trial_info()

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

        # Для задач с оценкой времени: устанавливаем задержку перед оценкой
        if self.current_task.timing_estimation:
            self.state.timing_delay_timer = pygame.time.get_ticks()
            self.state.waiting_for_timing_delay = True
            print(
                f"Установлена задержка 900 мс перед оценкой времени. Фактическое время движения: {actual_duration}мс"
            )
        else:
            # Для обычных задач: показываем инструкцию после задержки
            self.state.instruction_delay_timer = pygame.time.get_ticks()
            self.state.waiting_for_instruction = True

        reaction_time = self.space_press_time - self.start_time
        print(f"Пользователь остановил точку! Время реакции: {reaction_time}мс")

    def handle_timing_after_stop(self, actual_duration: float):
        """Обработка оценки времени после остановки точки пользователем"""
        print(
            f"Запуск оценки времени после остановки! Фактическое время: {actual_duration}мс"
        )
        self.timing_screen.activate(actual_duration)

    def show_help_info(self):
        """Показать информацию о управлении"""
        block_name = self.current_block.name if self.current_block else "N/A"

        help_info = [
            "=== Управление ===",
            "ПРОБЕЛ: Остановить точку / продолжить",
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
        if (
            self.state.waiting_for_initial_start
            and self.initial_instruction_screen.is_active
        ) or self.instruction_screen.is_active:
            color = self.photo_sensor_color_passive
            self.photo_sensor_state = "passive"
        elif self.photo_sensor_state == "occlusion":
            color = self.photo_sensor_color_occlusion  # Красный при окклюзии
        else:
            color = self.photo_sensor_color_active  # Черный в активном режиме
            self.photo_sensor_state = "active"

        pygame.draw.circle(
            self.screen, color, self.photo_sensor_position, self.photo_sensor_radius
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
        # Обработка экрана оценки времени (после остановки точки)
        if self.timing_screen.is_active:
            if self.timing_screen.handle_event(event):
                timing_results = self.timing_screen.get_results()
                self.data_collector.record_timing_estimation(timing_results)
                self.timing_screen.deactivate()
                self.data_collector.complete_trial(completed_normally=True)
                self.instruction_screen.activate()
                print(
                    f"Оценка времени завершена! Фактическое: {timing_results['actual_duration']}мс, Оцененное: {timing_results['estimated_duration']}мс"
                )
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
                return True

        return False

    def update_moving_point(self, dt):
        """Обновление движущейся точки (только для задач с траекторией)"""
        if not self._can_update_point():
            return

        if self.moving_point is not None:
            # Запускаем отсчет времени при первом обновлении
            if (
                self.moving_point.movement_start_time is None
                and self.moving_point.is_moving
            ):
                self.moving_point.start_movement()
                print("Отсчет времени для окклюзии запущен")

            self.moving_point.update(dt)
            current_time = pygame.time.get_ticks()

            # Запись начала движения
            if not self.state.movement_started and self.moving_point.is_moving:
                self.data_collector.record_movement_start()
                self.state.movement_started = True

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
            and not self.state.waiting_for_timing_delay
            and not self.fixation_preview_screen.is_active  # Не обновляем точку во время показа фиксации
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
            self.handle_timing_after_stop(actual_duration)
        else:
            self.handle_regular_task(actual_duration, current_time)

    def handle_regular_task(self, actual_duration, current_time):
        """Обработка регулярной задачи"""
        self.data_collector.record_space_press(stopped_by_user=False, was_visible=True)
        self.data_collector.record_trajectory_duration(actual_duration)
        self.data_collector.record_movement_end()

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
            and not self.current_task.timing_estimation  # Не показываем задержку для задач с оценкой времени
        ):
            self.instruction_screen.activate()
            self.state.waiting_for_instruction = False
            print("Показ инструкции 'Нажмите ПРОБЕЛ чтобы продолжить'...")

    def check_timing_delay(self, current_time):
        """Проверка задержки перед показом экрана оценки времени"""
        if (
            self.state.waiting_for_timing_delay
            and not self.timing_screen.is_active
            and current_time - self.state.timing_delay_timer >= self.state.TIMING_DELAY
        ):
            actual_duration = 0
            if (
                self.state.movement_started
                and self.data_collector.current_trial_data["movement_start_time"]
            ):
                actual_duration = (
                    self.state.timing_delay_timer
                    - self.data_collector.current_trial_data["movement_start_time"]
                )

            self.state.waiting_for_timing_delay = False
            self.handle_timing_after_stop(actual_duration)
            print("Задержка завершена, запуск экрана оценки времени...")

    def check_fixation_preview(self, current_time):
        """Проверка завершения показа фиксационной точки"""
        if self.fixation_preview_screen.is_active:
            if self.fixation_preview_screen.update():
                # Фиксационная точка показана достаточно времени, начинаем движение
                self.start_time = pygame.time.get_ticks()
                print("Начинаем движение точки после показа фиксационной точки")

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

            # Обновление состояния
            if self.reproduction_task.is_active:
                self.reproduction_task.update()
            elif self.timing_screen.is_active:
                # timing_screen обновляется через события
                pass
            elif self.fixation_preview_screen.is_active:  # Сначала фиксационная точка
                self.check_fixation_preview(current_time)
            elif (
                self.current_task.has_trajectory
                and not self.timing_screen.is_active
                and not self.instruction_screen.is_active
            ):
                # Только после фиксационной точки начинаем движение
                self.update_moving_point(dt)

            # Проверка задержки инструкции
            self.check_instruction_delay(current_time)

            # Проверка задержки перед оценкой времени
            self.check_timing_delay(current_time)

            # Отрисовка
            self.screen.fill(self.BACKGROUND_COLOR)
            self.screen_manager.draw_current_screen()
            pygame.display.flip()

        self.cleanup()

    def cleanup(self):
        """Очистка ресурсов"""
        # ВСЕГДА сохраняем данные при завершении, независимо от способа выхода
        try:
            if not self.block_manager.is_experiment_complete():
                print(f"\n=== Завершение эксперимента (досрочное) ===")
                self.save_current_data()
            else:
                print(f"\n=== Эксперимент завершен (нормально) ===")
                # Данные уже сохранены в handle_instruction_continue, но для надежности сохраняем еще раз
                if self.data_collector and self.data_collector.get_all_data():
                    self.save_current_data()
        except Exception as e:
            print(f"Ошибка при сохранении данных в cleanup: {e}")
            # Пытаемся сохранить с значениями по умолчанию
            try:
                if self.data_collector and self.data_collector.get_all_data():
                    filename = save_experiment_data(
                        self.config.participant_id,
                        1,  # блок по умолчанию
                        self.data_collector.get_all_data(),
                    )
                    print(f"Данные сохранены в файл: {filename}")
            except Exception as e2:
                print(f"Критическая ошибка при сохранении: {e2}")

        pygame.mouse.set_visible(True)
        pygame.quit()
        sys.exit()


def main() -> None:
    """Основная функция"""
    experiment = Experiment()
    experiment.run()


if __name__ == "__main__":
    main()
