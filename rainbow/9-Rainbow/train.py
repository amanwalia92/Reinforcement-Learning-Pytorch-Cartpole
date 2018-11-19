import os
import sys
import gym
import random
import numpy as np

import torch
import torch.optim as optim
import torch.nn.functional as F
from model import QNet
from memory import Memory_With_TDError
from tensorboardX import SummaryWriter

from config import env_name, initial_exploration, batch_size, update_target, goal_score, log_interval, device, replay_memory_capacity, lr, beta_start

def update_target_model(oneline_net, target_net):
    # Target <- Net
    target_net.load_state_dict(oneline_net.state_dict())


def main():
    env = gym.make(env_name)
    env.seed(500)
    torch.manual_seed(500)

    num_inputs = env.observation_space.shape[0]
    num_actions = env.action_space.n
    print('state size:', num_inputs)
    print('action size:', num_actions)

    oneline_net = QNet(num_inputs, num_actions)
    target_net = QNet(num_inputs, num_actions)
    update_target_model(oneline_net, target_net)

    optimizer = optim.Adam(oneline_net.parameters(), lr=lr)
    writer = SummaryWriter('logs')

    oneline_net.to(device)
    target_net.to(device)
    oneline_net.train()
    target_net.train()
    memory = Memory_With_TDError(replay_memory_capacity)
    running_score = 0
    steps = 0
    beta = beta_start
    loss = 0

    for e in range(3000):
        done = False

        score = 0
        state = env.reset()
        state = torch.Tensor(state).to(device)
        state = state.unsqueeze(0)

        while not done:
            steps += 1

            action = target_net.get_action(state)
            next_state, reward, done, _ = env.step(action)

            next_state = torch.Tensor(next_state)
            next_state = next_state.unsqueeze(0)

            mask = 0 if done else 1
            reward = reward if not done or score == 499 else -1
            action_one_hot = np.zeros(2)
            action_one_hot[action] = 1
            memory.push(state, next_state, action_one_hot, reward, mask)

            score += reward
            state = next_state

            if steps > initial_exploration:
                beta += 0.00005
                beta = min(1, beta)

                batch, weights = memory.sample(batch_size, oneline_net, target_net, beta)
                loss = QNet.train_model(oneline_net, target_net, optimizer, batch, weights)

                if steps % update_target == 0:
                    update_target_model(oneline_net, target_net)

        score = score if score == 500.0 else score + 1
        running_score = 0.99 * running_score + 0.01 * score
        if e % log_interval == 0:
            print('{} episode | score: {:.2f} |  beta: {:.2f}'.format(
                e, running_score, beta))
            writer.add_scalar('log/score', float(running_score), e)
            writer.add_scalar('log/loss', float(loss), e)

        if running_score > goal_score:
            break


if __name__=="__main__":
    main()