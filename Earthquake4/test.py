import argparse
import torch
from tqdm import tqdm
import data_loader.dataloader3 as module_data
import model.loss as module_loss
import model.metric as module_metric
import model.model as module_arch
from parse_config import ConfigParser
from functions import *
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
splitsize=96
import matplotlib; matplotlib.use('TkAgg')



def main(config):
    logger = config.get_logger('test')

    # setup data_loader instances
    data_loader = getattr(module_data, config['data_loader']['type'])(
        config['data_loader']['args']['seismic_path'],
        config['data_loader']['args']['label_path'],
        batch_size=config['data_loader2']['args']['batch_size'],
        val_number_of_pictures=config['data_loader2']['args']['val_number_of_pictures'],
        val_start=config['data_loader2']['args']['val_start']

    )
    data_loader = data_loader.val_loader
    modelNo = config['trainer']['modelNo']
    bceloss = nn.BCELoss()
    val_losses = []
    val_accuracies = []
    imageNo = -1
    best_iou_threshold = 0.5
    # build model architecture
    model = config.init_obj('arch', module_arch)
    # logger.info(model)
    print(config['arch']['type'])
    print("start:",config['data_loader2']['args']['val_start'])
    print("number_of_pictures:",config['data_loader2']['args']['val_number_of_pictures'])

    # get function handles of loss and metrics
    loss_fn = getattr(module_loss, config['loss'])
    metric_fns = [getattr(module_metric, met) for met in config['metrics']]

    logger.info('Loading checkpoint: {} ...'.format(config.resume))
    checkpoint = torch.load(config.resume)
    state_dict = checkpoint['state_dict']
    if config['n_gpu'] > 1:
        model = torch.nn.DataParallel(model)
    model.load_state_dict(state_dict)

    # prepare model for testing
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = model.to(device)
    model.eval()

    total_loss = 0.0
    total_metrics = torch.zeros(len(metric_fns))

    with torch.no_grad():
        for i, (data, target) in enumerate(tqdm(data_loader)):
            data, target = data.to(device), target.to(device)
            output = model(data)
            outputs=output
            images=data
            masks=target
            #
            # save sample images, or do something with output here
            #
            # computing loss, metrics on test set
            loss = torch.zeros(1).to(device)
            y_preds = outputs
            if modelNo == 0 or modelNo == 1:
                #             print("bceloss")

                loss = loss_fn(outputs, masks)
            #             loss = cross_entropy_loss_HED(outputs, masks)
            #             loss = nn.BCEWithLogitsLoss(outputs, masks)
            elif modelNo == 2:
                for o in range(5):
                    loss = loss + loss_fn(outputs[o], masks)
                loss = loss + bceloss(outputs[-1], masks)
                y_preds = outputs[-1]
            elif modelNo == 3:
                for o in outputs:
                    loss = loss + loss_fn(o, masks)
                y_preds = outputs[-1]
            # print("val_loss\n",loss.data)
            val_losses.append(loss.data)
            predicted_mask = y_preds > best_iou_threshold
            val_acc = iou_pytorch(predicted_mask.byte(), masks.squeeze(1).byte())
            val_accuracies.append(val_acc.mean())

            batch_size = data.shape[0]
            total_loss += loss.item() * batch_size
            for i, metric in enumerate(metric_fns):
                total_metrics[i] += metric(predicted_mask, masks) * batch_size

        n_samples = len(data_loader.sampler)
        log = {'loss': total_loss / n_samples}
        log.update({
            met.__name__: total_metrics[i].item() / n_samples for i, met in enumerate(metric_fns)
        })
        logger.info(log)

if __name__ == '__main__':
    args = argparse.ArgumentParser(description='PyTorch Template')
    args.add_argument('-c', '--config', default='config1.json', type=str,
                      help='config file path (default: None)')
    args.add_argument('-r', '--resume', default='saved/models/DeepLab/0307_130554/model_best.pth', type=str,
                      help='path to latest checkpoint (default: None)')
    args.add_argument('-d', '--device', default=None, type=str,
                      help='indices of GPUs to enable (default: all)')

    config = ConfigParser.from_args(args)
    main(config)
