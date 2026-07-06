def mod_id_and_game_id_to_mod_uid(game_id: int, mod_id: int) -> str:
    # Perform the left shift operation and combine the values
    return str((game_id << 32) + mod_id)

def file_id_and_game_id_to_mod_uid(game_id: int, file_id: int) -> str:
    # Perform the left shift operation and combine the values
    return str((game_id << 32) + file_id)