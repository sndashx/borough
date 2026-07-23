extends Node

# Audio Manager Singleton for Borough SFX & Ambiance

var sfx_player: AudioStreamPlayer

func _ready() -> void:
	sfx_player = AudioStreamPlayer.new()
	add_child(sfx_player)
	
	GameState.day_ticked.connect(func(_y, _d): _play_tick_sfx())

func _play_tick_sfx() -> void:
	# Audio feedback on day progression
	pass
