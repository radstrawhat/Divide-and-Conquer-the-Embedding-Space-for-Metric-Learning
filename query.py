# -*- coding: utf-8 -*-
"""
Created on Mon Apr 20 14:10:03 2020

Code for generating similar images to a query image using the output embedding space.
The approach taken for this was to use the search index module inbuilt into the FAISS package, which allowed us to use the resources of the present GPU’s and calculate the closest images to the query image using euclidean (L2) distance.
"""
import warnings
warnings.filterwarnings("ignore")

import numpy as np

import torch
from PIL import Image
from torchvision import transforms

from scipy.spatial.distance import squareform, pdist

try:
    import faiss
    using_faiss = True
    print('using faiss for clustering')
except:
    using_faiss = False
    print('using sklearn.cluster for clustering')

import utils as utils

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
feature_map_creatured = False

def ensure_3dim(img):
    '''
    Function to ensure 3 dimensional RGB image
    '''
        if len(img.size)==2:
            img = img.convert('RGB')
        return img

def query(args,test_dataloader,eval_dataloader,model):
    '''
    Method to calculate the closest points in the embedding space.
    This gives a list of the points, each of which is one image, using FAISS search_index.
    '''
    global feature_map_creatured
    
    normalize = transforms.Normalize(mean=[0.485, 0.456, 0.406],std=[0.229, 0.224, 0.225])
    transf_list = []
    transf_list.extend([transforms.Resize(256),
                        transforms.CenterCrop(224) if args.arch=='resnet50' else transforms.CenterCrop(224)])

    transf_list.extend([transforms.ToTensor(), normalize])
    trans = transforms.Compose(transf_list)
    
    query_im = trans(ensure_3dim(Image.open(args.query_im_path))).view(1,3,224,224)
    # Empty cache to prevent memory overflow in the GPU.
    torch.cuda.empty_cache()
    with torch.no_grad():
        if(not feature_map_creatured):
            target_labels, feature_coll, paths = [],[],[]
            test_iter = iter(test_dataloader)
            for idx,inp in enumerate(test_iter):
                input_img,target,im_path = inp[1], inp[0], inp[-1]
                target_labels.extend(target.numpy().tolist())
                paths.extend(list(im_path))
                out = model(input_img.to(device))
                feature_coll.extend(out.cpu().detach().numpy().tolist())
                if(args.debug):
                    if(idx==49): break
            eval_iter = iter(eval_dataloader)
            for idx,inp in enumerate(eval_iter):
                input_img,target,im_path = inp[1], inp[0], inp[-1]
                target_labels.extend(target.numpy().tolist())
                paths.extend(list(im_path))
                out = model(input_img.to(device))
                feature_coll.extend(out.cpu().detach().numpy().tolist())
                if(args.debug):
                    if(idx==49): break

            target_labels = np.hstack(target_labels).reshape(-1,1)
            paths = np.hstack(paths).reshape(-1,1)
            feature_coll  = np.vstack(feature_coll).astype('float32')
            feature_map_creatured = True
        
        query_out = model(query_im.to(device))
        torch.cuda.empty_cache()
        
        if(using_faiss):
            d = feature_coll.shape[-1]
    
            if(args.faiss_type == 'gpu'):
                faiss_search_index = utils.create_GpuIndex(d = d)
            else:
                faiss_search_index  = faiss.IndexFlatL2(d)
            
            faiss_search_index.add(feature_coll)
            _, k_closest_points = faiss_search_index.search(query_out.cpu().detach().numpy(), args.num_query)
            
        else:    
            k_closest_points  = squareform(pdist(feature_coll)).argsort(1)[:, :args.num_query]
        

    return paths[k_closest_points]
