#!/usr/bin/python3
# coding=utf-8
import os, json
import numpy as np
import cv2
import sys
from random import shuffle, choice
import tensorflow as tf
from functools import partial
import anchor, box_utils

def set_id_to_label(label_set):
    id_to_label = {}
    for idx, label in enumerate(label_set):
        id_to_label[idx+1] = label
    return id_to_label

class Dataset():
    def __init__(self, config, COCO):
        self.config = config
        self.COCO = COCO
        self.image_dir = config['image_dir']
        self.id_to_label = set_id_to_label(config['label_set'])
        self.input_shape = tuple(config['input_shape'])
        self.default_boxes = anchor.generate_default_boxes(config["anchor_param"])
        self.annotation_path = os.path.join(config['annotation_dir'], 'GDUT_HWD.json')


    def __len__(self):
        return len(self.ids)

    def _get_image(self, image_id, coco):
        image_info = coco.loadImgs(image_id)[0]
        filename = image_info['file_name']
        source = image_info['source']
        original_size = (int(image_info['height']), int(image_info['width']))
        image_path = os.path.join(self.image_dir, filename)
        image = cv2.imread(image_path)
        if image is None:
            filename = os.path.splitext(filename)[0] + '.JPG'
            image_path = self.path_finder.find_path(source, filename)
            image = cv2.imread(image_path)
            if image is None:
                raise FileNotFoundError("Can't not find correct filepath", filename)
            print(filename)
        image = image[:,:,::-1]

        return filename, image, original_size

    def _get_annotation(self, image_id, coco):
        ann_ids = coco.getAnnIds(imgIds=image_id, catIds=self.cat_ids, iscrowd=None)
        boxes = []
        for ann_id in ann_ids:
            x, y, w, h = coco.loadAnns(ann_id)[0]['bbox']
            xmin = x
            ymin = y
            xmax = (x+w)
            ymax = (y+h)
            box = [xmin, ymin, xmax, ymax]
            boxes.append(box)
        labels = [ self.annoID_to_modelID[coco.loadAnns(ann_id)[0]['category_id']] for ann_id in ann_ids]
        return boxes, labels

    def generate(self, split, coco, ids, num_examples, config):
        """
            num_examples : The number of examples to be used.
            It's used if you want to make model overfit a few examples
        """
        for image_id in ids:
            filename, image, original_size = self._get_image(image_id, coco)
            boxes, labels = self._get_annotation(image_id, coco)
            if len(labels) == 0:
                continue
            #assert image.shape[:2] == original_size[:2]
            height, width = original_size

            #normalize bounding box coord (range in 0~1.0)
            boxes = list(map(lambda box : (box[0]/width, box[1]/height, box[2]/width, box[3]/height), boxes))
            boxes = np.array(boxes, np.float32); labels = np.array(labels, np.float32);
            gt_confs, gt_locs = box_utils.compute_target(self.default_boxes, boxes, labels)
            image = cv2.resize(image, self.input_shape[:2], interpolation = cv2.INTER_AREA)

            if (config['inference_mode'] == 'mAP'):
                yield filename, image, labels, boxes
            else:
                yield filename, image, gt_confs, gt_locs

    def load_data_generator(self, split, config):
        """
            num_examples : The number of examples to be used.
            It's used if you want to make model overfit a few examples
        """
        batch_size = self.config[split]['batch_size']
        num_examples = self.config[split]['num_examples']
        coco = self.COCO(self.annotation_path)
        ids = coco.getImgIds()
        if num_examples>0:
            ids =ids[:num_examples]
        if split == 'train':
            shuffle(ids)
            if len(ids) > 1000:
                shuffle_buffer = 1000
            else:
                shuffle_buffer = len(ids)

        # Sometimes, we use some categories instead of using every category.
        # Then category id of annotation is different from category id of model.
        # The dict "annoID_to_model_ID" converts category id to model id.
        self.cat_ids = coco.getCatIds(self.id_to_label.values())
        self.annoID_to_modelID = {}
        for model_id, cat_id in enumerate(self.cat_ids):
            self.annoID_to_modelID[cat_id] = model_id+1

        # pre-argumenting self.generate function.
        gen = partial(self.generate, split, coco, ids, num_examples, config)
        # generate data pipeline with from_generator in TensorFlow dataset APIs
        dataset = tf.data.Dataset.from_generator(gen,
            (tf.string, tf.float32, tf.int32, tf.float32))

        if (split == "train") & (config['inference_mode'] != 'mAP'):
            dataset = dataset.shuffle(shuffle_buffer)

        return dataset.batch(batch_size).prefetch(tf.data.experimental.AUTOTUNE), len(ids)
