class_name CouncilWindow
extends PanelContainer

@onready var title_label: Label = $VBoxContainer/TitleLabel
@onready var treasury_label: Label = $VBoxContainer/TreasuryLabel
@onready var seats_container: VBoxContainer = $VBoxContainer/ScrollContainer/SeatsContainer
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

	var council = world_data.get("council_summary", {})
	if council.is_empty():
		treasury_label.text = "Town Governance: Tribal Assembly"
		return

	var treasury = council.get("treasury", 0)
	var tax_rate = council.get("tax_rate", 0)
	var curfew = council.get("curfew", false)
	var subsidies = council.get("subsidies", false)

	treasury_label.text = "Treasury: %d Gold | Tax Rate: %d%% | Curfew: %s | Subsidies: %s" % [
		treasury, tax_rate, "Active" if curfew else "None", "Active" if subsidies else "None"
	]

	for child in seats_container.get_children():
		child.queue_free()

	var seats = council.get("seats", {})
	for seat_title in seats.keys():
		var seat = seats[seat_title]
		var incumbent = seat.get("incumbent_name", "Vacant")
		var lbl = Label.new()
		lbl.text = "• %s: %s" % [seat_title, incumbent]
		lbl.add_theme_color_override("font_color", Color(0.9, 0.85, 0.5))
		seats_container.add_child(lbl)
