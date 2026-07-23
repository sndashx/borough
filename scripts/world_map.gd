extends Node2D

@onready var ground_layer: TileMapLayer = $GroundLayer
@onready var building_layer: TileMapLayer = $BuildingLayer
@onready var actors_layer: TileMapLayer = $ActorsLayer
@onready var selection_layer: TileMapLayer = $SelectionLayer

var terrain_atlas = {
	"grass": Vector2i(0, 0),
	"dirt": Vector2i(1, 0),
	"cobble": Vector2i(2, 0),
	"water": Vector2i(3, 0),
	"farmland": Vector2i(4, 0)
}

var building_atlas = {
	"house": Vector2i(0, 1),
	"church": Vector2i(1, 1),
	"tavern": Vector2i(2, 1),
	"smithy": Vector2i(3, 1),
	"market": Vector2i(4, 1),
	"granary": Vector2i(5, 1),
	"barn": Vector2i(6, 1)
}

func _ready() -> void:
	GameState.world_loaded.connect(_update_map)
	GameState.selection_changed.connect(_update_selection)
	GameState.day_ticked.connect(func(_y, _d): _update_map())
	
	if not GameState.world_data.is_empty():
		_update_map()

func _update_map() -> void:
	var world = GameState.world_data
	if world.is_empty():
		return
		
	ground_layer.clear()
	building_layer.clear()
	actors_layer.clear()
	
	var width = int(world.get("map_width", 64))
	var height = int(world.get("map_height", 64))
	var tiles = GameState.get_tiles()
	
	# 1. Populate Ground Layer
	for y in range(min(height, tiles.size())):
		var row = tiles[y]
		for x in range(min(width, row.size())):
			var tile = row[x]
			var terrain = tile.get("terrain", "grass")
			var atlas_pos = terrain_atlas.get(terrain, Vector2i(0, 0))
			ground_layer.set_cell(Vector2i(x, y), 0, atlas_pos)

	# 2. Populate Building Layer
	var buildings = GameState.get_buildings()
	for b_id in buildings:
		var b = buildings[b_id]
		var bx = int(b.get("x", 0))
		var by = int(b.get("y", 0))
		var btype = str(b.get("type", "house")).to_lower()
		var atlas_pos = building_atlas.get(btype, Vector2i(0, 1))
		
		# Draw 2x2 building footprint
		for dy in range(2):
			for dx in range(2):
				var pos = Vector2i(bx + dx, by + dy)
				building_layer.set_cell(pos, 0, atlas_pos)

	# 3. Populate Actors Layer (Living NPCs)
	var living_npcs = GameState.get_living_npcs()
	for npc in living_npcs:
		var status = npc.get("status", {})
		var house_id = str(status.get("household_id", ""))
		var pos = Vector2i(32, 32)
		
		if buildings.has(house_id):
			var house = buildings[house_id]
			pos = Vector2i(int(house.get("x", 32)), int(house.get("y", 32)))
			
		actors_layer.set_cell(pos, 0, Vector2i(0, 2))
		
	_update_selection()
	queue_redraw()

func _draw() -> void:
	# Draw moment-to-moment NPC activity labels & thought bubbles over actors
	var world = GameState.world_data
	if world.is_empty():
		return
		
	var activities = world.get("npc_activities", {})
	var buildings = GameState.get_buildings()
	var living_npcs = GameState.get_living_npcs()
	
	for npc in living_npcs:
		var nid = str(npc.get("id", ""))
		var act = str(activities.get(nid, "Socializing"))
		var status = npc.get("status", {})
		var house_id = str(status.get("household_id", ""))
		var pos = Vector2(32, 32)
		
		if buildings.has(house_id):
			var house = buildings[house_id]
			pos = Vector2(int(house.get("x", 32)), int(house.get("y", 32)))
			
		var world_pos = pos * 16.0 + Vector2(8, -4)
		draw_string(ThemeDB.fallback_font, world_pos, act, HORIZONTAL_ALIGNMENT_CENTER, -1, 10, Color.YELLOW)

func _update_selection() -> void:
	selection_layer.clear()
	
	if GameState.selected_type == "tile" and GameState.selected_tile_pos.x >= 0:
		selection_layer.set_cell(GameState.selected_tile_pos, 0, Vector2i(1, 2))
	elif GameState.selected_type == "building":
		var buildings = GameState.get_buildings()
		if buildings.has(GameState.selected_id):
			var b = buildings[GameState.selected_id]
			var bx = int(b.get("x", 0))
			var by = int(b.get("y", 0))
			for dy in range(2):
				for dx in range(2):
					selection_layer.set_cell(Vector2i(bx + dx, by + dy), 0, Vector2i(1, 2))

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed:
		var mouse_grid_pos = ground_layer.local_to_map(ground_layer.to_local(event.position))
		var world = GameState.world_data
		if world.is_empty():
			return
			
		var width = int(world.get("map_width", 64))
		var height = int(world.get("map_height", 64))
		
		if mouse_grid_pos.x >= 0 and mouse_grid_pos.x < width and mouse_grid_pos.y >= 0 and mouse_grid_pos.y < height:
			var buildings = GameState.get_buildings()
			var clicked_building_id = ""
			for b_id in buildings:
				var b = buildings[b_id]
				var bx = int(b.get("x", 0))
				var by = int(b.get("y", 0))
				if (mouse_grid_pos.x == bx or mouse_grid_pos.x == bx + 1) and (mouse_grid_pos.y == by or mouse_grid_pos.y == by + 1):
					clicked_building_id = b_id
					break
			
			if event.button_index == MOUSE_BUTTON_LEFT:
				if not clicked_building_id.is_empty():
					GameState.select_building(clicked_building_id)
				else:
					GameState.select_tile(mouse_grid_pos)
			elif event.button_index == MOUSE_BUTTON_RIGHT:
				# Right click context menu (Soulash 2 style)
				var main_node = get_tree().current_scene
				if main_node and main_node.has_node("ContextMenu"):
					var menu = main_node.get_node("ContextMenu")
					if not clicked_building_id.is_empty():
						menu.show_for_target("building", clicked_building_id, mouse_grid_pos, event.position)
					else:
						menu.show_for_target("tile", "", mouse_grid_pos, event.position)


