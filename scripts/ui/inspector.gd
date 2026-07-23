extends Control

@onready var inspector_text: RichTextLabel = %InspectorText
@onready var npc_item_list: ItemList = %NPCItemList

var npc_id_map: Array[String] = []

func _ready() -> void:
	GameState.selection_changed.connect(_update_inspector)
	GameState.world_loaded.connect(_update_npc_list)
	GameState.day_ticked.connect(func(_y, _d): _update_npc_list(); _update_inspector())
	
	npc_item_list.item_selected.connect(_on_npc_item_selected)
	_update_inspector()
	_update_npc_list()

func _update_npc_list() -> void:
	npc_item_list.clear()
	npc_id_map.clear()
	
	var living = GameState.get_living_npcs()
	for npc in living:
		var nid = str(npc.get("id", ""))
		var first = str(npc.get("first_name", ""))
		var fam = str(npc.get("family_name", ""))
		var year = GameState.get_year()
		var age = year - int(npc.get("birth_year", year))
		var occ = str(npc.get("status", {}).get("occupation", "citizen"))
		
		npc_item_list.add_item("%s %s (Age %d, %s)" % [first, fam, age, occ])
		npc_id_map.append(nid)

func _on_npc_item_selected(index: int) -> void:
	if index >= 0 and index < npc_id_map.size():
		GameState.select_npc(npc_id_map[index])

func _update_inspector() -> void:
	if GameState.selected_type == "npc":
		_show_npc_details(GameState.selected_id)
	elif GameState.selected_type == "building":
		_show_building_details(GameState.selected_id)
	elif GameState.selected_type == "tile":
		_show_tile_details(GameState.selected_tile_pos)
	else:
		inspector_text.text = "[color=gray]Select an NPC, Building, or Tile on the map.[/color]"

func _show_npc_details(npc_id: String) -> void:
	var npcs = GameState.get_npcs()
	if not npcs.has(npc_id):
		inspector_text.text = "NPC not found."
		return
		
	var npc = npcs[npc_id]
	var first = str(npc.get("first_name", ""))
	var fam = str(npc.get("family_name", ""))
	var sex = str(npc.get("sex", "M"))
	var birth = int(npc.get("birth_year", 0))
	var age = GameState.get_year() - birth
	var is_alive = bool(npc.get("is_alive", true))
	
	var body = npc.get("body", {})
	var health = int(body.get("health", 100))
	var hunger = int(body.get("hunger", 100))
	var fatigue = int(body.get("fatigue", 0))
	
	var status = npc.get("status", {})
	var occupation = str(status.get("occupation", "unemployed"))
	var coins = int(status.get("coins", 0))
	var house_id = str(status.get("household_id", "none"))
	
	var txt = "[b][size=18]%s %s[/size][/b]\n" % [first, fam]
	txt += "[i]Sex:[/i] %s | [i]Age:[/i] %d | [i]Status:[/i] %s\n" % [sex, age, "Alive" if is_alive else "Deceased"]
	txt += "[i]Occupation:[/i] %s | [i]Coins:[/i] %d coppers\n\n" % [occupation.capitalize(), coins]
	txt += "[b]Physical Condition:[/b]\n"
	txt += "• Health: %d/100\n• Hunger: %d/100\n• Fatigue: %d/100\n" % [health, hunger, fatigue]
	
	# Life Ambition, Goal Progress, Quirks & Mood
	var amb = npc.get("ambition", {})
	if not amb.is_empty():
		var atitle = str(amb.get("title", "Live a Peaceful Life"))
		var aprog = int(amb.get("progress", 10))
		var quirks = amb.get("quirks", [])
		var mood = str(amb.get("mood_summary", "Content with life in Borough"))
		
		txt += "\n[b][color=gold]Life Ambition:[/color][/b] " + atitle + "\n"
		txt += "• Progress: %d%% [" % aprog
		for i in range(10):
			if i * 10 < aprog:
				txt += "█"
			else:
				txt += "░"
		txt += "]\n"
		if not quirks.is_empty():
			txt += "• [color=cyan]Quirks:[/color] " + ", ".join(quirks) + "\n"
		txt += "• [color=lightgreen]Mood:[/color] " + mood + "\n\n"
	
	# Anatomy, Scars & Impairments
	var anatomy = npc.get("anatomy", {})
	if not anatomy.is_empty():
		var scars = anatomy.get("scars", [])
		var impairments = anatomy.get("impairments", [])
		if not scars.is_empty():
			txt += "• [color=gold]Scars:[/color] " + ", ".join(scars) + "\n"
		if not impairments.is_empty():
			txt += "• [color=red]Impairments:[/color] " + ", ".join(impairments) + "\n"
		var cod = anatomy.get("cause_of_death_detail")
		if cod:
			txt += "• [color=gray]Fate:[/color] " + str(cod) + "\n"
	txt += "\n"
	
	# Psychological Needs & Dynamic Emotions
	var psy = npc.get("psychology", {})
	if not psy.is_empty():
		txt += "\n[b]Psychological Needs & Emotions:[/b]\n"
		txt += "• Joy: %d/100 | Grief: %d/100\n" % [int(psy.get("joy", 50)), int(psy.get("grief", 0))]
		txt += "• Ambition: %d/100 | Jealousy: %d/100\n" % [int(psy.get("ambition", 50)), int(psy.get("jealousy", 0))]
		txt += "• Safety: %d/100 | Belonging: %d/100\n" % [int(psy.get("safety_need", 80)), int(psy.get("belonging_need", 70))]
		txt += "• Esteem: %d/100\n\n" % [int(psy.get("esteem_need", 60))]
		
	# Mind traits
	var mind = npc.get("mind", {})
	if not mind.is_empty():
		txt += "[b]Personality Traits:[/b]\n"
		for t_name in mind:
			txt += "• %s: %d\n" % [t_name.capitalize(), int(mind[t_name])]
			
	inspector_text.text = txt

func _show_building_details(building_id: String) -> void:
	var buildings = GameState.get_buildings()
	if not buildings.has(building_id):
		inspector_text.text = "Building not found."
		return
		
	var b = buildings[building_id]
	var bname = str(b.get("name", "Building"))
	var btype = str(b.get("type", "house"))
	var bx = int(b.get("x", 0))
	var by = int(b.get("y", 0))
	var occupants = b.get("occupant_npc_ids", [])
	var item_ids = b.get("item_ids", [])
	
	var txt = "[b][size=18]%s[/size][/b]\n" % bname
	txt += "[i]Type:[/i] %s | [i]Location:[/i] (%d, %d)\n\n" % [btype.capitalize(), bx, by]
	txt += "[b]Occupants (%d):[/b]\n" % occupants.size()
	
	var npcs = GameState.get_npcs()
	for occ_id in occupants:
		if npcs.has(occ_id):
			var n = npcs[occ_id]
			txt += "• %s %s\n" % [n.get("first_name", ""), n.get("family_name", "")]
			
	txt += "\n[b]Stored Items:[/b] %d items" % item_ids.size()
	inspector_text.text = txt

func _show_tile_details(pos: Vector2i) -> void:
	var tiles = GameState.get_tiles()
	if pos.y < 0 or pos.y >= tiles.size() or pos.x < 0 or pos.x >= tiles[pos.y].size():
		inspector_text.text = "Out of map bounds."
		return
		
	var tile = tiles[pos.y][pos.x]
	var terrain = str(tile.get("terrain", "grass"))
	var b_id = tile.get("building_id")
	
	var txt = "[b][size=18]Tile (%d, %d)[/size][/b]\n" % [pos.x, pos.y]
	txt += "[i]Terrain:[/i] %s\n" % terrain.capitalize()
	if b_id:
		txt += "[i]Building ID:[/i] %s\n" % str(b_id)
	else:
		txt += "[i]Building:[/i] None\n"
		
	inspector_text.text = txt
