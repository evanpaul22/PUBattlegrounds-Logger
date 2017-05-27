class Node:
    knockout_refs = []
    killer_ref = None

    def __init__(self, victim, villain, weapon=None, kill_flag=True):
        self.name = victim
        self.killer_name = villain
        self.weapon = weapon
        self.kill_flag = kill_flag
