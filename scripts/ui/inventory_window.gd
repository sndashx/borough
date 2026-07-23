extends AcceptDialog

# Player Inventory & Gear Window

@onready var item_list: ItemList = $VBox/ItemList
@onready var gold_label: Label = $VBox/GoldLabel

func _ready() -> void:
	title = "Player Inventory & Gear"

func show_inventory() -> void:
	item_list.clear()
	var world = GameState.world_data
	var player_id = world.get("player_id")
	var npcs = GameState.get_npcs()
	
	var coins = 0
	if player_id and npcs.has(player_id):
		coins = int(npcs[player_id].get("status", {}).get("coins", 0))
		
	gold_label.text = "Purse: %d copper coins" % coins
	
	# List player items
	item_list.add_item("🌾 Grain (Food Supply)")
	item_list.add_item("🍞 Loaf of Bread")
	item_list.add_item("🗡️ Iron Dagger")
	item_list.add_item("🧥 Woolen Cloak")
	
	popup_centered(Vector2i(400, 300))
