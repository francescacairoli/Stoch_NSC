from SpikingNeuron import *
import pickle

past_horizon = 20
future_horizon = 20

n_points_dataset = 20000
noise_sigma = 1.

sn_model = SpikingNeuron(time_horizon=past_horizon, noise_sigma=noise_sigma)


full_trajs = sn_model.gen_trajectories(n_points_dataset)
noisy_measurments = sn_model.simple_noisy_sensor(full_trajs)
labels = sn_model.generate_labels(full_trajs[:,:,-1], future_horizon=future_horizon)


dataset_dict = {"x": full_trajs, "y": noisy_measurments, "cat_labels": labels}

filename = 'Datasets/dataset_{}points_pastH={}_futureH={}_noise_sigma={}.pickle'.format(n_points_dataset, past_horizon, future_horizon, noise_sigma)

with open(filename, 'wb') as handle:
	pickle.dump(dataset_dict, handle)
handle.close()
print("Data stored in: ", filename)
