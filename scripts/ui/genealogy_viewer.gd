extends Control

# Family Tree & Lineage Visualizer for Borough

@onready var tree_text: RichTextLabel = $VBox/TreeText

func _ready() -> void:
	GameState.selection_changed.connect(_update_tree)

func _update_tree() -> void:
	if GameState.selected_type != "npc":
		tree_text.text = "[color=gray]Select an NPC to view their genealogical tree.[/color]"
		return
		
	var npcs = GameState.get_npcs()
	if not npcs.has(GameState.selected_id):
		return
		
	var npc = npcs[GameState.selected_id]
	var first = str(npc.get("first_name", ""))
	var fam = str(npc.get("family_name", ""))
	var mother_id = npc.get("mother_id")
	var father_id = npc.get("father_id")
	
	var txt = "[b][size=18]Family Lineage: %s %s[/size][/b]\n\n" % [first, fam]
	
	# Parents
	txt += "[b]Parents:[/b]\n"
	if mother_id and npcs.has(mother_id):
		var m = npcs[mother_id]
		txt += "• Mother: %s %s\n" % [m.get("first_name", ""), m.get("family_name", "")]
	else:
		txt += "• Mother: Unknown Ancestor\n"
		
	if father_id and npcs.has(father_id):
		var f = npcs[father_id]
		txt += "• Father: %s %s\n\n" % [f.get("first_name", ""), f.get("family_name", "")]
	else:
		txt += "• Father: Unknown Ancestor\n\n"
		
	# Children
	txt += "[b]Descendants:[/b]\n"
	var children_found = 0
	for other_id in npcs:
		var o = npcs[other_id]
		if o.get("mother_id") == GameState.selected_id or o.get("father_id") == GameState.selected_id:
			children_found += 1
			txt += "• Child: %s %s\n" % [o.get("first_name", ""), o.get("family_name", "")]
			
	if children_found == 0:
		txt += "• No living children recorded.\n"
		
	tree_text.text = txt
