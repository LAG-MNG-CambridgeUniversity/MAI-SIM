import numpy as np
import glob
import sys
import os
import math
import os

import torch
import time 

import torch.optim as optim
import torchvision
from torch.autograd import Variable

from skimage import io
from skimage.exposure import match_histograms
import tifffile
from models import *

import matplotlib.pyplot as plt
from tqdm import tqdm


import argparse
def GetParams():
  opt = argparse.Namespace()

  # data
  opt.weights = 'C:/Users/SIM_ADMIN/Documents/GitHub/AtheSIM/ML-SIM-inference-for-AtheiSIM/DIV2K_randomised_3x3_20200317.pth' 
  opt.imageSize = 255
  opt.root = 'D:/SIM_Data/19-01-2022/split channels/to process'
  opt.out = 'D:/SIM_Data/19-01-2022/split channels/to process'

  # input/output layer options
  opt.norm = 'minmax' # if normalization should not be used
  opt.task = 'simin_gtout'
  opt.scale = 1
  opt.nch_in = 9
  opt.nch_out = 1

  # architecture options 
  opt.model='rcan'#'model to use'  
  opt.narch = 0
  opt.n_resgroups = 3
  opt.n_resblocks = 10
  opt.n_feats = 96
  opt.reduction = 16
  opt.mean = 1 # sequential frames to average

  # test options
  opt.test = False
  opt.cpu = False # not supported for training
  opt.device = torch.device('cuda' if torch.cuda.is_available() and not opt.cpu else 'cpu')
    
  return opt

def remove_dataparallel_wrapper(state_dict):
	r"""Converts a DataParallel model to a normal one by removing the "module."
	wrapper in the module dictionary

	Args:
		state_dict: a torch.nn.DataParallel state dictionary
	"""
	from collections import OrderedDict

	new_state_dict = OrderedDict()
	for k, vl in state_dict.items():
		name = k[7:] # remove 'module.' of DataParallel
		new_state_dict[name] = vl

	return new_state_dict

def EvaluateModel(opt):

    try:
        os.makedirs(opt.out)
    except IOError:
        pass

    opt.fid = open(opt.out + '/log.txt','w')
    print(opt)
    print(opt,'/n',file=opt.fid)
    
    net = GetModel(opt)
    print('loading checkpoint',opt.weights)
    checkpoint = torch.load(opt.weights,map_location=opt.device)

    if type(checkpoint) is dict:
        state_dict = checkpoint['state_dict']
    else:
        state_dict = checkpoint

    net.module.load_state_dict(state_dict)


    


    if opt.root.split('.')[-1] == 'png' or opt.root.split('.')[-1] == 'jpg':
        imgs = [opt.root]
    else:
        imgs = []
        imgs.extend(glob.glob(opt.root + '/*.jpg'))
        imgs.extend(glob.glob(opt.root + '/*.png'))
        imgs.extend(glob.glob(opt.root + '/*.tif'))
        if len(imgs) == 0: # scan everything
            imgs.extend(glob.glob(opt.root + '/**/*.jpg',recursive=True))
            imgs.extend(glob.glob(opt.root + '/**/*.png',recursive=True))
            imgs.extend(glob.glob(opt.root + '/**/*.tif',recursive=True))

    imageSize = opt.imageSize

    for i, imgfile in enumerate(imgs):
        description = 'Processing image [%d/%d]' % (i+1,len(imgs))
        images = io.imread(imgfile)

        nImgs = images.shape[0] // (opt.nch_in*opt.mean)
        filename = os.path.basename(imgfile)[:-4]

        for stack_idx in tqdm(range(nImgs),desc=description):
            stackSubset = images[stack_idx*opt.nch_in*opt.mean:(stack_idx+1)*opt.nch_in*opt.mean]
            stackSubset = stackSubset-np.amin(stackSubset)
            stackSubset = stackSubset/np.amax(stackSubset)
            for f in range(1,opt.nch_in*opt.mean):
                stackSubset[f,:,:] =  match_histograms(stackSubset[f,:,:],stackSubset[0,:,:])
            wf = np.mean(stackSubset,0)
            rolling = np.zeros(wf.shape)
            for slice in range(opt.mean):

                sub_tensor = torch.from_numpy(stackSubset[opt.nch_in*slice:opt.nch_in*(slice+1)])
                sub_tensor = sub_tensor.unsqueeze(0)
                sub_tensor = sub_tensor.type(torch.FloatTensor)
                
                
                with torch.no_grad():
                    if opt.cpu:
                        sr = net(sub_tensor)
                    else:
                        sr = net(sub_tensor.cuda())
                    sr = sr.cpu()

                    sr = torch.clamp(sr[0],0,1)
                    sr_frame = sr.numpy()
                    sr_frame = np.squeeze(sr_frame)                               
                rolling += sr_frame
                #if stack_idx == 0:
                #    reference = np.copy(sr_frame)
                #else: 
                #    sr_frame = match_histograms(sr_frame,reference)

            
            try:
                wf = (wf * 65000/np.amax(wf)).astype('uint16')
                svPath = opt.out + '/' + filename +'_wf.tif'
                tifffile.imsave(svPath,wf,append=True)


                rolling = (rolling * 65000/opt.mean).astype('uint16')
                svPath = opt.out + '/' + filename +'_sr.tif'
                tifffile.imsave(svPath,rolling,append=True)
            except:
                print('Permission error')
                break


if __name__ == '__main__':
    opt = GetParams()

    EvaluateModel(opt)
