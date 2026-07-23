extends Node

# Achievements & Milestones Manager

signal achievement_unlocked(id, title, description)

var unlocked_achievements: Dictionary = {}

var achievements_db = {
	"first_town": {"title": "Founding Father", "desc": "Establish your first town in Borough."},
	"pop_50": {"title": "Thriving Borough", "desc": "Reach a population of 50 living souls."},
	"century": {"title": "Centennial", "desc": "Guide the town through 100 years of history."},
	"wealthy": {"title": "Gilded Vaults", "desc": "Accumulate 100 copper coins in your purse."}
}

func _ready() -> void:
	GameState.day_ticked.connect(func(_y, _d): _check_achievements())

func _check_achievements() -> void:
	if not unlocked_achievements.has("first_town"):
		unlock("first_town")
		
	var living = GameState.get_living_npcs().size()
	if living >= 50 and not unlocked_achievements.has("pop_50"):
		unlock("pop_50")
		
	var year = GameState.get_year()
	if year >= 100 and not unlocked_achievements.has("century"):
		unlock("century")

func unlock(id: String) -> void:
	if achievements_db.has(id) and not unlocked_achievements.has(id):
		unlocked_achievements[id] = true
		var data = achievements_db[id]
		achievement_unlocked.emit(id, data["title"], data["desc"])
		print("ACHIEVEMENT UNLOCKED: ", data["title"])
