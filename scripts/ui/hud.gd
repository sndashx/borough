extends Control

@onready var town_label: Label = %TownLabel
@onready var year_day_label: Label = %YearDayLabel
@onready var season_label: Label = %SeasonLabel
@onready var pop_label: Label = %PopLabel

@onready var pause_play_btn: Button = %PausePlayBtn
@onready var step_day_btn: Button = %StepDayBtn
@onready var step_year_btn: Button = %StepYearBtn
@onready var speed_opt_btn: OptionButton = %SpeedOptBtn
@onready var new_world_btn: Button = %NewWorldBtn

var tick_accumulator: float = 0.0

func _ready() -> void:
	GameState.world_loaded.connect(_update_hud)
	GameState.day_ticked.connect(func(_y, _d): _update_hud())
	
	pause_play_btn.pressed.connect(_on_pause_play_pressed)
	step_day_btn.pressed.connect(_on_step_day_pressed)
	step_year_btn.pressed.connect(_on_step_year_pressed)
	new_world_btn.pressed.connect(_on_new_world_pressed)
	
	speed_opt_btn.add_item("1x Speed (1s/day)")
	speed_opt_btn.add_item("2x Speed (0.5s/day)")
	speed_opt_btn.add_item("5x Speed (0.2s/day)")
	speed_opt_btn.item_selected.connect(_on_speed_selected)
	
	_update_hud()

func _process(delta: float) -> void:
	if not GameState.is_paused and not GameState.is_simulating:
		tick_accumulator += delta
		var interval = 1.0 / GameState.sim_speed
		if tick_accumulator >= interval:
			tick_accumulator -= interval
			GameState.advance_days(1)

func _update_hud() -> void:
	town_label.text = GameState.get_town_name()
	
	var year = GameState.get_year()
	var day = GameState.get_day() % 360
	year_day_label.text = "Year %d, Day %d" % [year, day]
	
	# Season calculation (360 days / 4 = 90 days per season)
	var season_names = ["Winter", "Spring", "Summer", "Autumn"]
	var season_idx = (day / 90) % 4
	season_label.text = "Season: %s" % season_names[season_idx]
	
	var living_count = GameState.get_living_npcs().size()
	pop_label.text = "Population: %d souls" % living_count
	
	if GameState.is_paused:
		pause_play_btn.text = "▶ Play"
	else:
		pause_play_btn.text = "⏸ Pause"

func _on_pause_play_pressed() -> void:
	GameState.is_paused = not GameState.is_paused
	_update_hud()

func _on_step_day_pressed() -> void:
	GameState.advance_days(1)

func _on_step_year_pressed() -> void:
	GameState.advance_years(1)

func _on_speed_selected(index: int) -> void:
	match index:
		0: GameState.sim_speed = 1.0
		1: GameState.sim_speed = 2.0
		2: GameState.sim_speed = 5.0

func _on_new_world_pressed() -> void:
	var seed_val = str(Time.get_ticks_msec())
	GameState.generate_new_world(seed_val, "New Borough", 30)
