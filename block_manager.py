import random
from typing import List, Dict, Any
from exp_config import BlockConfig


class BlockManager:
    def __init__(
        self,
        trajectories_data: Dict[str, Any],
        blocks: List[BlockConfig],
        available_speeds: List[float],
        available_durations: List[int],
    ):
        self.trajectories_data = trajectories_data
        self.blocks = blocks
        self.available_speeds = available_speeds
        self.available_durations = available_durations
        self.current_block_index = 0
        self.current_trial_index = 0

        # Глобальный отслеживатель использованных траекторий для всего эксперимента
        self.used_trajectories_global = set()  # Формат: (category, index)

        # Генерируем последовательности для всех блоков
        self.block_sequences = []

        for block in blocks:
            # Генерируем последовательность попыток для блока
            trial_sequence = block.generate_trial_sequence(
                available_speeds, available_durations
            )

            # Для каждой попытки выбираем случайную траекторию
            for trial in trial_sequence:
                category = block.trajectories_category
                trajectory_idx, actual_category = self._get_next_available_trajectory(
                    category
                )
                trial["trajectory_index"] = trajectory_idx
                trial["actual_trajectory_category"] = (
                    actual_category  # Сохраняем реальную категорию
                )

            self.block_sequences.append(trial_sequence)

    def _get_available_categories(self) -> List[str]:
        """Возвращает список доступных категорий траекторий (исключая R)"""
        return [cat for cat in self.trajectories_data.keys() if cat != "R"]

    def _get_random_category(self) -> str:
        """Возвращает случайную категорию из доступных"""
        available_categories = self._get_available_categories()
        if available_categories:
            return random.choice(available_categories)
        return "T"  # Резервный вариант

    def _get_next_available_trajectory(
        self, requested_category: str
    ) -> tuple[int, str]:
        """Возвращает следующую доступную траекторию"""
        # Если запрошена случайная категория (R) - выбираем случайную категорию
        if requested_category == "R":
            actual_category = self._get_random_category()
        else:
            actual_category = requested_category

        if actual_category not in self.trajectories_data:
            return 0, actual_category

        total_trajectories = len(self.trajectories_data[actual_category])

        # Создаем список доступных траекторий для этой категории
        available_trajectories = []
        for i in range(total_trajectories):
            trajectory_key = (actual_category, i)
            if trajectory_key not in self.used_trajectories_global:
                available_trajectories.append(i)

        # Если есть доступные траектории - выбираем случайную
        if available_trajectories:
            trajectory_idx = random.choice(available_trajectories)
            self.used_trajectories_global.add((actual_category, trajectory_idx))
            return trajectory_idx, actual_category

        # Если все траектории использованы - пробуем другую категорию
        if requested_category == "R":
            # Для случайного режима пробуем другую случайную категорию
            available_categories = self._get_available_categories()
            for category in random.sample(
                available_categories, len(available_categories)
            ):
                if category != actual_category:
                    trajectory_idx, new_category = self._get_next_available_trajectory(
                        category
                    )
                    if trajectory_idx != 0:  # Если нашли доступную траекторию
                        return trajectory_idx, new_category

        # Если ничего не нашли - сбрасываем для этой категории
        print(
            f"ВНИМАНИЕ: Все траектории категории {actual_category} использованы, сбрасываем..."
        )

        # Удаляем все использованные траектории этой категории
        trajectories_to_remove = [
            key for key in self.used_trajectories_global if key[0] == actual_category
        ]
        for key in trajectories_to_remove:
            self.used_trajectories_global.remove(key)

        # Пробуем снова
        available_trajectories = list(range(total_trajectories))
        if available_trajectories:
            trajectory_idx = random.choice(available_trajectories)
            self.used_trajectories_global.add((actual_category, trajectory_idx))
            return trajectory_idx, actual_category

        # Резервный вариант
        return 0, actual_category

    def get_current_block(self) -> BlockConfig:
        """Возвращает текущий блок"""
        return self.blocks[self.current_block_index]

    def get_current_trial(self) -> Dict[str, Any]:
        """Возвращает текущую попытку"""
        return self.block_sequences[self.current_block_index][self.current_trial_index]

    def move_to_next_trial(self) -> bool:
        """Переходит к следующей попытке, возвращает True если блок завершен"""
        self.current_trial_index += 1

        if self.current_trial_index >= len(
            self.block_sequences[self.current_block_index]
        ):
            # Блок завершен
            self.current_trial_index = 0
            self.current_block_index += 1
            return True
        return False

    def is_experiment_complete(self) -> bool:
        """Проверяет, завершен ли эксперимент"""
        return self.current_block_index >= len(self.blocks)

    def get_progress_info(self) -> Dict[str, Any]:
        """Возвращает информацию о прогрессе"""
        current_block = self.get_current_block()
        current_trial = self.get_current_trial()
        total_trials_in_block = len(self.block_sequences[self.current_block_index])

        return {
            "block_number": self.current_block_index + 1,
            "total_blocks": len(self.blocks),
            "trial_in_block": current_trial["trial_in_block"],
            "display_order": current_trial["display_order"],
            "total_trials_in_block": total_trials_in_block,
            "block_name": current_block.name,
            "task_type": current_trial["task_type"],
            "trajectory_category": current_block.trajectories_category,  # Запрошенная категория
            "actual_trajectory_category": current_trial.get(
                "actual_trajectory_category", current_block.trajectories_category
            ),  # Реальная категория
            "trajectory_index": current_trial["trajectory_index"],
            "speed": current_trial["speed"],
            "duration": current_trial["duration"],
        }

    def get_used_trajectories_info(self) -> Dict[str, Any]:
        """Возвращает информацию об использованных траекториях (для отладки)"""
        return {
            "total_used": len(self.used_trajectories_global),
            "used_by_category": {
                category: len(
                    [key for key in self.used_trajectories_global if key[0] == category]
                )
                for category in self.trajectories_data.keys()
                if category != "R"
            },
        }
