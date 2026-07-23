extends Node2D

@onready var rain_particles: CPUParticles2D = $RainParticles
@onready var snow_particles: CPUParticles2D = $SnowParticles

func _ready() -> void:
	GameState.day_ticked.connect(func(_y, _d): _update_weather())
	GameState.world_loaded.connect(_update_weather)
	_update_weather()

func _update_weather() -> void:
	var day = GameState.get_day() % 360
	var season_idx = (day / 90) % 4 # 0=Winter, 1=Spring, 2=Summer, 3=Autumn
	
	if season_idx == 0: # Winter
		snow_particles.emitting = true
		rain_particles.emitting = false
	elif season_idx == 1 or season_idx == 3: # Spring or Autumn
		snow_particles.emitting = false
		rain_particles.emitting = true
	else: # Summer
		snow_particles.emitting = false
		rain_particles.emitting = false
