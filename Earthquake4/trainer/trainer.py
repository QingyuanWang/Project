import numpy as np
import torch
from torchvision.utils import make_grid
from base import BaseTrainer
from utils import inf_loop, MetricTracker
from functions import *
from model.loss import *
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
class Trainer(BaseTrainer):
    """
    Trainer class
    """
    def __init__(self, model, criterion, metric_ftns, optimizer, config, data_loader,
                 valid_data_loader, lr_scheduler=None, len_epoch=None):
        super().__init__(model, criterion, metric_ftns, optimizer, config)
        self.config = config
        self.data_loader = data_loader
        if len_epoch is None:
            # epoch-based training
            self.len_epoch = len(self.data_loader)
        else:
            # iteration-based training
            self.data_loader = inf_loop(data_loader)
            self.len_epoch = len_epoch
        self.valid_data_loader = valid_data_loader
        self.do_validation = self.valid_data_loader is not None
        self.lr_scheduler = lr_scheduler
        self.log_step = int(np.sqrt(data_loader.batch_size))

        self.train_metrics = MetricTracker('loss', *[m.__name__ for m in self.metric_ftns], writer=self.writer)
        self.valid_metrics = MetricTracker('loss', *[m.__name__ for m in self.metric_ftns], writer=self.writer)
        splitsize = 96
        stepsize = 48


    def _progress(self, batch_idx):
        base = '[{}/{} ({:.0f}%)]'
        if hasattr(self.data_loader, 'n_samples'):
            current = batch_idx * self.data_loader.batch_size
            total = self.data_loader.n_samples
        else:
            current = batch_idx
            total = self.len_epoch
        return base.format(current, total, 100.0 * current / total)


    def _train_epoch(self, epoch):
        train_losses = []
        train_accuracies = []
        self.model.train()
        self.train_metrics.reset()
        ##参数
        modelNo=self.modelNo
        splitsize = 96
        stepsize = 48
        ##summary(self.model, (1, splitsize, splitsize))
        print("modelNo",modelNo)
        best_iou_threshold = 0.5

        for batch_idx, (images, masks) in enumerate(self.data_loader):
            #images, masks = images.to(self.device), masks.to(self.device)
        # for images, masks in self.data_loader:
            # torch.cuda.empty_cache()
            images = Variable(images.to(device))
            masks = Variable(masks.to(device))
            data = images
            target = masks
            outputs = self.model(images)
            loss = torch.zeros(1).to(device)
            y_preds = outputs
            bceloss = nn.BCELoss()
            # if modelNo == 0 or modelNo == 1 or modelNo == 4:
            #     #             print("bceloss")
            #     loss = bceloss(outputs, masks)
            # #             loss = cross_entropy_loss_HED(outputs, masks)
            # #             loss = nn.BCEWithLogitsLoss(outputs, masks)
            # elif modelNo == 2 or modelNo == 21:
            #     for o in range(5):
            #         loss = loss + cross_entropy_loss_HED(outputs[o], masks)
            #     loss = loss + bceloss(outputs[-1], masks)
            #     y_preds = outputs[-1]
            # elif modelNo == 3:
            #     for o in outputs:
            #         loss = loss + cross_entropy_loss_RCF(o, masks)
            #     y_preds = outputs[-1]
            if modelNo == 0 or modelNo == 1:
                #             print("bceloss")

                loss = self.criterion(outputs, masks)
            #             loss = cross_entropy_loss_HED(outputs, masks)
            #             loss = nn.BCEWithLogitsLoss(outputs, masks)
            elif modelNo == 2:
                for o in range(5):
                    loss = loss + self.criterion(outputs[o], masks)
                loss = loss + bceloss(outputs[-1], masks)
                y_preds = outputs[-1]
            elif modelNo == 3:
                for o in outputs:
                    loss = loss + self.criterion(o, masks)
                y_preds = outputs[-1]

            loss.backward()
            self.optimizer.step()
            self.optimizer.zero_grad()
            train_losses.append(loss.data)
            predicted_mask = y_preds > best_iou_threshold
            train_acc = iou_pytorch(predicted_mask.squeeze(1).byte(), masks.squeeze(1).byte())
            train_accuracies.append(train_acc.mean())

            self.writer.set_step((epoch - 1) * self.len_epoch )
            self.train_metrics.update('loss', loss.item())
            # print("loss\n",loss.item())
            for met in self.metric_ftns:
                self.train_metrics.update(met.__name__, met(predicted_mask, masks))

            if batch_idx % self.log_step == 0:
                self.logger.debug('Train Epoch: {} {} Loss: {:.6f}'.format(
                    epoch,
                    self._progress(batch_idx),
                    loss.item()))
                self.writer.add_image('input', make_grid(data.cpu(), nrow=8, normalize=True))

            if batch_idx == self.len_epoch:
                break
        log = self.train_metrics.result()

        if self.do_validation:
            val_log,val_losses = self._valid_epoch(epoch)
            log.update(**{'val_'+k : v for k, v in val_log.items()})

        if self.lr_scheduler is not None:
            #self.lr_scheduler.step(torch.mean(torch.stack(val_losses)))
            self.lr_scheduler.step(val_losses)

        return log

    def _valid_epoch(self,epoch):
        val_losses = []
        val_accuracies = []
        labelled_val_accuracies = []
        modelNo = self.modelNo
        best_iou_threshold = 0.5
        splitsize = 96
        stepsize = 48
        bceloss = nn.BCELoss()
        self.model.eval()
        self.valid_metrics.reset()
        for batch_idx, (images, masks) in enumerate(self.valid_data_loader):
            #images, masks = images.to(self.device), masks.to(self.device)
            images = Variable(images.to(device))
            masks = Variable(masks.to(device))
            data = images
            target = masks

            outputs = self.model(data)
            loss = torch.zeros(1).to(device)
            y_preds = outputs
            if modelNo == 0 or modelNo == 1:
                #             print("bceloss")

                loss = self.criterion(outputs, masks)
            #             loss = cross_entropy_loss_HED(outputs, masks)
            #             loss = nn.BCEWithLogitsLoss(outputs, masks)
            elif modelNo == 2:
                for o in range(5):
                    loss = loss + self.criterion(outputs[o], masks)
                loss = loss + bceloss(outputs[-1], masks)
                y_preds = outputs[-1]
            elif modelNo == 3:
                for o in outputs:
                    loss = loss + self.criterion(o, masks)
                y_preds = outputs[-1]
            # print("val_loss\n",loss.data)
            val_losses.append(loss.data)
            predicted_mask = y_preds > best_iou_threshold
            val_acc = iou_pytorch(predicted_mask.byte(), masks.squeeze(1).byte())
            val_accuracies.append(val_acc.mean())

            self.writer.set_step((epoch - 1) * len(self.valid_data_loader) + batch_idx, 'valid')
            self.valid_metrics.update('loss', loss.item())
            for met in self.metric_ftns:
                self.valid_metrics.update(met.__name__, met(predicted_mask, masks))
            self.writer.add_image('input', make_grid(data.cpu(), nrow=8, normalize=True))

        # add histogram of model parameters to the tensorboard
        for name, p in self.model.named_parameters():
            self.writer.add_histogram(name, p, bins='auto')
        return self.valid_metrics.result(),torch.mean(torch.stack(val_losses))