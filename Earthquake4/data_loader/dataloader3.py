from torchsummary import summary
from functions import *

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# train/validation/test 用此dataloader
class EarthquakeDataLoader():
    def __init__(self,seismic_path,label_path,batch_size,train_number_of_pictures=1, val_number_of_pictures=1,train_start=1,val_start=0):
        self.train_loader,self.val_loader = self.train_val_dataset(seismic_path,label_path,batch_size,train_number_of_pictures, val_number_of_pictures,train_start,val_start)

    def train_val_dataset(self, seismic_path,label_path, batch_size, train_number_of_pictures, val_number_of_pictures, train_start, val_start):


        os.environ["CUDA_VISIBLE_DEVICES"] = "3"  # Only GPU 1 is visible to this code
        time1 = time.time()
        # print("RandomBrightnessContrast")
        # modelNo
        # Unet --> 0
        # Deeplab --> 1
        # HED --> 2
        # RCF --> 3
        # CED --> 4

        t_start = time.time()
        seismic = np.load(seismic_path)
        fault = np.load(label_path)
        print("load in {} sec".format(time.time() - t_start))

        # In[4]:

        # print(seismic.shape, fault.shape)
        # seismic = np.moveaxis(seismic[4:1807],-2,-1)
        print("seismic.shape, fault.shape",seismic.shape, fault.shape)
        print("seismic.max(), seismic.min(), fault.max(), fault.min()",seismic.max(), seismic.min(), fault.max(), fault.min())
        # # reorder input data to same order IL, Z, XL

        # # In[5]:

        # seismic = (seismic-seismic.min(axis=(1,2), keepdims=True))/(seismic.max(axis=(1,2), keepdims=True)-seismic.min(axis=(1,2), keepdims=True))
        # print(seismic.shape)

        # # In[6]:

        IL, Z, XL = fault.shape

        # In[7]:

        best_model_fpath = 'hed_192_96_900200_seed.model'
        best_iou_threshold = 0.5
        epoches = 10
        patience = 20
        im_height = Z
        im_width = XL
        splitsize = 96
        stepsize = 48
        overlapsize = splitsize - stepsize
        pixelThre = int(0.03 * splitsize * splitsize)
        print("pixelThre ",pixelThre)

        # In[8]:


        horizontal_splits_number = int(np.ceil((im_width - overlapsize) / stepsize))
        print("horizontal_splits_number", horizontal_splits_number)
        width_after_pad = stepsize * horizontal_splits_number + overlapsize
        print("width_after_pad", width_after_pad)
        left_pad = int((width_after_pad - im_width) / 2)
        right_pad = width_after_pad - im_width - left_pad
        print("left_pad,right_pad", left_pad, right_pad)

        vertical_splits_number = int(np.ceil((im_height - overlapsize) / stepsize))
        print("vertical_splits_number", vertical_splits_number)
        height_after_pad = stepsize * vertical_splits_number + overlapsize
        print("height_after_pad", height_after_pad)
        top_pad = int((height_after_pad - im_height) / 2)
        bottom_pad = height_after_pad - im_height - top_pad
        print("top_pad,bottom_pad", top_pad, bottom_pad)

        # In[17]:
        # train_dataset

        t_start = time.time()
        X = []
        Y = []
        for i in range(train_start, train_number_of_pictures+train_start, 1):
            mask = fault[i]
            splits = split_Image(mask, True, top_pad, bottom_pad, left_pad, right_pad, splitsize, stepsize,
                                 vertical_splits_number, horizontal_splits_number)
            #     print(splits.shape)
            t = (splits.sum((1, 2)) < pixelThre)
            no_label_element_index = list(compress(range(len(t)), t))
            # get all the indexes of the no label pieces by adding elements in axis 2 and 3.
            splits = np.delete(splits, no_label_element_index, 0)  # delete element i along axis 0
            #     print("splits.shape", splits.shape)
            Y.extend(splits)

            img = seismic[i]
            splits = split_Image(img, True, top_pad, bottom_pad, left_pad, right_pad, splitsize, stepsize,
                                 vertical_splits_number, horizontal_splits_number)
            splits = np.delete(splits, no_label_element_index, 0)  # delete element i along axis 0
            #     print("splits.shape", splits.shape)
            X.extend(splits)
        #     break

        print("len(Y)",len(Y))
        print("len(X)",len(X))
        print("X[0].shape",X[0].shape)
        print("read images in {} sec".format(time.time() - t_start))

        # In[20]:

        t_start = time.time()
        X = np.asarray(X, dtype=np.float32)
        Y = np.asarray(Y, dtype=np.float32)
        print(X.shape)
        print(Y.shape)
        print("read images in {} sec".format(time.time() - t_start))

        # In[22]:

        if len(Y.shape) == 3:
            Y = np.expand_dims(Y, axis=-1)
        if len(X.shape) == 3:
            X = np.expand_dims(X, axis=-1)
        print(X.shape)
        print(Y.shape)

        X_train = X
        Y_train = Y

        t_start = time.time()
        X = []
        Y = []
        for i in range(val_start, val_number_of_pictures+val_start, 1):
            mask = fault[i]
            splits = split_Image(mask, True, top_pad, bottom_pad, left_pad, right_pad, splitsize, stepsize,
                                 vertical_splits_number, horizontal_splits_number)
            #     print(splits.shape)
            t = (splits.sum((1, 2)) < pixelThre)
            no_label_element_index = list(compress(range(len(t)), t))
            # get all the indexes of the no label pieces by adding elements in axis 2 and 3.
            splits = np.delete(splits, no_label_element_index, 0)  # delete element i along axis 0
            #     print("splits.shape", splits.shape)
            Y.extend(splits)

            img = seismic[i]
            splits = split_Image(img, True, top_pad, bottom_pad, left_pad, right_pad, splitsize, stepsize,
                                 vertical_splits_number, horizontal_splits_number)
            splits = np.delete(splits, no_label_element_index, 0)  # delete element i along axis 0
            #     print("splits.shape", splits.shape)
            X.extend(splits)
        #     break

        print(len(Y))
        print(len(X))
        print(X[0].shape)
        print("read images in {} sec".format(time.time() - t_start))

        # In[20]:

        t_start = time.time()
        X = np.asarray(X, dtype=np.float32)
        Y = np.asarray(Y, dtype=np.float32)
        print(X.shape)
        print(Y.shape)
        print("read images in {} sec".format(time.time() - t_start))

        # In[22]:

        if len(Y.shape) == 3:
            Y = np.expand_dims(Y, axis=-1)
        if len(X.shape) == 3:
            X = np.expand_dims(X, axis=-1)
        print(X.shape)
        print(Y.shape)

        X_val = X
        Y_val = Y

        print("X_train", X_train.shape)
        print("X_val", X_val.shape)

        print("Y_train", Y_train.shape)
        print("Y_val", Y_val.shape)

        # In[ ]:

        # aug_times = 1

        # t_start = time.time()
        # origin_train_size = len(X_train)
        # print(origin_train_size)
        # X_train_aug = np.zeros((origin_train_size*aug_times,splitsize,splitsize,1))
        # Y_train_aug = np.zeros((origin_train_size*aug_times,splitsize,splitsize,1))
        # for i in range(len(X_train)):
        #     for j in range(aug_times):
        #         aug = strong_aug(p=1)
        #         augmented = aug(image=X_train[i], mask=Y_train[i])
        #         X_train_aug[origin_train_size*j + i] = augmented['image']
        #         Y_train_aug[origin_train_size*j + i] = augmented['mask']
        # print("read images in {} sec".format(time.time()-t_start))

        # X_train_aug = X_train_aug.astype(np.float32)
        # Y_train_aug = Y_train_aug.astype(np.float32)
        # if len(X_train)==origin_train_size:
        #     X_train = np.append(X_train,X_train_aug, axis=0)
        # if len(Y_train)==origin_train_size:
        #     Y_train = np.append(Y_train, Y_train_aug, axis=0)
        # print("X_train after aug",X_train.shape)
        # print("Y_train after aug",Y_train.shape)
        # print("read images in {} sec".format(time.time()-t_start))
        # X_train = X_train.astype(np.float32)
        # Y_train = Y_train.astype(np.float32)
        # #-----------------------
        # t_start = time.time()
        # origin_val_size = len(X_val)
        # print(origin_val_size)
        # X_val_aug = np.zeros((origin_val_size*aug_times,splitsize,splitsize,1))
        # Y_val_aug = np.zeros((origin_val_size*aug_times,splitsize,splitsize,1))
        # for i in range(len(X_val)):
        #     for j in range(aug_times):
        #         aug = strong_aug(p=1)
        #         augmented = aug(image=X_train[i], mask=Y_train[i])
        #         X_val_aug[origin_val_size*j + i] = augmented['image']
        #         Y_val_aug[origin_val_size*j + i] = augmented['mask']
        # print("read images in {} sec".format(time.time()-t_start))

        # X_val_aug = X_val_aug.astype(np.float32)
        # Y_val_aug = Y_val_aug.astype(np.float32)
        # if len(X_val)==origin_val_size:
        #     X_val = np.append(X_val,X_val_aug, axis=0)
        # if len(Y_val)==origin_val_size:
        #     Y_val = np.append(Y_val, Y_val_aug, axis=0)
        # print("X_val after aug",X_val.shape)
        # print("Y_val after aug",Y_val.shape)
        # print("read images in {} sec".format(time.time()-t_start))
        # X_val = X_val.astype(np.float32)
        # Y_val = Y_val.astype(np.float32)
        # -----------------------
        X_train = np.moveaxis(X_train, -1, 1)
        Y_train = np.moveaxis(Y_train, -1, 1)
        X_val = np.moveaxis(X_val, -1, 1)
        Y_val = np.moveaxis(Y_val, -1, 1)
        print("X_train", X_train.shape)
        print("X_val", X_val.shape)
        print("Y_train", Y_train.shape)
        print("Y_val", Y_val.shape)

        # In[ ]:

        # dataset
        # idea from: https://www.kaggle.com/erikistre/pytorch-basic-u-net

        class faultsDataset(torch.utils.data.Dataset):

            def __init__(self, preprocessed_images, train=True, preprocessed_masks=None):
                """
                Args:
                    text_file(string): path to text file
                    root_dir(string): directory with all train images
                """
                self.train = train
                self.images = preprocessed_images
                self.masks = preprocessed_masks

            def __len__(self):
                return len(self.images)

            def __getitem__(self, idx):
                image = self.images[idx]
                #         mask = None
                # #         if self.train:
                mask = self.masks[idx]
                return (image, mask)

        # In[32]:

        faults_dataset_train = faultsDataset(X_train, train=True, preprocessed_masks=Y_train)
        faults_dataset_val = faultsDataset(X_val, train=False, preprocessed_masks=Y_val)
        # faults_dataset_test = faultsDataset(X_test, train=False, preprocessed_masks=Y_test)

        # batch_size = 64

        train_loader = torch.utils.data.DataLoader(dataset=faults_dataset_train,
                                                   batch_size=batch_size,
                                                   shuffle=True)

        val_loader = torch.utils.data.DataLoader(dataset=faults_dataset_val,
                                                 batch_size=batch_size,
                                                 shuffle=False)

        # test_loader = torch.utils.data.DataLoader(dataset=faults_dataset_test,
        #                                            batch_size=batch_size,
        #                                            shuffle=False)
        return train_loader,val_loader


# save——predicted——picture 用此dataloader
class EarthquakeDataLoader2():
    def __init__(self,seismic_path,batch_size, val_number_of_pictures,val_start):
       self.test_loader,self.faults_dataset_test = self.train_val_dataset(seismic_path,batch_size, val_number_of_pictures,val_start)

    def train_val_dataset(self, seismic_path, batch_size, val_number_of_pictures, val_start):
        seis = np.load(seismic_path)
        IL, Z, XL = seis.shape
        print("IL, Z, XL",IL, Z, XL)
        print(seis.shape)

        im_height = Z
        im_width = XL
        splitsize = 96
        stepsize = 48  # overlap half
        overlapsize = splitsize - stepsize

        horizontal_splits_number = int(np.ceil((im_width) / stepsize))
        print(horizontal_splits_number)
        width_after_pad = stepsize * horizontal_splits_number + 2 * overlapsize
        print(width_after_pad)
        left_pad = int((width_after_pad - im_width) / 2)
        right_pad = width_after_pad - im_width - left_pad
        print(left_pad, right_pad)

        vertical_splits_number = int(np.ceil((im_height) / stepsize))
        print(vertical_splits_number)
        height_after_pad = stepsize * vertical_splits_number + 2 * overlapsize
        print(height_after_pad)
        top_pad = int((height_after_pad - im_height) / 2)
        bottom_pad = height_after_pad - im_height - top_pad
        print(top_pad, bottom_pad)

        horizontal_splits_number = horizontal_splits_number + 1
        print(horizontal_splits_number)
        vertical_splits_number = vertical_splits_number + 1
        print(vertical_splits_number)

        halfoverlapsize = int(overlapsize / 2)
        print(halfoverlapsize)

        # In[ ]:

        print(len(seis))

        # In[ ]:

        # seis_norm = seis
        # seis_norm = (seis-seis.min(axis=(1,2), keepdims=True))/(seis.max(axis=(1,2), keepdims=True)-seis.min(axis=(1,2), keepdims=True))
        # print(seis_norm.shape)

        # In[ ]:

        # count = 0
        # for l in range(0,len(seis),5):
        #     count+=1
        #     print(l)
        # print(count)

        # In[ ]:

        t_start = time.time()
        X_list = []
        for i in range(val_start, val_start+val_number_of_pictures, 1):
            img = seis[i]
            X_list.extend(split_Image(img, True, top_pad, bottom_pad, left_pad, right_pad, splitsize, stepsize,
                                      vertical_splits_number, horizontal_splits_number))

        print(len(X_list))
        print(X_list[0].shape)
        print("read images in {} sec".format(time.time() - t_start))
        X = np.asarray(X_list)
        print(X.shape)
        print("read images in {} sec".format(time.time() - t_start))

        # X_norm = X

        # if len(X_norm.shape) == 3:
        #     X_norm = np.expand_dims(X_norm, axis=1)
        # print(X_norm.shape) #float32

        # In[ ]:

        X = X.astype(np.float32)
        X = np.expand_dims(X, 1)
        print(X.shape)

        # In[ ]:

        # plt.imshow(np.squeeze(X[0]))
        # plt.show()

        # In[ ]:

        # # images = Variable(images.to(device))
        # inputs = Variable(torch.from_numpy(X[900:904]).to(device))
        # device = torch.device('cuda')
        # # model = TheModelClass(*args, **kwargs)
        # model = HED()
        # print("use model HED")
        # best_model_fpath = 'hed_96_48_checkpoint.pt' #hed_96_48_checkpoint.pt
        # save_path = 'thebepred_hed_blend'
        # model.load_state_dict(torch.load(best_model_fpath, map_location=device))
        # model.to(device)
        # outputs = model(inputs)
        # predicts = outputs[-2]
        # print(predicts[0].shape)
        # plt.imshow(np.squeeze(predicts[0].detach().cpu().numpy()))
        # plt.show()

        # In[ ]:

        # # idea from: https://www.kaggle.com/erikistre/pytorch-basic-u-net
        # class faultsDataset(torch.utils.data.Dataset):

        #     def __init__(self,preprocessed_images,train=True, preprocessed_masks=None):
        #         """
        #         Args:
        #             text_file(string): path to text file
        #             root_dir(string): directory with all train images
        #         """
        #         self.train = train
        #         self.images = preprocessed_images
        #         if self.train:
        #             self.masks = preprocessed_masks
        # #         self.masks = preprocessed_masks

        #     def __len__(self):
        #         return len(self.images)

        #     def __getitem__(self, idx):
        #         image = self.images[idx]
        #         mask = None
        #         if self.train:
        #             mask = self.masks[idx]
        #         return (image, mask)
        # idea from: https://www.kaggle.com/erikistre/pytorch-basic-u-net
        class faultsDataset(torch.utils.data.Dataset):

            def __init__(self, preprocessed_images):
                """
                Args:
                    text_file(string): path to text file
                    root_dir(string): directory with all train images
                """
                #         self.train = train
                self.images = preprocessed_images

            #         if self.train:
            #             self.masks = preprocessed_masks
            # #         self.masks = preprocessed_masks

            def __len__(self):
                return len(self.images)

            def __getitem__(self, idx):
                image = self.images[idx]
                return image

        #         mask = None
        #         if self.train:
        #             mask = self.masks[idx]
        #         return (image, mask)

        # In[ ]:

        # faults_dataset_test = faultsDataset(X_norm, train=False, preprocessed_masks=None)

        # batch_size = 64

        # test_loader = torch.utils.data.DataLoader(dataset=faults_dataset_test,
        #                                            batch_size=batch_size,
        #                                            shuffle=False)
        faults_dataset_test = faultsDataset(X)


        test_loader = torch.utils.data.DataLoader(dataset=faults_dataset_test,
                                                  batch_size=batch_size,
                                                  shuffle=False)

        return test_loader,faults_dataset_test
