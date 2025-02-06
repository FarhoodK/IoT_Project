def collect(num_balls, balls_distance, first_ball_rank):
    balls = []
    tot_distance = 0
    for i in range(num_balls):
        balls.append(f"Ball {i+1}")
    return print(balls)

collect(5, 10, 3)