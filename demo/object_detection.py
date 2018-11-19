"""
Copyright 2018 Lambda Labs. All Rights Reserved.
Licensed under
==========================================================================

python demo/object_detection.py \
--mode=train \
--model_dir=~/demo/model/rpn_mscoco \
--network=rpn \
--augmenter=rpn_augmenter \
--batch_size_per_gpu=1 --epochs=1 \
--dataset_dir=/mnt/data/data/mscoco \
--num_classes=81 --resolution=512 \
train_args \
--learning_rate=0.5 --optimizer=momentum \
--piecewise_boundaries=50,75,90 \
--piecewise_lr_decay=1.0,0.1,0.01,0.001 \
--dataset_meta=valminusminival2014
"""
import sys
import os
import argparse
import importlib

def main():

  sys.path.append('.')

  from source.tool import downloader
  from source.tool import tuner
  from source.tool import config_parser

  from source.config.object_detection_config import \
      ObjectDetectionInputterConfig, \
      ObjectDetectionModelerConfig

  parser = config_parser.default_parser()

  parser.add_argument("--num_classes",
                      help="Number of classes.",
                      type=int,
                      default=81)
  parser.add_argument("--resolution",
                      help="Image resolution used for detectoin.",
                      type=int,
                      default=512) 
  parser.add_argument("--dataset_dir",
                      help="Path to dataset.",
                      type=str,
                      default="/mnt/data/data/mscoco")
  parser.add_argument("--feature_net",
                      help="Name of feature net",
                      default="vgg_19_ssd512")
  parser.add_argument("--feature_net_path",
                      help="Path to pre-trained vgg model.",
                      default=os.path.join(
                        os.environ['HOME'],
                        "demo/model/vgg_19_2016_08_28/vgg_19.ckpt"))
  parser.add_argument("--data_format",
                      help="channels_first or channels_last",
                      choices=["channels_first", "channels_last"],
                      default="channels_last")  
  config = parser.parse_args()

  config = config_parser.prepare(config)

  # Generate config
  runner_config, callback_config, inputter_config, modeler_config = \
      config_parser.default_config(config)

  inputter_config = ObjectDetectionInputterConfig(
    inputter_config,
    dataset_dir=config.dataset_dir,
    num_classes=config.num_classes,
    resolution=config.resolution)

  modeler_config = ObjectDetectionModelerConfig(
    modeler_config,
    num_classes=config.num_classes,
    data_format=config.data_format,
    feature_net=config.feature_net,
    feature_net_path=config.feature_net_path)

  if config.mode == "tune":
    pass
  else:
    """
    An application owns a runner.
    Runner: Distributes a job across devices, schedules the excution.
            It owns an inputter and a modeler.
    Inputter: Handles the data pipeline.
              It (optionally) owns a data augmenter.
    Modeler: Creates functions for network, loss, optimization and evaluation.
             It owns a network and a list of callbacks as inputs.
    """
    augmenter = (None if not config.augmenter else
                 importlib.import_module(
                  "source.augmenter." + config.augmenter))

    net = getattr(importlib.import_module(
      "source.network." + config.network), "net")

    callbacks = []
    
    for name in config.callbacks:
      callback = importlib.import_module(
        "source.callback." + name).build(callback_config)
      callbacks.append(callback)

    inputter = importlib.import_module(
      "source.inputter.object_detection_mscoco_inputter").build(
      inputter_config, augmenter)

    modeler = importlib.import_module(
      "source.modeler.object_detection_modeler").build(
      modeler_config, net)

    runner = importlib.import_module(
      "source.runner.parameter_server_runner").build(
      runner_config, inputter, modeler, callbacks)

    # Run application
    runner.dev()

if __name__ == "__main__":
  main()