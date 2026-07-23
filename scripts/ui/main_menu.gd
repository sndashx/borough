extends Control

# Main Menu & Settings Controller for Borough

@onready var new_game_btn: Button = %NewGameBtn
@onready var load_game_btn: Button = %LoadGameBtn
@onready var settings_btn: Button = %SettingsBtn
@onready var quit_btn: Button = %QuitBtn

@onready var master_vol_slider: HSlider = %MasterVolSlider
@onready var sfx_vol_slider: HSlider = %SFXVolSlider
@onready var fullscreen_check: CheckBox = %FullscreenCheck

func _ready() -> void:
	if new_game_btn:
		new_game_btn.pressed.connect(_on_new_game_pressed)
		new_game_btn.grab_focus()
	if load_game_btn:
		load_game_btn.pressed.connect(_on_load_game_pressed)
	if quit_btn:
		quit_btn.pressed.connect(func(): get_tree().quit())
		
	if master_vol_slider:
		master_vol_slider.value_changed.connect(_on_master_vol_changed)
	if fullscreen_check:
		fullscreen_check.toggled.connect(_on_fullscreen_toggled)

func _on_new_game_pressed() -> void:
	get_tree().change_scene_to_file("res://scenes/main.tscn")

func _on_load_game_pressed() -> void:
	get_tree().change_scene_to_file("res://scenes/main.tscn")

func _on_master_vol_changed(value: float) -> void:
	AudioServer.set_bus_volume_db(AudioServer.get_bus_index("Master"), linear_to_db(value / 100.0))

func _on_fullscreen_toggled(toggled: bool) -> void:
	if toggled:
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN)
	else:
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED)
