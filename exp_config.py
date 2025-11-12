from fixation import FixationShape
from typing import Dict, Any, Tuple, List
import random


class TaskConfig:
    """Конфигурация отдельной задачи"""

    def __init__(
        self,
        name: str,
        fixation_shape: FixationShape,
        occlusion_enabled: bool = True,
        occlusion_type: str = "half",
        timing_estimation: bool = False,
        reproduction_task: bool = False,
        reproduction_duration: int = 2000,
    ):
        self.name = name
        self.fixation_shape = fixation_shape
        self.occlusion_enabled = occlusion_enabled
        self.occlusion_type = occlusion_type
        self.timing_estimation = timing_estimation
        self.reproduction_task = reproduction_task
        self.reproduction_duration = reproduction_duration

    def to_dict(self) -> Dict[str, Any]:
        """Возвращает настройки задачи в виде словаря"""
        return {
            "name": self.name,
            "fixation_shape": self.fixation_shape.value,
            "occlusion_enabled": self.occlusion_enabled,
            "occlusion_type": self.occlusion_type,
            "timing_estimation": self.timing_estimation,
            "reproduction_task": self.reproduction_task,
            "reproduction_duration": self.reproduction_duration,
        }


class BlockConfig:
    """Конфигурация блока"""

    def __init__(
        self, name: str, tasks_distribution: Dict[int, int], trajectories_category: str
    ):
        """
        tasks_distribution: словарь {тип_задачи: количество_повторений}
        trajectories_category: категория траекторий для этого блока
        """
        self.name = name
        self.tasks_distribution = tasks_distribution
        self.trajectories_category = trajectories_category

    def generate_trial_sequence(
        self, available_speeds: List[float], available_durations: List[int]
    ) -> List[Dict[str, Any]]:
        """Генерирует случайную последовательность попыток для блока"""
        trials = []

        # Создаем список всех попыток согласно распределению
        for task_type, count in self.tasks_distribution.items():
            for i in range(count):
                # Случайно выбираем скорость для задач с траекторией (0,1,2)
                speed = (
                    random.choice(available_speeds) if task_type in [0, 1, 2] else None
                )

                # Случайно выбираем длительность для задач с временем (2,3)
                duration = (
                    random.choice(available_durations) if task_type in [2, 3] else None
                )

                trials.append(
                    {
                        "task_type": task_type,
                        "speed": speed,
                        "duration": duration,
                        "trial_in_block": len(trials) + 1,
                    }
                )

        # Перемешиваем последовательность
        random.shuffle(trials)

        # Добавляем номера попыток после перемешивания
        for i, trial in enumerate(trials):
            trial["display_order"] = i + 1

        return trials


class ExperimentConfig:
    def __init__(self):
        # Настройки по умолчанию
        self.fixation_size = 30
        self.fixation_color: Tuple[int, int, int] = (0, 0, 0)
        self.participant_id = "test_01"

        # Настройки фото-сенсора
        self.photo_sensor_radius = 20  # Размер окружности
        self.photo_sensor_offset_x = (
            -80
        )  # Смещение от правого края (отрицательное = внутрь экрана)
        self.photo_sensor_offset_y = (
            -80
        )  # Смещение от нижнего края (отрицательное = внутрь экрана)
        self.photo_sensor_color_active = (0, 0, 0)  # Черный - активный экран
        self.photo_sensor_color_passive = (255, 255, 255)  # Белый - инструкция

        # Доступные скорости движения точки (пикселей в кадр), нужен FLOAT!!!
        self.available_speeds = [2.0, 4.0]

        # Доступные длительности для задач с временем (миллисекунды)
        self.available_durations = [500, 1600, 2900]

        # Определяем задачи
        self.tasks: List[TaskConfig] = [
            TaskConfig(
                "Задача 1: Окклюзия (половина)", FixationShape.TRIANGLE, True, "half"
            ),
            TaskConfig("Задача 2: Без окклюзии", FixationShape.RHOMBUS, False, "half"),
            TaskConfig(
                "Задача 3: Оценка времени (без окклюзии)",
                FixationShape.STAR,
                False,
                "half",
                True,
            ),
            TaskConfig(
                "Задача 4: Воспроизведение времени",
                FixationShape.CROSS,
                False,
                "half",
                False,
                True,
                2000,
            ),
        ]

        # Определяем блоки (8 блоков с разными настройками)
        self.blocks: List[BlockConfig] = [
            BlockConfig("Блок 1: Простые траектории", {0: 5, 1: 5, 2: 5, 3: 5}, "R"),
            BlockConfig("Блок 2: Сложные траектории 1", {0: 5, 1: 5, 2: 5, 3: 5}, "H1"),
            BlockConfig("Блок 3: Сложные траектории 2", {0: 5, 1: 5, 2: 5, 3: 5}, "H2"),
            BlockConfig("Блок 4: Средние траектории 1", {0: 5, 1: 5, 2: 5, 3: 5}, "M1"),
            BlockConfig("Блок 5: Средние траектории 2", {0: 5, 1: 5, 2: 5, 3: 5}, "M2"),
            BlockConfig(
                "Блок 6: Короткие траектории 1", {0: 5, 1: 5, 2: 5, 3: 5}, "S1"
            ),
            BlockConfig(
                "Блок 7: Короткие траектории 2", {0: 5, 1: 5, 2: 5, 3: 5}, "S2"
            ),
            BlockConfig(
                "Блок 8: Случайные траектории", {0: 5, 1: 5, 2: 5, 3: 5}, "R"
            ),  # R - случайные из всех категорий
        ]

    def get_current_task_config(self, task_index: int) -> TaskConfig:
        """Возвращает конфигурацию для текущей задачи"""
        if 0 <= task_index < len(self.tasks):
            return self.tasks[task_index]
        else:
            return TaskConfig(
                "Задача по умолчанию", FixationShape.TRIANGLE, True, "half"
            )

    def get_total_tasks(self) -> int:
        """Возвращает общее количество задач"""
        return len(self.tasks)

    def get_total_blocks(self) -> int:
        """Возвращает общее количество блоков"""
        return len(self.blocks)

    def to_dict(self) -> Dict[str, Any]:
        """Возвращает настройки в виде словаря"""
        return {
            "fixation_size": self.fixation_size,
            "fixation_color": self.fixation_color,
            "participant_id": self.participant_id,
            "photo_sensor_radius": self.photo_sensor_radius,
            "photo_sensor_offset_x": self.photo_sensor_offset_x,
            "photo_sensor_offset_y": self.photo_sensor_offset_y,
            "photo_sensor_color_active": self.photo_sensor_color_active,
            "photo_sensor_color_passive": self.photo_sensor_color_passive,
            "available_speeds": self.available_speeds,
            "available_durations": self.available_durations,
            "tasks": [task.to_dict() for task in self.tasks],
            "blocks": [
                {
                    "name": block.name,
                    "tasks_distribution": block.tasks_distribution,
                    "trajectories_category": block.trajectories_category,
                }
                for block in self.blocks
            ],
        }

    def from_dict(self, config_dict: Dict[str, Any]) -> None:
        """Загружает настройки из словаря"""
        self.fixation_size = config_dict.get("fixation_size", 30)

        color_data = config_dict.get("fixation_color", (0, 0, 0))
        if isinstance(color_data, (list, tuple)) and len(color_data) >= 3:
            self.fixation_color = (
                int(color_data[0]),
                int(color_data[1]),
                int(color_data[2]),
            )
        else:
            self.fixation_color = (0, 0, 0)

        self.participant_id = config_dict.get("participant_id", "test_01")

        # Настройки фото-сенсора
        self.photo_sensor_radius = config_dict.get("photo_sensor_radius", 20)
        self.photo_sensor_offset_x = config_dict.get("photo_sensor_offset_x", -50)
        self.photo_sensor_offset_y = config_dict.get("photo_sensor_offset_y", -50)

        active_color_data = config_dict.get("photo_sensor_color_active", (0, 0, 0))
        if isinstance(active_color_data, (list, tuple)) and len(active_color_data) >= 3:
            self.photo_sensor_color_active = (
                int(active_color_data[0]),
                int(active_color_data[1]),
                int(active_color_data[2]),
            )
        else:
            self.photo_sensor_color_active = (0, 0, 0)

        passive_color_data = config_dict.get(
            "photo_sensor_color_passive", (255, 255, 255)
        )
        if (
            isinstance(passive_color_data, (list, tuple))
            and len(passive_color_data) >= 3
        ):
            self.photo_sensor_color_passive = (
                int(passive_color_data[0]),
                int(passive_color_data[1]),
                int(passive_color_data[2]),
            )
        else:
            self.photo_sensor_color_passive = (255, 255, 255)

        self.available_speeds = config_dict.get(
            "available_speeds", [2.0, 2.5, 3.0, 3.5, 4.0]
        )
        self.available_durations = config_dict.get(
            "available_durations", [1500, 2000, 2500, 3000, 3500]
        )

        # Загружаем задачи
        self.tasks = []
        tasks_data = config_dict.get("tasks", [])
        for task_data in tasks_data:
            task = TaskConfig(
                name=task_data.get("name", "Задача"),
                fixation_shape=FixationShape(
                    task_data.get("fixation_shape", "triangle")
                ),
                occlusion_enabled=task_data.get("occlusion_enabled", True),
                occlusion_type=task_data.get("occlusion_type", "half"),
                timing_estimation=task_data.get("timing_estimation", False),
                reproduction_task=task_data.get("reproduction_task", False),
                reproduction_duration=task_data.get("reproduction_duration", 2000),
            )
            self.tasks.append(task)

        # Загружаем блоки
        self.blocks = []
        blocks_data = config_dict.get("blocks", [])
        for block_data in blocks_data:
            block = BlockConfig(
                name=block_data.get("name", "Блок"),
                tasks_distribution=block_data.get(
                    "tasks_distribution", {0: 5, 1: 5, 2: 5, 3: 5}
                ),
                trajectories_category=block_data.get("trajectories_category", "T"),
            )
            self.blocks.append(block)
