from typing import List, Dict, Any, Optional
from exp_config import BlockConfig


class BlockManager:
    def __init__(
        self,
        trajectories_data: Dict[str, Any],
        blocks: List[BlockConfig],
        available_speeds: List[float],
        available_durations: List[int],
    ) -> None:
        self.trajectories_data: Dict[str, Any] = trajectories_data
        self.available_speeds: List[float] = available_speeds
        self.available_durations: List[int] = available_durations

        # СОЗДАЕМ БЛОКИ ИЗ СТРУКТУРЫ ФАЙЛА
        self.blocks = self._create_blocks_from_file_structure()
        self.current_block_index = 0
        self.current_trial_index = 0

        # Генерируем последовательности для всех блоков
        self.block_sequences = []
        for block_index, block in enumerate(self.blocks):
            print(f"Обработка блока {block_index + 1}: '{block.name}'")
            trial_sequence = self._generate_trial_sequence_for_block(block)
            print(f"  Создано {len(trial_sequence)} попыток")
            self.block_sequences.append(trial_sequence)

    def _create_blocks_from_file_structure(self) -> List[BlockConfig]:
        """Создает блоки на основе структуры файла"""
        blocks = []

        print("=" * 50)
        print("СОЗДАНИЕ БЛОКОВ ИЗ ФАЙЛА:")
        print("=" * 50)

        for block_name in sorted(self.trajectories_data.keys()):
            # Для каждого блока в файле создаем BlockConfig
            block = BlockConfig(
                name=block_name,
                tasks_distribution={},  # Не используется в новой системе
                trajectories_category=block_name,  # Используем имя блока как категорию
            )
            blocks.append(block)
            print(f"Создан блок: {block_name}")

        print(f"Всего создано {len(blocks)} блоков")
        print("=" * 50)

        return blocks

    def _generate_trial_sequence_for_block(
        self, block: BlockConfig
    ) -> List[Dict[str, Any]]:
        """Генерирует последовательность попыток для конкретного блока"""
        trials = []
        block_data = self.trajectories_data[block.name]

        print(f"  Генерация попыток для блока '{block.name}':")

        # Проходим по всем категориям в блоке в порядке их следования в файле
        for category, trajectories in block_data.items():
            # Игнорируем нижнее подчеркивание в названии категории для декодирования
            clean_category = category.split("_")[0]  # Убираем _1, _2 и т.д.

            # Декодируем параметры из названия категории
            from exp_config import ExperimentConfig

            config = ExperimentConfig()
            decoded_params = config.decode_category(clean_category)

            print(f"    Категория: {category} -> {clean_category}")
            print(
                f"      Задача: {decoded_params['task_index']}, "
                f"Скорость: {decoded_params['speed']}, "
                f"Длительность: {decoded_params['duration']}"
            )
            print(f"      Траекторий в категории: {len(trajectories)}")

            # Создаем попытки для всех траекторий в этой категории
            for trajectory_idx in range(len(trajectories)):
                trial = {
                    "task_type": decoded_params["task_index"],
                    "speed": decoded_params["speed"],
                    "duration": decoded_params["duration"],
                    "trajectory_index": trajectory_idx,
                    "actual_trajectory_category": category,  # Оригинальное название с _ если есть
                    "decoded_params": decoded_params,
                    "block_name": block.name,
                    "trial_in_block": len(trials) + 1,
                    "display_order": len(trials) + 1,
                }
                trials.append(trial)

        print(f"    Всего создано {len(trials)} попыток для блока {block.name}")
        return trials

    def get_current_block(self) -> Optional[BlockConfig]:
        """Возвращает текущий блок"""
        if self.current_block_index < len(self.blocks):
            return self.blocks[self.current_block_index]
        else:
            return None

    def get_current_trial(self) -> Dict[str, Any]:
        """Возвращает текущую попытку"""
        if self.current_block_index < len(self.block_sequences):
            block_trials = self.block_sequences[self.current_block_index]
            if self.current_trial_index < len(block_trials):
                return block_trials[self.current_trial_index]

        return {}

    def move_to_next_trial(self) -> bool:
        """Переходит к следующей попытке, возвращает True если блок завершен"""
        self.current_trial_index += 1

        if self.current_trial_index >= len(
            self.block_sequences[self.current_block_index]
        ):
            # Блок завершен
            self.current_trial_index = 0
            self.current_block_index += 1

            # Проверяем, не вышли ли за пределы списка блоков
            if self.current_block_index >= len(self.blocks):
                return True  # Эксперимент завершен

            return True  # Блок завершен, но эксперимент продолжается
        return False

    def is_experiment_complete(self) -> bool:
        """Проверяет, завершен ли эксперимент"""
        return self.current_block_index >= len(self.blocks)

    def get_progress_info(self) -> Dict[str, Any]:
        """Возвращает информацию о прогрессе"""
        if self.is_experiment_complete():
            return {
                "block_number": len(self.blocks),
                "total_blocks": len(self.blocks),
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
                "decoded_params": {},
            }

        current_block = self.get_current_block()
        current_trial = self.get_current_trial()

        if not current_block or not current_trial:
            return {
                "block_number": 0,
                "total_blocks": len(self.blocks),
                "trial_in_block": 0,
                "display_order": 0,
                "total_trials_in_block": 0,
                "block_name": "Ошибка",
                "task_type": 0,
                "trajectory_category": "none",
                "actual_trajectory_category": "none",
                "trajectory_index": 0,
                "speed": None,
                "duration": None,
                "decoded_params": {},
            }

        total_trials_in_block = len(self.block_sequences[self.current_block_index])

        return {
            "block_number": self.current_block_index + 1,
            "total_blocks": len(self.blocks),
            "trial_in_block": current_trial["trial_in_block"],
            "display_order": current_trial["display_order"],
            "total_trials_in_block": total_trials_in_block,
            "block_name": current_trial[
                "block_name"
            ],  # Используем оригинальное имя блока
            "task_type": current_trial["task_type"],
            "trajectory_category": current_block.name,
            "actual_trajectory_category": current_trial["actual_trajectory_category"],
            "trajectory_index": current_trial["trajectory_index"],
            "speed": current_trial.get("speed"),
            "duration": current_trial.get("duration"),
            "decoded_params": current_trial.get("decoded_params", {}),
        }
