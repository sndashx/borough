class_name RelicsWindow
extends PanelContainer

@onready var title_label: Label = $VBoxContainer/TitleLabel
@onready var relics_container: VBoxContainer = $VBoxContainer/ScrollContainer/RelicsContainer
@onready var close_button: Button = $VBoxContainer/CloseButton

func _ready() -> void:
	visible = false
	if close_button:
		close_button.pressed.connect(func(): visible = false)
	GameState.world_loaded.connect(_update_view)
	GameState.day_ticked.connect(_update_view)

func open_window() -> void:
	_update_view()
	visible = true

func _update_view() -> void:
	var world_data = GameState.world_data
	if world_data.is_empty():
		return

	for child in relics_container.get_children():
		child.queue_free()

	var relics = world_data.get("relics_summary", [])
	if relics.is_empty():
		var empty_lbl = Label.new()
		empty_lbl.text = "No masterwork relics or legendary heirlooms forged yet."
		empty_lbl.add_theme_color_override("font_color", Color(0.6, 0.6, 0.6))
		relics_container.add_child(empty_lbl)
		return

	for relic in relics:
		var name_str = relic.get("name", "Artifact")
		var material = relic.get("material", "Iron")
		var creator = relic.get("creator", "Unknown Artisan")
		var owner = relic.get("owner", "Unknown")
		var value = relic.get("value", 100)
		var desc = relic.get("description", "")

		var item_box = VBoxContainer.new()
		var header = Label.new()
		header.text = "⚔ %s (%s)" % [name_str, material]
		header.add_theme_color_override("font_color", Color(0.95, 0.75, 0.2))

		var detail = Label.new()
		detail.text = "Forged by: %s | Held by: %s | Worth: %d Gold\n%s" % [
			creator, owner, value, desc
		]
		detail.add_theme_color_override("font_color", Color(0.85, 0.85, 0.85))

		item_box.add_child(header)
		item_box.add_child(detail)

		var history = relic.get("history", [])
		if not history.is_empty():
			var hist_lbl = Label.new()
			hist_lbl.text = "History: " + "; ".join(history)
			hist_lbl.add_theme_color_override("font_color", Color(0.6, 0.8, 0.9))
			item_box.add_child(hist_lbl)

		item_box.add_child(HSeparator.new())
		relics_container.add_child(item_box)
