extends Control

@onready var chronicle_text: RichTextLabel = %ChronicleText

func _ready() -> void:
	GameState.chronicle_updated.connect(_update_chronicle)
	_update_chronicle()

func _update_chronicle() -> void:
	var chronicle = GameState.get_chronicle()
	var txt = ""
	
	for i in range(chronicle.size() - 1, -1, -1):
		var entry = chronicle[i]
		var yr = entry.get("year", 0)
		var etype = entry.get("type", "event")
		var summary = entry.get("summary", "")
		
		var type_color = "yellow"
		match etype:
			"founding": type_color = "gold"
			"birth": type_color = "light_green"
			"marriage": type_color = "pink"
			"death": type_color = "red"
			"crisis": type_color = "orange"
			"market": type_color = "light_blue"
			"player": type_color = "cyan"
			
		txt += "[color=gray][Year %d][/color] [color=%s][%s][/color] %s\n" % [yr, type_color, etype.capitalize(), summary]
		
	chronicle_text.text = txt
