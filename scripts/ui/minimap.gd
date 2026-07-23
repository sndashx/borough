extends SubViewportContainer

# Top-right interactive Minimap for Borough

@onready var minimap_camera: Camera2D = $SubViewport/MinimapCamera

func _ready() -> void:
	# Center minimap over world center (64 * 16 / 2 = 512)
	minimap_camera.position = Vector2(512, 512)
	minimap_camera.zoom = Vector2(0.15, 0.8)

func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		# Click on minimap to jump main camera
		var rect_size = size
		var local_pos = event.position
		var norm_pos = local_pos / rect_size
		var world_target = norm_pos * Vector2(1024, 1024)
		
		var main_cam = get_tree().current_scene.get_node("MainCamera")
		if main_cam:
			main_cam.position = world_target
