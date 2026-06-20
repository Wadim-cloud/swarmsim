import random
from config import WIDTH, HEIGHT

class Agent:
    def __init__(self, id, team):
        self.id = id
        self.team = team
        self.x = random.randint(0, WIDTH-1)
        self.y = random.randint(0, HEIGHT-1)

    def step(self, grid, brain):
        dx, dy = brain.direction(self, grid)

        self.x = max(0, min(WIDTH-1, self.x + dx))
        self.y = max(0, min(HEIGHT-1, self.y + dy))

        grid[self.y][self.x] = self.team