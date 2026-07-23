extends Camera2D

# AAA Camera Controller with Screen Shake & Smooth Tween Pan

@export var pan_speed: float = 500.0
@export var min_zoom: float = 0.4
@export var max_zoom: float = 3.0

var shake_strength: float = 0.0
var shake_decay: float = 5.0
var rng: RandomNumberGenerator = RandomNumberGenerator.new()

func _ready() -> void:
	position = Vector2(512, 512)
	zoom = Vector2(1.2, 1.5)

func _process(delta: float) -> void:
	# Screen Shake Decay
	if shake_strength > 0:
		shake_strength = max(0, shake_strength - shake_decay * delta)
		offset = Vector2(rng.randf_range(-shake_strength, shake_strength), rng.randf_range(-shake_strength, shake_strength))
	else:
		offset = Vector2.ZERO

func apply_shake(strength: float = 10.0) -> void:
	shake_strength = strength

func tween_to_target(target_pos: Vector2, target_zoom: float = 1.5) -> void:
	var tween = create_tween().set_parallel(true).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	tween.tween_property(self, "position", target_pos, 0.8)
	tween.tween_property(self, "zoom", Vector2(target_zoom, target_zoom), 0.8)
