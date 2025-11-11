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

def main() -> None:
    # Инициализация Pygame
    pygame.init()
    
    # Получаем информацию о дисплее для автоматического определения размера
    display_info = pygame.display.Info()
    screen_width: int = display_info.current_w  # Ширина экрана
    screen_height: int = display_info.current_h  # Высота экрана

    # Создаем полноэкранное окно без рамок
    screen = pygame.display.set_mode((screen_width, screen_height), pygame.NOFRAME)
    
    # Скрываем курсор мыши в полноэкранном режиме
    pygame.mouse.set_visible(False)

    # Установка названия
    pygame.display.set_caption("Time_exp_v.0.1.0")
    
    # Цвет заднего фона
    BACKGROUND_COLOR: tuple[int, int, int] = (255, 255, 255)

    # Загружает траектории
    trajectories_data = load_trajectories("trajectories.json")
    trajectory_manager = TrajectoryManager(trajectories_data)
   
    # Создаем конфигурацию эксперимента
    config = ExperimentConfig()
    
    # Создаем менеджер блоков с передачей скоростей и длительностей
    block_manager = BlockManager(
        trajectories_data, 
        config.blocks,
        config.available_speeds,
        config.available_durations
    )
    
    # Получаем информацию о первой попытке
    progress_info = block_manager.get_progress_info()
    current_block = block_manager.get_current_block()
    current_trial = block_manager.get_current_trial()
    
    # Загружаем первую траекторию
    try:
        trajectory_manager.load_trajectory(
            current_block.trajectories_category, 
            current_trial["trajectory_index"]
        )
    except ValueError as e:
        print(f"Ошибка загрузки начальной траектории: {e}")
        sys.exit()
    
    # Получаем конфигурацию текущей задачи
    current_task = config.get_current_task_config(current_trial["task_type"])
    
    # Создаем сборщик данных для первого блока
    data_collector = DataCollector(config.participant_id, progress_info["block_number"])

    # Используем назначенную скорость или берем первую из доступных
    assigned_speed = current_trial["speed"] if current_trial["speed"] is not None else config.available_speeds[0]
    
    # Автоматически рассчитываем продолжительность для траектории с использованием назначенной скорости
    trajectory_info = trajectory_manager.get_current_trajectory_info()
    calculated_duration = 0.0
    if (trajectory_manager.current_trajectory is not None and 
        hasattr(trajectory_manager.current_trajectory, 'calculate_duration')):
        calculated_duration = trajectory_manager.current_trajectory.calculate_duration(assigned_speed)
    
    print(f"=== Блок {progress_info['block_number']}/{progress_info['total_blocks']}: {current_block.name} ===")
    print(f"=== {current_task.name} ===")
    print(f"Попытка: {progress_info['trial_in_block']}/{progress_info['total_trials_in_block']} (порядок: {progress_info['display_order']})")
    print(f"Загружена траектория {current_block.trajectories_category}[{current_trial['trajectory_index']}]")
    print(f"Длина траектории: {trajectory_info.get('total_length', 0):.1f} пикселей")
    print(f"Расчетная продолжительность: {calculated_duration:.0f} мс")
    print(f"Назначенная скорость: {assigned_speed} px/кадр")
    if current_trial["duration"] is not None:
        print(f"Назначенная длительность: {current_trial['duration']} мс")
    print(f"Фиксационная точка: {current_task.fixation_shape.value}")
    print(f"Окклюзия: {'ВКЛ' if current_task.occlusion_enabled else 'ВЫКЛ'}")
    if current_task.occlusion_enabled:
        print(f"Тип окклюзии: {current_task.occlusion_type}")
    print(f"Оценка времени: {'ДА' if current_task.timing_estimation else 'НЕТ'}")
    print(f"Воспроизведение времени: {'ДА' if current_task.reproduction_task else 'НЕТ'}")
    print(f"Разрешение экрана: {screen_width}x{screen_height}")

    # Создается движущаяся точка с настройками из текущей задачи
    moving_point = None
    if trajectory_manager.current_trajectory is not None:
        moving_point = MovingPoint(
            trajectory_manager.current_trajectory, 
            speed=assigned_speed,  # Используем назначенную скорость
            occlusion_type=current_task.occlusion_type if current_task.occlusion_enabled else "none"
        )
        if not current_task.occlusion_enabled:
            moving_point.disable_occlusion()
    else:
        print("Ошибка: Не удалось создать движущуюся точку - траектория не загружена")
        sys.exit()

    # Создаем экран инструкции
    instruction_screen = InstructionScreen(screen_width, screen_height)
    
    # Создаем начальный экран инструкции
    initial_instruction_screen = InstructionScreen(screen_width, screen_height)
    initial_instruction_screen.set_custom_content(
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
            "Нажмите ПРОБЕЛ чтобы начать эксперимент"
        ]
    )
    initial_instruction_screen.activate()
    
    # Создаем экран оценки времени
    timing_screen = TimingEstimationScreen(screen_width, screen_height)
    
    # Создаем задачу воспроизведения времени
    reproduction_task = ReproductionTask(screen_width, screen_height)

    # Флаг для отслеживания начального экрана
    waiting_for_initial_start = True

    # Создаем фиксационную точку с настройками из текущей задачи
    fixation = FixationCross(screen_width, screen_height, current_task.fixation_shape, config.fixation_size)
    fixation.set_color(config.fixation_color)
    
    # pygame.time.Clock - тип таймера
    # Переменная для контроля обновления частоты кадров для снижения нагрузки на проц и регуляции под герцовку монитора
    clock: pygame.time.Clock = pygame.time.Clock()
    
    # Переменные для отслеживания времени
    start_time = pygame.time.get_ticks()  # Запускаем таймер сразу для первой траектории
    space_press_time = 0
    
    # Флаг для отслеживания ожидания инструкции
    waiting_for_instruction = False
    
    # Флаг для отслеживания начала движения (чтобы записать время начала движения только один раз)
    movement_started = False
    
    # Флаг для отслеживания начала окклюзии (чтобы записать время начала окклюзии только один раз)
    occlusion_started = False
    
    # Переменная для хранения информации о текущей траектории
    current_trajectory_info = trajectory_manager.get_current_trajectory_info()
    current_calculated_duration = calculated_duration
    
    # Таймер для задержки перед показом инструкции
    instruction_delay_timer = 0
    INSTRUCTION_DELAY = 900  # 900 мс задержки
    
    # Начинаем первую попытку с автоматически рассчитанной продолжительностью
    condition_type = f"occlusion_{current_task.occlusion_type}" if current_task.occlusion_enabled else "no_occlusion"
    if current_task.timing_estimation:
        condition_type += "_timing_estimation"
    if current_task.reproduction_task:
        condition_type += "_reproduction"
    
    data_collector.start_new_trial(
        trajectory_type=current_block.trajectories_category,
        duration=current_calculated_duration,
        speed=assigned_speed,
        trajectory_number=current_trial["trajectory_index"],
        condition_type=condition_type,
        block_number=progress_info["block_number"],
        trial_in_block=progress_info["trial_in_block"],
        display_order=progress_info["display_order"],
        assigned_speed=current_trial["speed"],
        assigned_duration=current_trial["duration"]
    )

    # Цикл отрабатывает пока не нажмем на ESC. Переменная running вместо while True для более легкого выхода через изменение значения переменной, а не двойной break/
    running: bool = True
    while running:
        dt = clock.tick(60)  # delta time в миллисекундах
        current_time = pygame.time.get_ticks()
        
        # Отрабатывает события по списку всех событий из pygame.event.get()
        for event in pygame.event.get():
            # Закрываемся по нажатию на крестик
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                # Выходим из цикла через ESC
                if event.key == pygame.K_ESCAPE:
                    running = False
                
                # Обработка начального экрана инструкции
                elif waiting_for_initial_start and initial_instruction_screen.is_active:
                    if event.key == pygame.K_SPACE:
                        initial_instruction_screen.deactivate()
                        waiting_for_initial_start = False
                        print("Эксперимент начат!")
                
                # Обработка экрана оценки времени
                elif timing_screen.is_active:
                    if timing_screen.handle_event(event):
                        # Записываем результаты оценки времени
                        timing_results = timing_screen.get_results()
                        data_collector.record_timing_estimation(timing_results)
                        timing_screen.deactivate()
                        
                        # Сразу завершаем попытку для задачи 3
                        data_collector.complete_trial(completed_normally=True)
                        
                        # Для задачи 3 (оценка времени) - сразу показываем инструкцию без задержки
                        if current_task.timing_estimation:
                            instruction_screen.activate()
                            print(f"Оценка времени завершена!")
                            print(f"Фактическое время: {timing_results['actual_duration']}мс")
                            print(f"Оцененное время: {timing_results['estimated_duration']}мс")
                            print(f"Ошибка: {timing_results['estimation_error']}мс")
                        else:
                            # Для других задач - запускаем задержку
                            instruction_delay_timer = current_time
                            waiting_for_instruction = True
                            print(f"Оценка времени завершена! Задержка 900 мс перед показом инструкции...")
                
                # Обработка задачи воспроизведения времени
                elif reproduction_task.is_active:
                    if reproduction_task.handle_event(event):
                        # Записываем результаты воспроизведения
                        reproduction_results = reproduction_task.get_results()
                        data_collector.record_reproduction_results(reproduction_results)
                        reproduction_task.deactivate()
                        
                        # Сразу завершаем попытку
                        data_collector.complete_trial(completed_normally=True)
                        
                        # Сразу показываем инструкцию без задержки
                        instruction_screen.activate()
                        
                        print(f"Воспроизведение времени завершено!")
                        print(f"Целевая длительность: {reproduction_results['target_duration']}мс")
                        print(f"Воспроизведенная длительность: {reproduction_results['reproduced_duration']}мс")
                        print(f"Ошибка: {reproduction_results['reproduction_error']}мс")
                
                elif event.key == pygame.K_SPACE:
                    # Если начальная инструкция активна
                    if waiting_for_initial_start and initial_instruction_screen.is_active:
                        initial_instruction_screen.deactivate()
                        waiting_for_initial_start = False
                        print("Эксперимент начат!")
                    
                    # Если инструкция активна - обрабатываем нажатие пробела для продолжения
                    elif instruction_screen.is_active:
                        if instruction_screen.handle_event(event):
                            waiting_for_instruction = False
                            # Завершаем текущую попытку в сборщике данных
                            data_collector.complete_trial(completed_normally=not moving_point.stopped_by_user)
                            
                            # Переходим к следующей попытке
                            block_completed = block_manager.move_to_next_trial()
                            
                            if block_completed:
                                # Блок завершен, сохраняем данные
                                filename = save_experiment_data(
                                    config.participant_id, 
                                    progress_info["block_number"], 
                                    data_collector.get_all_data()
                                )
                                print(f"Блок {progress_info['block_number']} завершен! Данные сохранены в: {filename}")
                                
                                if block_manager.is_experiment_complete():
                                    print("=== Эксперимент завершен! Все блоки пройдены. ===")
                                    running = False
                                    continue
                                else:
                                    # Создаем новый сборщик данных для нового блока
                                    progress_info = block_manager.get_progress_info()
                                    data_collector = DataCollector(config.participant_id, progress_info["block_number"])
                            
                            # Получаем информацию о следующей попытке
                            progress_info = block_manager.get_progress_info()
                            current_block = block_manager.get_current_block()
                            current_trial = block_manager.get_current_trial()
                            current_task = config.get_current_task_config(current_trial["task_type"])
                            
                            # Загружаем следующую траекторию
                            try:
                                trajectory_manager.load_trajectory(
                                    current_block.trajectories_category, 
                                    current_trial["trajectory_index"]
                                )
                                
                                # Используем назначенную скорость или берем первую из доступных
                                assigned_speed = current_trial["speed"] if current_trial["speed"] is not None else config.available_speeds[0]
                                
                                # Автоматически рассчитываем продолжительность для новой траектории с использованием назначенной скорости
                                current_trajectory_info = trajectory_manager.get_current_trajectory_info()
                                current_calculated_duration = 0.0
                                if (trajectory_manager.current_trajectory is not None and 
                                    hasattr(trajectory_manager.current_trajectory, 'calculate_duration')):
                                    current_calculated_duration = trajectory_manager.current_trajectory.calculate_duration(assigned_speed)
                                
                                # Обновляем фиксационную точку для новой задачи
                                fixation.set_shape(current_task.fixation_shape)
                                
                                # Безопасно создаем движущуюся точку с настройками новой задачи
                                if trajectory_manager.current_trajectory is not None:
                                    moving_point.reset(trajectory_manager.current_trajectory)
                                    # Обновляем настройки окклюзии для новой задачи
                                    if current_task.occlusion_enabled:
                                        moving_point.set_occlusion_type(current_task.occlusion_type)
                                        moving_point.occlusion_enabled = True
                                    else:
                                        moving_point.disable_occlusion()
                                else:
                                    print("Ошибка: Не удалось сбросить движущуюся точку - траектория не загружена")
                                    continue
                                    
                                start_time = pygame.time.get_ticks()  # Запускаем таймер для новой траектории
                                movement_started = False  # Сбрасываем флаг начала движения
                                occlusion_started = False  # Сбрасываем флаг начала окклюзии
                                instruction_delay_timer = 0  # Сбрасываем таймер задержки
                                
                                # Начинаем новую попытку в сборщике данных
                                condition_type = f"occlusion_{current_task.occlusion_type}" if current_task.occlusion_enabled else "no_occlusion"
                                if current_task.timing_estimation:
                                    condition_type += "_timing_estimation"
                                if current_task.reproduction_task:
                                    condition_type += "_reproduction"
                                
                                data_collector.start_new_trial(
                                    trajectory_type=current_block.trajectories_category,
                                    duration=current_calculated_duration,
                                    speed=assigned_speed,
                                    trajectory_number=current_trial["trajectory_index"],
                                    condition_type=condition_type,
                                    block_number=progress_info["block_number"],
                                    trial_in_block=progress_info["trial_in_block"],
                                    display_order=progress_info["display_order"],
                                    assigned_speed=current_trial["speed"],
                                    assigned_duration=current_trial["duration"]
                                )
                                
                                print(f"\n=== Блок {progress_info['block_number']}/{progress_info['total_blocks']}: {current_block.name} ===")
                                print(f"=== {current_task.name} ===")
                                print(f"Попытка: {progress_info['trial_in_block']}/{progress_info['total_trials_in_block']} (порядок: {progress_info['display_order']})")
                                print(f"Загружена траектория {current_block.trajectories_category}[{current_trial['trajectory_index']}]")
                                print(f"Длина: {current_trajectory_info.get('total_length', 0):.1f}px, Продолжительность: {current_calculated_duration:.0f}мс")
                                print(f"Назначенная скорость: {assigned_speed} px/кадр")
                                if current_trial["duration"] is not None:
                                    print(f"Назначенная длительность: {current_trial['duration']} мс")
                                print(f"Фиксационная точка: {current_task.fixation_shape.value}")
                                print(f"Окклюзия: {'ВКЛ' if current_task.occlusion_enabled else 'ВЫКЛ'}")
                                if current_task.occlusion_enabled:
                                    print(f"Тип окклюзии: {current_task.occlusion_type}")
                                print(f"Оценка времени: {'ДА' if current_task.timing_estimation else 'НЕТ'}")
                                print(f"Воспроизведение времени: {'ДА' if current_task.reproduction_task else 'НЕТ'}")
                            except ValueError as e:
                                print(f"Ошибка загрузки траектории: {e}")
                    
                    # Если инструкция не активна и точка движется (и это НЕ задача с оценкой времени или воспроизведением) - останавливаем точку
                    elif (not instruction_screen.is_active and 
                          not waiting_for_instruction and
                          not waiting_for_initial_start and
                          not timing_screen.is_active and
                          not reproduction_task.is_active and
                          moving_point is not None and 
                          moving_point.is_moving and 
                          not moving_point.stopped_by_user and
                          not current_task.timing_estimation and
                          not current_task.reproduction_task):  # Не позволяем останавливать в задачах с оценкой времени и воспроизведением
                        # Останавливаем точку по нажатию пробела
                        moving_point.stop_by_user()
                        space_press_time = pygame.time.get_ticks()
                        reaction_time = space_press_time - start_time
                        
                        # Записываем нажатие пробела в сборщике данных
                        data_collector.record_space_press(stopped_by_user=True)
                        
                        # Для задач 1-2 - запускаем задержку
                        instruction_delay_timer = current_time
                        waiting_for_instruction = True
                        
                        print(f"Пользователь остановил точку! Время реакции: {reaction_time}мс")
                        print(f"Задержка 900 мс перед показом инструкции...")
                
                elif event.key == pygame.K_h and not instruction_screen.is_active and not waiting_for_initial_start and not timing_screen.is_active and not reproduction_task.is_active:
                    print("\n=== Управление ===")
                    print("ПРОБЕЛ: Остановить точку / продолжить")
                    print("H: Показать справку")
                    print("S: Сохранить данные")
                    print("ESC: Выход")
                    print(f"Текущий блок: {progress_info['block_number']}/{progress_info['total_blocks']} - {current_block.name}")
                    print(f"Текущая задача: {current_task.name}")
                    print(f"Прогресс: {progress_info['trial_in_block']}/{progress_info['total_trials_in_block']} попыток")
                    print(f"Порядок показа: {progress_info['display_order']}")
                    print(f"Скорость: {assigned_speed} px/кадр")
                    if current_trial["duration"] is not None:
                        print(f"Длительность: {current_trial['duration']} мс")
                    print(f"Фиксационная точка: {current_task.fixation_shape.value}")
                    print(f"Окклюзия: {'ВКЛ' if current_task.occlusion_enabled else 'ВЫКЛ'}")
                    if current_task.occlusion_enabled:
                        print(f"Тип окклюзии: {current_task.occlusion_type}")
                    print(f"Оценка времени: {'ДА' if current_task.timing_estimation else 'НЕТ'}")
                    print(f"Воспроизведение времени: {'ДА' if current_task.reproduction_task else 'НЕТ'}")
                    print(f"Разрешение экрана: {screen_width}x{screen_height}")
                
                elif event.key == pygame.K_s and not instruction_screen.is_active and not waiting_for_initial_start and not timing_screen.is_active and not reproduction_task.is_active:
                    # Сохранить данные текущей задачи (для отладки)
                    filename = save_experiment_data(
                        config.participant_id, 
                        progress_info["block_number"], 
                        data_collector.get_all_data()
                    )
                    print(f"Данные текущего блока сохранены в файл: {filename}")
        
        # Проверяем, прошла ли задержка перед показом инструкции (только для задач 1-2)
        if (waiting_for_instruction and 
            not instruction_screen.is_active and 
            not timing_screen.is_active and
            not reproduction_task.is_active and
            current_time - instruction_delay_timer >= INSTRUCTION_DELAY and
            not current_task.timing_estimation and
            not current_task.reproduction_task):  # Только для задач без оценки времени и воспроизведения
            instruction_screen.activate()
            print("Показ инструкции...")
        
        # Обновление задачи воспроизведения времени
        if reproduction_task.is_active:
            reproduction_task.update()
        
        # Обновление движения точки (только если не на экране инструкции и точка существует)
        if (not instruction_screen.is_active and 
            not waiting_for_initial_start and
            not timing_screen.is_active and
            not reproduction_task.is_active and
            moving_point is not None):
            moving_point.update(dt)
            
            # Записываем время начала движения (только один раз)
            if not movement_started and moving_point.is_moving:
                data_collector.record_movement_start()
                movement_started = True
            
            # Записываем время начала окклюзии (только один раз, когда точка входит в зону окклюзии)
            if (not occlusion_started and 
                moving_point.occlusion_enabled and 
                not moving_point.is_visible):
                data_collector.record_occlusion_start(moving_point)
                occlusion_started = True
                print("Точка вошла в зону окклюзии")
            
            # Проверяем автоматическое переключение при достижении финиша
            if moving_point.should_switch_to_next() and not waiting_for_instruction:
                # Записываем окончание движения
                actual_duration = pygame.time.get_ticks() - start_time
                data_collector.record_movement_end()
                
                # Для задач с оценкой времени - активируем экран оценки
                if current_task.timing_estimation:
                    data_collector.record_trajectory_duration(actual_duration)
                    timing_screen.activate(actual_duration)
                    print(f"Траектория завершена! Фактическое время: {actual_duration}мс")
                    print("Переходим к оценке времени...")
                # Для задач с воспроизведением времени - активируем задачу воспроизведения
                elif current_task.reproduction_task:
                    data_collector.record_trajectory_duration(actual_duration)
                    
                    # Используем назначенную длительность или время из траектории
                    assigned_duration = current_trial["duration"] if current_trial["duration"] is not None else actual_duration
                    reproduction_task.activate(assigned_duration)
                    
                    print(f"Траектория завершена! Фактическое время: {actual_duration}мс")
                    print(f"Используемое время для воспроизведения: {assigned_duration}мс")
                    print("Переходим к воспроизведению времени...")
                else:
                    data_collector.record_space_press(stopped_by_user=False)
                    # Для задач 1-2 - запускаем задержку
                    instruction_delay_timer = current_time
                    waiting_for_instruction = True
                    print("Точка достигла финиша! Задержка 900 мс перед показом инструкции...")

        # Чистка экрана и заливка чистого указанным цветом (BACKGROUND_COLOR)
        screen.fill(BACKGROUND_COLOR)
        
        # Если начальная инструкция активна - показываем только ее
        if waiting_for_initial_start and initial_instruction_screen.is_active:
            initial_instruction_screen.draw(screen)
        # Если активен экран оценки времени - показываем его
        elif timing_screen.is_active:
            timing_screen.draw(screen)
        # Если активна задача воспроизведения - показываем ее
        elif reproduction_task.is_active:
            reproduction_task.draw(screen, fixation)
        else:
            # Рисуем фиксационную точку через метод из fixation.py
            fixation.draw(screen)

            # Отрисовка траектории (без визуализации окклюзии) - только для задач 1-3
            if not current_task.reproduction_task:  # Не показываем траекторию в задаче 4
                trajectory_manager.draw_current(screen)

            # Отрисовка точки (если точка существует) - только для задач 1-3
            if moving_point is not None and not current_task.reproduction_task:  # Не показываем точку в задаче 4
                moving_point.draw(screen)
            
            # Отрисовка экрана инструкции (если активен)
            instruction_screen.draw(screen)
            
            # Отображаем информацию о текущей задаче, блоке и попытке
            font = pygame.font.Font(None, 24)
            task_info = font.render(
                f"Задача: {current_task.name}", 
                True, (0, 0, 0)
            )
            block_info = font.render(
                f"Блок: {progress_info['block_number']}/{progress_info['total_blocks']} - {current_block.name}", 
                True, (0, 0, 0)
            )
            progress_info_text = font.render(
                f"Прогресс: {progress_info['trial_in_block']}/{progress_info['total_trials_in_block']} (порядок: {progress_info['display_order']})", 
                True, (0, 0, 0)
            )
            participant_info = font.render(
                f"Испытуемый: {config.participant_id}", 
                True, (0, 0, 0)
            )
            settings_info = font.render(
                f"Фиксация: {current_task.fixation_shape.value} | Окклюзия: {'ВКЛ' if current_task.occlusion_enabled else 'ВЫКЛ'} | Оценка: {'ДА' if current_task.timing_estimation else 'НЕТ'} | Воспроизведение: {'ДА' if current_task.reproduction_task else 'НЕТ'}", 
                True, (0, 0, 0)
            )
            resolution_info = font.render(
                f"Разрешение: {screen_width}x{screen_height}", 
                True, (0, 0, 0)
            )
            
            # Отображаем информацию о задержке, если она активна (только для задач 1-2)
            if (waiting_for_instruction and 
                not instruction_screen.is_active and 
                not current_task.timing_estimation and
                not current_task.reproduction_task):
                time_left = INSTRUCTION_DELAY - (current_time - instruction_delay_timer)
                if time_left > 0:
                    delay_info = font.render(
                        f"Задержка: {time_left} мс", 
                        True, (255, 0, 0)
                    )
                    screen.blit(delay_info, (screen_width - 150, screen_height - 25))
            
            screen.blit(task_info, (10, screen_height - 120))
            screen.blit(block_info, (10, screen_height - 95))
            screen.blit(progress_info_text, (10, screen_height - 70))
            screen.blit(participant_info, (10, screen_height - 45))
            screen.blit(settings_info, (10, screen_height - 20))
            screen.blit(resolution_info, (screen_width - 200, screen_height - 20))
        
        # Двойная буферизация из библиотеки pygame. Через метод flip отображаем, что было нарисовано в "заднем буфере" (Рисуем -> показываем через .flip())
        pygame.display.flip()
        
        # Устанавливаем нужный FPS
        clock.tick(60)
    
    # Сохраняем данные текущего блока при завершении программы
    if not block_manager.is_experiment_complete():
        print(f"\n=== Завершение эксперимента ===")
        filename = save_experiment_data(
            config.participant_id, 
            progress_info["block_number"], 
            data_collector.get_all_data()
        )
        print(f"Данные текущего блока сохранены в файл: {filename}")
    
    # Восстанавливаем видимость курсора мыши перед выходом
    pygame.mouse.set_visible(True)
    
    # Вырубаем все модули pygame (освобождаем ресурсы)
    pygame.quit()

    # Завершаем выполнение программы
    sys.exit()

# Точка входа кода, не меняем, нужна для того, чтобы код запускался только через main.py
if __name__ == "__main__":
    main()