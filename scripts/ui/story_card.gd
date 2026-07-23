extends AcceptDialog

# Narrative Story Card Popup for major events (Crises, Weddings, Feuds, Brawls)

@onready var title_label: Label = $VBox/TitleLabel
@onready var prose_text: RichTextLabel = $VBox/ProseText

func _ready() -> void:
	dialog_hide_on_ok = true

func display_story(event_title: String, prose_body: String) -> void:
	title = "Chronicle Story Card"
	title_label.text = event_title
	prose_text.text = prose_body
	popup_centered(Vector2i(500, 300))
