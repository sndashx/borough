extends PopupMenu

# Soulash 2 style contextual interaction menu

signal action_selected(action_name, target_id, tile_pos)

var target_type: String = "" # "npc", "building", "tile"
var target_id: String = ""
var target_pos: Vector2i = Vector2i.ZERO

func _ready() -> void:
	id_pressed.connect(_on_id_pressed)

func show_for_target(type: String, id: String, pos: Vector2i, screen_pos: Vector2) -> void:
	clear()
	target_type = type
	target_id = id
	target_pos = pos
	
	if target_type == "npc":
		add_item("💬 Talk / Greet", 1)
		add_item("🪙 Trade Goods", 2)
		add_item("🔍 Inspect NPC", 3)
		add_item("⚔️ Challenge", 4)
	elif target_type == "building":
		add_item("🔨 Work / Labor (+5 Coppers)", 10)
		add_item("😴 Rest / Sleep", 11)
		add_item("🏠 Inspect Structure", 12)
	elif target_type == "tile":
		add_item("🚶 Move Player Here", 20)
		add_item("🔍 Inspect Ground", 21)
		
	position = Vector2i(screen_pos)
	popup()

func _on_id_pressed(id: int) -> void:
	match id:
		1: action_selected.emit("talk", target_id, target_pos)
		2: action_selected.emit("trade", target_id, target_pos)
		3: action_selected.emit("inspect_npc", target_id, target_pos)
		4: action_selected.emit("fight", target_id, target_pos)
		10: action_selected.emit("work", target_id, target_pos)
		11: action_selected.emit("rest", target_id, target_pos)
		12: action_selected.emit("inspect_building", target_id, target_pos)
		20: action_selected.emit("move_player", target_id, target_pos)
		21: action_selected.emit("inspect_tile", target_id, target_pos)
