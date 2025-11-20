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
        self.blocks: List[BlockConfig] = blocks
        self.available_speeds: List[float] = available_speeds
        self.available_durations: List[int] = available_durations
        self.current_block_index = 0
        self.current_trial_index = 0

        # ВЫВЕДЕМ ВСЕ ДОСТУПНЫЕ КАТЕГОРИИ ДЛЯ ОТЛАДКИ
        print("=" * 50)
        print("ДОСТУПНЫЕ КАТЕГОРИИ ТРАЕКТОРИЙ:")
        print("=" * 50)
        total_trajectories = 0
        for category in sorted(trajectories_data.keys()):
            count = len(trajectories_data[category])
            total_trajectories += count
            print(f"  '{category}': {count} траекторий")
        print(f"ОБЩЕЕ КОЛИЧЕСТВО ТРАЕКТОРИЙ: {total_trajectories}")
        print("=" * 50)

        # Для последовательного выбора: отслеживаем текущий индекс для каждой категории
        self.category_counters: Dict[str, int] = {}

        # Инициализируем счетчики для всех категорий
        for category in trajectories_data.keys():
            self.category_counters[category] = 0

        # Генерируем последовательности для всех блоков
        self.block_sequences = []

        for block_index, block in enumerate(blocks):
            print(f"Обработка блока {block_index + 1}: '{block.name}'")
            print(f"  Запрошенная категория: '{block.trajectories_category}'")

            # Генерируем последовательность попыток для блока
            # Теперь создаем попытки на основе всех доступных траекторий
            trial_sequence = self._generate_sequential_trial_sequence()

            print(f"  Создано {len(trial_sequence)} попыток для блока")

            self.block_sequences.append(trial_sequence)
            print()

    def _generate_sequential_trial_sequence(self) -> List[Dict[str, Any]]:
        """Генерирует последовательность попыток на основе всех доступных траекторий"""
        trials = []

        # Получаем все категории в отсортированном порядке
        available_categories = sorted(self.trajectories_data.keys())

        for category in available_categories:
            # Для каждой категории создаем попытки для всех траекторий
            category_trajectories = self.trajectories_data[category]

            for trajectory_idx in range(len(category_trajectories)):
                # Декодируем параметры из названия категории
                from exp_config import ExperimentConfig

                config = ExperimentConfig()
                decoded_params = config.decode_category(category)

                trial = {
                    "task_type": decoded_params["task_index"],
                    "speed": decoded_params["speed"],
                    "duration": decoded_params["duration"],
                    "trajectory_index": trajectory_idx,
                    "actual_trajectory_category": category,
                    "decoded_params": decoded_params,
                    "trial_in_block": len(trials) + 1,
                    "display_order": len(trials) + 1,
                }

                trials.append(trial)
                print(
                    f"    Создана попытка: {category}[{trajectory_idx}] -> задача={decoded_params['task_index']}, скорость={decoded_params['speed']}, длительность={decoded_params['duration']}"
                )

        print(f"  Всего создано {len(trials)} попыток для всех категорий")
        return trials

    def get_current_block(self) -> Optional[BlockConfig]:
        """Возвращает текущий блок"""
        if self.current_block_index < len(self.blocks):
            return self.blocks[self.current_block_index]
        else:
            return None

    def get_current_trial(self) -> Dict[str, Any]:
        """Возвращает текущую попытку"""
        if self.current_block_index < len(
            self.block_sequences
        ) and self.current_trial_index < len(
            self.block_sequences[self.current_block_index]
        ):
            return self.block_sequences[self.current_block_index][
                self.current_trial_index
            ]
        else:
            # Возвращаем пустой словарь как запасной вариант
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
            # Возвращаем информацию о завершенном эксперименте
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
            "block_name": current_block.name,
            "task_type": current_trial["task_type"],
            "trajectory_category": current_block.trajectories_category,
            "actual_trajectory_category": current_trial.get(
                "actual_trajectory_category", current_block.trajectories_category
            ),
            "trajectory_index": current_trial["trajectory_index"],
            "speed": current_trial.get("speed"),
            "duration": current_trial.get("duration"),
            "decoded_params": current_trial.get("decoded_params", {}),
        }

    def get_used_trajectories_info(self) -> Dict[str, Any]:
        """Возвращает информацию об использованных траекториях (для отладки)"""
        total_trajectories = sum(
            len(trajectories) for trajectories in self.trajectories_data.values()
        )
        used_trajectories = sum(self.category_counters.values())

        return {
            "category_counters": self.category_counters,
            "total_categories": len(self.trajectories_data),
            "total_trajectories": total_trajectories,
            "used_trajectories": used_trajectories,
            "remaining_trajectories": total_trajectories - used_trajectories,
        }
