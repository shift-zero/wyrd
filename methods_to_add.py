    def _generate_room_name(self, room_type: str, x: int, y: int) -> str:
        """Generate a human-readable name for a room based on its type and coordinates."""
        type_names = {
            "plaza": "Town Square", "street": "Street", "alley": "Alleyway",
            "house": "House", "shop": "Shop", "tavern": "Tavern", "inn": "Inn",
            "gate": "City Gate", "tower": "Watchtower", "wall": "City Wall",
            "dungeon_hall": "Dungeon Hall", "dungeon_room": "Dungeon Chamber",
            "basement": "Basement", "attic": "Attic",
        }
        return type_names.get(room_type, room_type.capitalize())

    def _generate_room_description(self, room_type: str, zone_name: str, economy: str) -> str:
        """Generate a description for a room based on its type and zone."""
        return f"A {room_type} in {zone_name}. The town's economy is based on {economy}."