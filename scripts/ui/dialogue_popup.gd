extends AcceptDialog

# Dialogue & Interaction Window for NPC conversations

@onready var dialogue_text: RichTextLabel = $VBox/DialogueText

func _ready() -> void:
	title = "NPC Conversation"
	dialog_hide_on_ok = true

func show_dialogue(speaker_name: String, text_content: String) -> void:
	title = "Conversation with " + speaker_name
	dialogue_text.text = text_content
	popup_centered(Vector2i(450, 250))
