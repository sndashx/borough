"""Procedural 32x32 NPC portrait generator for Borough."""
from __future__ import annotations
from PIL import Image, ImageDraw


def generate_npc_portrait(npc_data: dict) -> Image.Image:
    """Generate a 32x32 pixel face portrait based on sex, age, health, and mood."""
    sex = str(npc_data.get("sex", "M"))
    birth_year = int(npc_data.get("birth_year", 0))
    age = max(0, 1200 - birth_year)
    health = int(npc_data.get("body", {}).get("health", 100))
    
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Skin tone
    skin_color = (220, 180, 140, 255) if health > 50 else (180, 170, 160, 255)
    
    # Head base
    draw.ellipse([8, 6, 23, 25], fill=skin_color)
    
    # Eyes
    eye_color = (40, 30, 20, 255)
    draw.rectangle([11, 13, 13, 15], fill=eye_color)
    draw.rectangle([18, 13, 20, 15], fill=eye_color)
    
    # Mouth
    if health < 40:
        draw.line([13, 22, 18, 20], fill=(120, 40, 40, 255), width=1) # Frown
    else:
        draw.line([13, 21, 18, 21], fill=(120, 40, 40, 255), width=1) # Smile
        
    # Hair
    hair_color = (60, 40, 20, 255) if age < 50 else (200, 200, 200, 255)
    if sex == "M":
        draw.rectangle([8, 5, 23, 10], fill=hair_color)
    else:
        draw.ellipse([6, 4, 25, 14], fill=hair_color)
        
    return img
