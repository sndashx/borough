extends CanvasModulate

# Dynamic Day/Night and Seasonal Ambient Lighting

func _ready() -> void:
	GameState.day_ticked.connect(func(_y, _d): _update_lighting())
	GameState.world_loaded.connect(_update_lighting)
	_update_lighting()

func _update_lighting() -> void:
	var day = GameState.get_day() % 360
	var season_idx = (day / 90) % 4
	
	# Seasonal base tint
	var season_tints = [
		Color(0.82, 0.88, 1.0), # Winter (Cool Blue)
		Color(0.95, 1.0, 0.92), # Spring (Fresh Green)
		Color(1.0, 0.98, 0.90), # Summer (Bright Warm)
		Color(1.0, 0.88, 0.75)  # Autumn (Golden Amber)
	]
	
	color = season_tints[season_idx]
