extends Node

# Autoload GameState singleton for Borough Godot application.

signal world_loaded
signal day_ticked(year, day)
signal selection_changed
signal chronicle_updated

var world_data: Dictionary = {}
var is_paused: bool = true
var sim_speed: float = 1.0 # Ticks per second when unpaused
var is_simulating: bool = false

# Selection state
var selected_type: String = "" # "npc", "building", "tile"
var selected_id: String = ""
var selected_tile_pos: Vector2i = Vector2i(-1, -1)

# Temp save file path
var current_save_path: String = "user://temp_world.json"

func _ready() -> void:
	# Convert user:// path to global OS path for Python bridge if needed
	var global_user_dir = OS.get_user_data_dir()
	current_save_path = global_user_dir + "/current_world.json"
	
	# Generate initial world on startup
	generate_new_world("1729", "Hollowfield", 30)

func generate_new_world(seed_str: String, town_name: String, pop: int) -> void:
	var py_path = _get_python_path()
	var bridge_path = ProjectSettings.globalize_path("res://sim_bridge.py")
	var repo_dir = ProjectSettings.globalize_path("res://")
	
	var args = [
		bridge_path,
		"--action", "gen",
		"--seed", seed_str,
		"--name", town_name,
		"--pop", str(pop),
		"--output-file", current_save_path
	]
	
	var output = []
	var exit_code = OS.execute(py_path, args, output, true)
	if exit_code == 0 and FileAccess.file_exists(current_save_path):
		_load_world_from_file(current_save_path)
	else:
		print("Error generating world via python bridge: ", output)

func advance_days(days: int = 1) -> void:
	if is_simulating:
		return
	is_simulating = true
	
	var py_path = _get_python_path()
	var bridge_path = ProjectSettings.globalize_path("res://sim_bridge.py")
	
	var args = [
		bridge_path,
		"--action", "tick_days",
		"--days", str(days),
		"--input-file", current_save_path,
		"--output-file", current_save_path
	]
	
	var output = []
	var exit_code = OS.execute(py_path, args, output, true)
	if exit_code == 0:
		_load_world_from_file(current_save_path)
		day_ticked.emit(get_year(), get_day())
	else:
		print("Error ticking simulation: ", output)
		
	is_simulating = false

func advance_years(years: int = 1) -> void:
	if is_simulating:
		return
	is_simulating = true
	
	var py_path = _get_python_path()
	var bridge_path = ProjectSettings.globalize_path("res://sim_bridge.py")
	
	var args = [
		bridge_path,
		"--action", "tick_years",
		"--years", str(years),
		"--input-file", current_save_path,
		"--output-file", current_save_path
	]
	
	var output = []
	var exit_code = OS.execute(py_path, args, output, true)
	if exit_code == 0:
		_load_world_from_file(current_save_path)
		day_ticked.emit(get_year(), get_day())
	else:
		print("Error ticking years: ", output)
		
	is_simulating = false

func _load_world_from_file(path: String) -> void:
	if not FileAccess.file_exists(path):
		return
	var file = FileAccess.open(path, FileAccess.READ)
	var content = file.get_as_text()
	file.close()
	
	var json = JSON.new()
	var parse_result = json.parse(content)
	if parse_result == OK:
		world_data = json.data
		world_loaded.emit()
		chronicle_updated.emit()
	else:
		print("JSON Parse Error: ", json.get_error_message())

func _get_python_path() -> String:
	# Try python3 or python from system
	return "python3"

# Convenience getters
func get_year() -> int:
	return int(world_data.get("year", 0))

func get_day() -> int:
	return int(world_data.get("day", 0))

func get_town_name() -> String:
	return str(world_data.get("name", "Hollowfield"))

func get_npcs() -> Dictionary:
	return world_data.get("npcs", {})

func get_living_npcs() -> Array:
	var res = []
	var npcs_dict = get_npcs()
	for id in npcs_dict:
		var npc = npcs_dict[id]
		if npc.get("is_alive", true):
			res.append(npc)
	return res

func get_buildings() -> Dictionary:
	return world_data.get("buildings", {})

func get_tiles() -> Array:
	return world_data.get("tiles", [])

func get_chronicle() -> Array:
	return world_data.get("chronicle", [])

func select_npc(npc_id: String) -> void:
	selected_type = "npc"
	selected_id = npc_id
	selection_changed.emit()

func select_building(building_id: String) -> void:
	selected_type = "building"
	selected_id = building_id
	selection_changed.emit()

func select_tile(pos: Vector2i) -> void:
	selected_type = "tile"
	selected_tile_pos = pos
	selection_changed.emit()
