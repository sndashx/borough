extends Camera2D

@export var pan_speed: float = 400.0
@export var zoom_speed: float = 0.1
@export var min_zoom: float = 0.3
@export var max_zoom: float = 3.0

var dragging: bool = false
var last_mouse_pos: Vector2 = Vector2.ZERO

func _ready() -> void:
	# Center initial camera over the 64x64 map (64 * 24 / 2 = 768)
	position = Vector2(768, 768)
	zoom = Vector2(0.8, 0.8)

func _process(delta: float) -> void:
	var move_vec = Vector2.ZERO
	if Input.is_action_pressed("ui_right") or Input.is_key_pressed(KEY_D):
		move_vec.x += 1
	if Input.is_action_pressed("ui_left") or Input.is_key_pressed(KEY_A):
		move_vec.x -= 1
	if Input.is_action_pressed("ui_down") or Input.is_key_pressed(KEY_S):
		move_vec.y += 1
	if Input.is_action_pressed("ui_up") or Input.is_key_pressed(KEY_W):
		move_vec.y -= 1
		
	if move_vec != Vector2.ZERO:
		position += move_vec.normalized() * pan_speed * delta * (1.0 / zoom.x)

func _unhandled_input(event: InputEvent) -> void:
	# Middle Mouse Pan
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_MIDDLE:
			if event.pressed:
				dragging = true
				last_mouse_pos = event.position
			else:
				dragging = false
		elif event.button_index == MOUSE_BUTTON_WHEEL_UP and event.pressed:
			zoom_camera(zoom_speed)
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN and event.pressed:
			zoom_camera(-zoom_speed)
			
	elif event is InputEventMouseMotion and dragging:
		var delta = event.position - last_mouse_pos
		position -= delta * (1.0 / zoom.x)
		last_mouse_pos = event.position

func zoom_camera(amount: float) -> void:
	var new_zoom = clamp(zoom.x + amount, min_zoom, max_zoom)
	zoom = Vector2(new_zoom, new_zoom)
