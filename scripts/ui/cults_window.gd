class_name CultsWindow
extends PanelContainer

@onready var title_label: Label = $VBoxContainer/TitleLabel
@onready var cults_container: VBoxContainer = $VBoxContainer/ScrollContainer/CultsContainer
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

	for child in cults_container.get_children():
		child.queue_free()

	var cults = world_data.get("cults_summary", [])
	if cults.is_empty():
		var empty_lbl = Label.new()
		empty_lbl.text = "No secret cults or heresies detected... yet."
		empty_lbl.add_theme_color_override("font_color", Color(0.6, 0.6, 0.6))
		cults_container.add_child(empty_lbl)
		return

	for cult in cults:
		var name_str = cult.get("name", "Unknown Order")
		var leader = cult.get("leader", "Shadow")
		var symbol = cult.get("symbol", "Unmarked")
		var doctrine = cult.get("doctrine", "Secret")
		var secrecy = cult.get("secrecy", 100)
		var members = cult.get("members_count", 0)

		var item_box = VBoxContainer.new()
		var header = Label.new()
		header.text = "%s (Symbol: %s)" % [name_str, symbol]
		header.add_theme_color_override("font_color", Color(0.8, 0.3, 0.3))

		var detail = Label.new()
		detail.text = "Leader: %s | Members: %d | Secrecy: %d%%\nDoctrine: %s" % [
			leader, members, secrecy, doctrine
		]
		detail.add_theme_color_override("font_color", Color(0.8, 0.8, 0.8))

		item_box.add_child(header)
		item_box.add_child(detail)
		item_box.add_child(HSeparator.new())
		cults_container.add_child(item_box)
