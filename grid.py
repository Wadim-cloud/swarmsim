import numpy as np
from config import WIDTH, HEIGHT, EMPTY, RED, BLUE

attraction_field = np.zeros((HEIGHT, WIDTH))
threat_field = np.zeros((HEIGHT, WIDTH))
frontier_field = np.zeros((HEIGHT, WIDTH))

def update_fields(grid):
    attraction_field.fill(0)
    threat_field.fill(0)
    frontier_field.fill(0)

    for y in range(1, HEIGHT-1):
        for x in range(1, WIDTH-1):

            v = grid[y][x]

            if v == EMPTY:
                attraction_field[y][x] = 1

            if v in (RED, BLUE):
                threat_field[y][x] = 1

            neighbors = [
                grid[y+1][x], grid[y-1][x],
                grid[y][x+1], grid[y][x-1]
            ]

            if EMPTY in neighbors and (RED in neighbors or BLUE in neighbors):
                frontier_field[y][x] = 1