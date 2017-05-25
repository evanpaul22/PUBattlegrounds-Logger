class Player_node:
    knockout_refs = []
    killer_ref = None

    def __init__(self, victim, villain, weapon=None, kill=True):
        self.name = victim
        self.killer_name = villain
        self.weapon = weapon
        self.kill = kill
