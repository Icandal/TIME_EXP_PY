import random
from typing import List, Dict, Any
from exp_config import BlockConfig

class BlockManager:
    def __init__(self, trajectories_data: Dict[str, Any], blocks: List[BlockConfig], 
                 available_speeds: List[float], available_durations: List[int]):
        self.trajectories_data = trajectories_data
        self.blocks = blocks
        self.available_speeds = available_speeds
        self.available_durations = available_durations
        self.current_block_index = 0
        self.current_trial_index = 0
        
        # Генерируем последовательности для всех блоков
        self.block_sequences = []
        self.used_trajectories = {}  # Для отслеживания использованных траекторий
        
        for block in blocks:
            # Генерируем последовательность попыток для блока с учетом скоростей и длительностей
            trial_sequence = block.generate_trial_sequence(available_speeds, available_durations)
            
            # Для каждой попытки выбираем случайную траекторию
            for trial in trial_sequence:
                category = block.trajectories_category
                available_trajectories = self._get_available_trajectories(category)
                if available_trajectories:
                    trajectory_idx = random.choice(available_trajectories)
                    trial["trajectory_index"] = trajectory_idx
                    self._mark_trajectory_used(category, trajectory_idx)
                else:
                    # Если траектории закончились, начинаем заново
                    self._reset_used_trajectories(category)
                    available_trajectories = self._get_available_trajectories(category)
                    if available_trajectories:
                        trajectory_idx = random.choice(available_trajectories)
                        trial["trajectory_index"] = trajectory_idx
                        self._mark_trajectory_used(category, trajectory_idx)
                    else:
                        trial["trajectory_index"] = 0  # Резервный вариант
            
            self.block_sequences.append(trial_sequence)
    
    def _get_available_trajectories(self, category: str) -> List[int]:
        """Возвращает список доступных траекторий для категории"""
        if category not in self.trajectories_data:
            return []
        
        total_trajectories = len(self.trajectories_data[category])
        if category not in self.used_trajectories:
            self.used_trajectories[category] = set()
        
        available = []
        for i in range(total_trajectories):
            if i not in self.used_trajectories[category]:
                available.append(i)
        
        return available
    
    def _mark_trajectory_used(self, category: str, trajectory_idx: int) -> None:
        """Помечает траекторию как использованную"""
        if category not in self.used_trajectories:
            self.used_trajectories[category] = set()
        self.used_trajectories[category].add(trajectory_idx)
    
    def _reset_used_trajectories(self, category: str) -> None:
        """Сбрасывает использованные траектории для категории"""
        if category in self.used_trajectories:
            self.used_trajectories[category] = set()
    
    def get_current_block(self) -> BlockConfig:
        """Возвращает текущий блок"""
        return self.blocks[self.current_block_index]
    
    def get_current_trial(self) -> Dict[str, Any]:
        """Возвращает текущую попытку"""
        return self.block_sequences[self.current_block_index][self.current_trial_index]
    
    def move_to_next_trial(self) -> bool:
        """Переходит к следующей попытке, возвращает True если блок завершен"""
        self.current_trial_index += 1
        
        if self.current_trial_index >= len(self.block_sequences[self.current_block_index]):
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
            "trajectory_category": current_block.trajectories_category,
            "trajectory_index": current_trial["trajectory_index"],
            "speed": current_trial["speed"],
            "duration": current_trial["duration"]
        }