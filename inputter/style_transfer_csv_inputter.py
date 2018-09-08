"""
Copyright 2018 Lambda Labs. All Rights Reserved.
Licensed under
==========================================================================

"""
from __future__ import print_function
import os
import csv
import importlib

import tensorflow as tf

from inputter import Inputter
from augmenter.external import vgg_preprocessing


class StyleTransferCSVInputter(Inputter):
  def __init__(self, args):
    super(StyleTransferCSVInputter, self).__init__(args)
    self.augmenter = importlib.import_module("augmenter." + args.augmenter)
    self.num_samples = -1

    if self.args.mode == "infer":
      self.test_samples = [os.path.expanduser(x) for x
                           in self.args.test_samples.split(",")]

  def create_nonreplicated_fn(self):
    batch_size = (self.args.batch_size_per_gpu *
                  self.args.num_gpu)
    max_step = (self.get_num_samples() * self.args.epochs // batch_size)
    tf.constant(max_step, name="max_step")

  def get_num_samples(self):
    if self.num_samples < 0:
      if self.args.mode == "infer":
        self.num_samples = len(self.test_samples)
      else:
        with open(self.args.dataset_csv) as f:
          parsed = csv.reader(f, delimiter=",", quotechar="'")
          self.num_samples = len(list(parsed))
    return self.num_samples

  def get_samples_fn(self):
    if self.args.mode == "infer":
      images_path = self.test_samples
    elif self.args.mode == "train" or \
            self.args.mode == "eval":
      assert os.path.exists(self.args.dataset_csv), (
        "Cannot find dataset_csv file {}.".format(self.args.dataset_csv))

      images_path = []
      dirname = os.path.dirname(self.args.dataset_csv)
      with open(self.args.dataset_csv) as f:
        parsed = csv.reader(f, delimiter=",", quotechar="'")
        for row in parsed:
          images_path.append(os.path.join(dirname, row[0]))
    return (images_path,)

  def parse_fn(self, image_path):
    """Parse a single input sample
    """
    image = tf.read_file(image_path)
    image = tf.image.decode_png(image, channels=self.args.image_depth)
    image = tf.image.convert_image_dtype(image, dtype=tf.float32)

    if self.args.mode == "infer":
      image = vgg_preprocessing._mean_image_subtraction(
        image * 255.0)
    else:
      is_training = (self.args.mode == "train")
      image = self.augmenter.augment(image,
                                     self.args.image_height,
                                     self.args.image_width,
                                     self.args.resize_side_min,
                                     self.args.resize_side_max,
                                     is_training=is_training)
    return (image,)

  def input_fn(self, test_samples=[]):
    batch_size = (self.args.batch_size_per_gpu *
                  self.args.num_gpu)
    max_step = (self.get_num_samples() * self.args.epochs // batch_size)

    samples = self.get_samples_fn()

    dataset = tf.data.Dataset.from_tensor_slices(samples)

    if self.args.mode == "train":
      dataset = dataset.shuffle(self.args.shuffle_buffer_size)

    dataset = dataset.repeat(self.args.epochs)

    dataset = dataset.map(
      lambda image: self.parse_fn(image),
      num_parallel_calls=4)

    dataset = dataset.apply(
        tf.contrib.data.batch_and_drop_remainder(batch_size))

    dataset = dataset.take(max_step)

    dataset = dataset.prefetch(2)

    iterator = dataset.make_one_shot_iterator()
    return iterator.get_next()


def build(args):
  return StyleTransferCSVInputter(args)