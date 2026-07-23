extends Node

# Automated Beta Tester Agent for Borough Godot Engine

func _ready() -> void:
	print("\n=== STARTING AUTOMATED BETA TEST SESSION ===")
	await get_tree().create_timer(1.0).timeout
	
	# 1. Test GameState World Loading
	print("[Beta Tester] 1. Verifying initial world generation...")
	assert(not GameState.world_data.is_empty(), "World data should not be empty")
	print("  ✓ World Name: ", GameState.get_town_name())
	print("  ✓ Living Population: ", GameState.get_living_npcs().size(), " souls")
	print("  ✓ Buildings Count: ", GameState.get_buildings().size())
	
	await get_tree().create_timer(0.5).timeout
	
	# 2. Test Selection & Inspector
	print("\n[Beta Tester] 2. Inspecting living citizens...")
	var npcs = GameState.get_living_npcs()
	if npcs.size() > 0:
		var target_npc = npcs[0]
		var nid = str(target_npc.get("id", ""))
		print("  ✓ Selecting NPC: ", target_npc.get("first_name", ""), " ", target_npc.get("family_name", ""))
		GameState.select_npc(nid)
		assert(GameState.selected_type == "npc", "Selection type should be 'npc'")
		
	await get_tree().create_timer(0.5).timeout
	
	# 3. Test Building Selection
	print("\n[Beta Tester] 3. Inspecting town buildings...")
	var buildings = GameState.get_buildings()
	if buildings.size() > 0:
		var b_id = buildings.keys()[0]
		var b = buildings[b_id]
		print("  ✓ Selecting Building: ", b.get("name", "Building"))
		GameState.select_building(b_id)
		assert(GameState.selected_type == "building", "Selection type should be 'building'")
		
	await get_tree().create_timer(0.5).timeout
	
	# 4. Test World Simulation Step (+1 Day)
	print("\n[Beta Tester] 4. Testing simulation day progression...")
	var initial_day = GameState.get_day()
	GameState.advance_days(1)
	print("  ✓ Day advanced from ", initial_day, " -> ", GameState.get_day())
	assert(GameState.get_day() == initial_day + 1, "Day should advance by 1")
	
	await get_tree().create_timer(0.5).timeout
	
	# 5. Test World Simulation Step (+1 Year)
	print("\n[Beta Tester] 5. Testing annual boundary step (+1 Year)...")
	var initial_year = GameState.get_year()
	GameState.advance_years(1)
	print("  ✓ Year advanced from ", initial_year, " -> ", GameState.get_year())
	assert(GameState.get_year() == initial_year + 1, "Year should advance by 1")
	
	await get_tree().create_timer(0.5).timeout
	
	# 6. Test Chronicle Event Feed
	print("\n[Beta Tester] 6. Verifying town chronicle event logging...")
	var chronicle = GameState.get_chronicle()
	print("  ✓ Chronicle entries logged: ", chronicle.size())
	assert(chronicle.size() > 0, "Chronicle should contain events")
	
	print("\n=== ALL BETA TEST SUITES PASSED PERFECTLY WITH ZERO ERRORS ===")
	get_tree().quit()
