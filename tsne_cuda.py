# -*- coding: utf-8 -*-
"""tsne-cuda.ipynb

Method to run TSNE evaluation on the existing clusters to generate visualizations of the embedding space.
"""

from tsnecuda import TSNE
import seaborn as sns
import torch
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import torch, torch.nn as nn
import argparse
import sys
import torch, torch.nn as nn
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
sys.path.insert(1, 'dataloaders/')

import SOP_Loader as loader
import model as net
import train as train

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

parser = argparse.ArgumentParser()

parser.add_argument('--batch_sz', type = int, default = 80, help = 'batch size for complete dataset')
parser.add_argument('--cluster_batch_sz', type = int, default = 40, help = 'batch size for each cluster')
parser.add_argument('--dataset_name', default = 'SOP', help = 'name of dataset used')
parser.add_argument('--dataset_path', default = '../Stanford_Online_Products', help = 'path for input data')

parser.add_argument('--arch', default = 'resnet50', help = 'model architecture used')
parser.add_argument('--pretrained', type = bool, default = True, help = 'Require pretrained model')

# number of workers for data loader
parser.add_argument('--nb_workers', type = int, default = 16, help = 'Number of workers for dataloader')
parser.add_argument('--samples_per_class', type = int, default = 4, help = 'Number of samples drawn per class while building dataloader')
parser.add_argument('--cluster_samples_per_class', type = int, default = 4, help = 'Number of samples of a cluster drawn per class while building dataloader')

parser.add_argument('--lr', type = float, default = 0.00001, help = 'learning rate')
parser.add_argument('--decay', type = float, default = 0.0004, help = 'decay rate for adam')
parser.add_argument('--tau', default = '30,35', help = 'milstones for multistepLR')
parser.add_argument('--gamma', type = float, default = 0.3, help = 'gamma for multistepLR')

parser.add_argument('--initial_epochs', type = int, default =20, help = 'train full learner for initial_epochs')
# number of initial epochs
parser.add_argument('--num_epochs', type = int, default = 40, help = 'number of epochs')
parser.add_argument('--num_epochs_cluster', type = int, default =1, help = 'number of epochs per cluster')
parser.add_argument('--num_T', type = int, default = 20, help= 'each cluster is trained num_T times before joining back learners')

parser.add_argument('--loss_type', default = 'tripletloss', help = 'loss function used')
parser.add_argument('--triplet_margin', type = float, default = 0.2, help = 'margin value for triplet loss')
parser.add_argument('--sampling_type', default = 'semihard', help = 'type of sampling used')

parser.add_argument('--num_learners', type = int, default = 8, help = 'number of learners embedding space is divided into')
parser.add_argument('--embed_dim', type = int, default = 128, help = 'dimension of embedded space')

parser.add_argument('--faiss_type', default = 'gpu', help = 'use cpu or gpu for faiss clustering')

parser.add_argument('--cluster_save', type = bool, default = True, help = 'use save clusters method')

parser.add_argument('--debug', type = bool, default = False, help = 'debug option')

parser.add_argument('--save_model', type = bool, default = True, help = 'save model?')
parser.add_argument('--model_dict_path', default = './model_dict.pth', help = 'file in which model parameters are saved')
parser.add_argument('--load_model', type = bool, default = True, help = 'load model parameters?')
args = parser.parse_args()

dataloaders = loader.give_dataloaders(args)
# print(len(dataloaders['training'].dataset))
model = net.ResNet50(args)
if(torch.cuda.device_count() > 1):
    model = nn.DataParallel(model)
 
model.to(device)

if(args.load_model):
    model.load_state_dict(torch.load(args.model_dict_path))

embed_num = -1
test_dataloader = dataloaders['testing']
torch.cuda.empty_cache()
n_classes = len(test_dataloader.dataset.avail_classes)
with torch.no_grad():
    target_labels, feature_coll = [],[]
    test_iter = iter(test_dataloader)
    # image_paths= [x[0] for x in test_dataloader.dataset.image_list]
    for idx,inp in enumerate(test_iter):
        input_img,target = inp[-1], inp[0]
        target_labels.extend(target.numpy().tolist())
        out = model(input_img.to(device),embed_num = embed_num)
        feature_coll.extend(out.cpu().detach().numpy().tolist())

    target_labels = np.hstack(target_labels).reshape(-1,1)
    feature_coll  = np.vstack(feature_coll).astype('float32')

#tsne_model = TSNE(n_components=2, perplexity=1000.0, n_iter=10000).fit_transform(feature_coll)
pca = PCA(n_components=2)
pca_result = pca.fit_transform(feature_coll)
tsne = TSNE(n_components=2, verbose=1, perplexity=40, n_iter=300)
tsne_results = tsne.fit_transform(pca_result)
tsne_df = pd.DataFrame(tsne_results)
target_labels = pd.DataFrame(target_labels)
tsne_df = pd.concat([tsne_df,target_labels], axis=1)
tsne_df.to_csv('tsne_viz.csv')

sns.FacetGrid(tsne_df, hue="label" , size=6).map(plt.scatter, 0, 1).add_legend()

plt.show()
