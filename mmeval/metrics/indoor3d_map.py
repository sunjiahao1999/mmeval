# Copyright (c) OpenMMLab. All rights reserved.
import numpy as np
import torch
from numpy import ndarray
from rich.console import Console
from rich.table import Table
from rich.box import MARKDOWN
from typing import Dict, List, Sequence, Tuple, Union

from mmeval.core.base_metric import BaseMetric


class Indoor3DMeanAP(BaseMetric):
    """Evaluate AR, AP, and mAP for 3D indoor object detection task.

    Args:
        iou_thr (float | List[float]): Iou_threshold for evaluation.
        **kwargs: Keyword parameters passed to :class:`BaseMetric`.

    Examples:
        >>> from mmeval import Indoor3DMeanAP
        >>> from mmdet3d.structures import DepthInstance3DBoxes
        >>> indoor_metric = Indoor3DMeanAP()
        >>> gt_dict = {
        ...     'gt_bboxes_3d':
        ...     DepthInstance3DBoxes(
        ...         torch.tensor([
        ...         [2.3578, 1.7841, -0.0987, 0.5532, 0.4948, 0.6474, 0.0000],
        ...         [-0.2773, -2.1403, 0.0615, 0.4786, 0.5170, 0.3842, 0.0000],
        ...         [0.0259, -2.7954, -0.0157, 0.3869, 0.4361, 0.5229, 0.0000],
        ...         [-2.3968, 1.1040, 0.0945, 2.5563, 1.5989, 0.9322, 0.0000],
        ...         [-0.3173, -2.7770, 0.0134, 0.5473, 0.8569, 0.5577, 0.0000],
        ...         [-2.4882, -1.4437, 0.0987, 1.2199, 0.4859, 0.6461, 0.0000],
        ...         [-3.4702, -0.1315, 0.2463, 1.3137, 0.8022, 0.4765, 0.0000],
        ...         [1.9786, 3.0196, -0.0934, 1.6129, 0.5834, 1.4662, 0.0000],
        ...         [2.3835, 2.2691, -0.1376, 0.5197, 0.5099, 0.6896, 0.0000],
        ...         [2.5986, -0.5313, 1.4269, 0.0696, 0.2933, 0.3104, 0.0000],
        ...         [0.4555, -3.1278, -0.0637, 2.0247, 0.1292, 0.2419, 0.0000],
        ...         [0.4655, -3.1941, 0.3769, 2.1132, 0.3536, 1.9803, 0.0000]
        ...          ])),
        ...     'gt_labels_3d':
        ...         np.array([2, 2, 2, 3, 4, 17, 4, 7, 2, 8, 17, 11])
        ... }
        >>> pred_dict = dict()
        >>> pred_dict['scores_3d'] = np.ones(len(gt_dict['gt_bboxes_3d']))
        >>> pred_dict['bboxes_3d'] = gt_dict['gt_bboxes_3d']
        >>> pred_dict['labels_3d'] = gt_dict['gt_labels_3d']
        >>> indoor_metric.dataset_meta = {
        ...     'classes': ('cabinet', 'bed', 'chair', 'sofa', 'table', 'door',
        ...                 'window', 'bookshelf', 'picture', 'counter',
        ...                'desk', 'curtain', 'refrigerator', 'showercurtrain',
        ...                 'toilet','sink', 'bathtub', 'garbagebin'),
        ...     'box_type_3d':
        ...     'Depth',
        ... }
        >>> eval_results = indoor_metric([pred_dict], [gt_dict])
    """

    def __init__(self,
                 iou_thr: Union[Sequence[float], float] = [0.25, 0.5],
                 **kwargs) -> None:
        super().__init__(**kwargs)
        self.iou_thr = [iou_thr] if isinstance(iou_thr, float) else iou_thr

    def add(self, predictions: Sequence[Dict], groundtruths: Sequence[Dict]) -> None:  # type: ignore # yapf: disable # noqa: E501
        """Add the intermediate results to `self._results`.

        Args:
            predictions (Sequence[dict]): A sequence of dict. Each dict
                representing a detection result for a sample, with the
                following keys:

                - bboxes_3d (numpy.ndarray): Shape (N, 7), the predicted
                  3D bounding bboxes of this sample, in 'x, y, z, x_size,
                  y_size, z_size, yaw' foramrt.
                - scores_3d (numpy.ndarray): Shape (N, ), the predicted scores
                  of 3D bounding boxes.
                - labels_3d (numpy.ndarray): Shape (N, ), the predicted labels
                  of 3D bounding boxes.

            groundtruths (Sequence[dict]): A sequence of dict. Each dict
                represents a groundtruths for a sample, with the following
                keys:

                - gt_bboxes_3d (numpy.ndarray): Shape (K, 4), the ground truth
                  bounding bboxes of this sample_ids, in 'x, y, z, x_size,
                  y_size, z_size, yaw' foramrt.
                - gt_labels_3d (numpy.ndarray): Shape (K, ), the ground truth
                  labels of bounding boxes.
        """
        for prediction, groundtruth in zip(predictions, groundtruths):
            assert isinstance(prediction, dict), 'The prediciton should be a' \
                f'sequence of dict, but got a sequence of {type(prediction)}.'
            assert isinstance(groundtruth, dict), 'The label should be a' \
                f'sequence of dict, but got a sequence of {type(groundtruth)}.'
            self._results.append((prediction, groundtruth))

    def compute_metric(self, results: Sequence) -> dict:
        """Compute the Indoor 3D meanAP.

        Args:
            results (List[tuple]): A list of tuple. Each tuple is the
                prediction and ground truth of a sample. This list has already
                been synced across all ranks.

        Returns:
            dict: The computed metric.
            The keys are the names of the metrics, and the values are
            corresponding results.
        """
        preds, gts = zip(*results)
        label2cat = self.dataset_meta['classes']  # type: ignore

        assert len(preds) == len(gts)
        preds_per_class = {}  # type: ignore
        gts_per_class = {}  # type: ignore
        for sample_id in range(len(preds)):
            # parse preds
            pred = preds[sample_id]
            for i in range(len(pred['labels_3d'])):
                label = pred['labels_3d'][i]
                bbox = pred['bboxes_3d'][i]
                score = pred['scores_3d'][i]
                if label not in preds_per_class:
                    preds_per_class[int(label)] = {}
                if sample_id not in preds_per_class[label]:
                    preds_per_class[int(label)][sample_id] = []
                if label not in gts_per_class:
                    gts_per_class[int(label)] = {}
                if sample_id not in gts_per_class[label]:
                    gts_per_class[int(label)][sample_id] = []
                preds_per_class[int(label)][sample_id].append((bbox, score))

            # parse gts
            gt = gts[sample_id]
            gt_boxes = gt['gt_bboxes_3d']
            labels_3d = gt['gt_labels_3d']
            for i in range(len(labels_3d)):
                label = labels_3d[i]
                bbox = gt_boxes[i]
                if label not in gts_per_class:
                    gts_per_class[label] = {}
                if sample_id not in gts_per_class[label]:
                    gts_per_class[label][sample_id] = []
                gts_per_class[label][sample_id].append(bbox)

        rec, prec, ap = self.eval_map_recall(preds_per_class, gts_per_class,
                                             self.iou_thr)

        eval_results = dict()
        header = ['classes']
        table_columns = [[label2cat[label]
                          for label in ap[0].keys()] + ['Overall']]
        for i, iou_thresh in enumerate(self.iou_thr):
            header.append(f'AP_{iou_thresh:.2f}')
            header.append(f'AR_{iou_thresh:.2f}')
            rec_list = []
            eval_results[f'AP_{iou_thresh:.2f}'] = float(
                np.mean(list(ap[i].values())))

            table_columns.append(list(map(float, list(ap[i].values()))))
            table_columns[-1] += [eval_results[f'AP_{iou_thresh:.2f}']]
            table_columns[-1] = [f'{x:.4f}' for x in table_columns[-1]]

            for label in rec[i].keys():
                rec_list.append(rec[i][label][-1])
            eval_results[f'AR_{iou_thresh:.2f}'] = float(np.mean(rec_list))

            table_columns.append(list(map(float, rec_list)))
            table_columns[-1] += [eval_results[f'AR_{iou_thresh:.2f}']]
            table_columns[-1] = [f'{x:.4f}' for x in table_columns[-1]]

        console = Console(color_system=None)
        table = Table(*header)
        for i, table_rows in enumerate(list(zip(*table_columns))):
            if i == len(table_columns[0]) - 1:
                table.add_section()
            table.add_row(*table_rows)
        with console.capture() as capture:
            console.print(table, end='')
        self.logger.info('\n' + capture.get())

        return eval_results

    def eval_map_recall(self, pred: dict, gt: dict,
                        ovthresh: Sequence[float]) -> Tuple:
        """Evaluate mAP and recall. Generic functions to compute
        precision/recall for 3D object detection for multiple classes.

        Args:
            pred (dict): Information of detection results,
                which maps class_id and predictions.
            gt (dict): Information of ground truths, which maps class_id and
                ground truths.
            ovthresh (List[float]): iou threshold. Default: None.

        Return:
            tuple[dict]: dict results of recall, AP, and precision for
                all classes.
        """

        ret_values = {}
        for classname in gt.keys():
            if classname in pred:
                ret_values[classname] = self._eval_map_recall_single(
                    pred[classname], gt[classname], ovthresh)
        recall = [{} for _ in ovthresh]  # type: ignore
        precision = [{} for _ in ovthresh]  # type: ignore
        ap = [{} for _ in ovthresh]  # type: ignore

        for label in gt.keys():
            for iou_idx in range(len(ovthresh)):
                if label in pred:
                    recall[iou_idx][label], precision[iou_idx][label], ap[
                        iou_idx][label] = ret_values[label][iou_idx]
                else:
                    recall[iou_idx][label] = np.zeros(1)
                    precision[iou_idx][label] = np.zeros(1)
                    ap[iou_idx][label] = np.zeros(1)

        return recall, precision, ap

    def _eval_map_recall_single(self, pred: dict, gt: dict,
                                iou_thr: Sequence[float]) -> List:
        """Generic functions to compute precision/recall for object detection
        for a single class.

        Args:
            pred (dict): Predictions mapping from sample id to bounding boxes
                and scores.
            gt (dict): Ground truths mapping from sample id to bounding boxes.
            iou_thr (list[float]): A list of iou thresholds.

        Return:
            tuple (np.ndarray, np.ndarray, float): Recalls, precisions and
                average precision.
        """

        class_recs = {}
        npos = 0
        for sample_id in gt.keys():
            cur_gt_num = len(gt[sample_id])
            if cur_gt_num != 0:
                gt_cur = torch.zeros([cur_gt_num, 7], dtype=torch.float32)
                for i in range(cur_gt_num):
                    gt_cur[i] = gt[sample_id][i].tensor
                bbox = gt[sample_id][0].new_box(gt_cur)
            else:
                bbox = gt[sample_id]
            det = [[False] * len(bbox) for i in iou_thr]
            npos += len(bbox)
            class_recs[sample_id] = {'bbox': bbox, 'det': det}

        sample_ids = []
        confidence = []
        ious = []
        for sample_id in pred.keys():
            cur_num = len(pred[sample_id])
            if cur_num == 0:
                continue
            pred_cur = torch.zeros((cur_num, 7), dtype=torch.float32)
            box_idx = 0
            for box, score in pred[sample_id]:
                sample_ids.append(sample_id)
                confidence.append(score)
                pred_cur[box_idx] = box.tensor
                box_idx += 1
            pred_cur = box.new_box(pred_cur)
            gt_cur = class_recs[sample_id]['bbox']
            if len(gt_cur) > 0:
                # calculate iou in each sample
                iou_cur = pred_cur.overlaps(pred_cur, gt_cur)
                for i in range(cur_num):
                    ious.append(iou_cur[i])
            else:
                for i in range(cur_num):
                    ious.append(np.zeros(1))

        confidence = np.array(confidence)

        # sort by confidence
        sorted_ind = np.argsort(-confidence)
        sample_ids = [sample_ids[x] for x in sorted_ind]
        ious = [ious[x] for x in sorted_ind]

        # go down dets and mark TPs and FPs
        tp_thr = [np.zeros(len(sample_ids)) for _ in iou_thr]
        fp_thr = [np.zeros(len(sample_ids)) for _ in iou_thr]
        for i in range(len(sample_ids)):
            R = class_recs[sample_ids[i]]
            iou_max = -np.inf
            BBGT = R['bbox']
            cur_iou = ious[i]

            if len(BBGT) > 0:
                # compute overlaps
                for j in range(len(BBGT)):
                    # iou = get_iou_main(get_iou_func, (bb, BBGT[j,...]))
                    iou = cur_iou[j]
                    if iou > iou_max:
                        iou_max = iou
                        jmax = j

            for iou_idx, thresh in enumerate(iou_thr):
                if iou_max > thresh:
                    if not R['det'][iou_idx][jmax]:
                        tp_thr[iou_idx][i] = 1.
                        R['det'][iou_idx][jmax] = 1
                    else:
                        fp_thr[iou_idx][i] = 1.
                else:
                    fp_thr[iou_idx][i] = 1.

        ret = []
        for iou_idx, thresh in enumerate(iou_thr):
            # compute precision recall
            fp = np.cumsum(fp_thr[iou_idx])
            tp = np.cumsum(tp_thr[iou_idx])
            recall = tp / float(npos)
            # avoid divide by zero in case the first detection matches
            # a difficult ground truth
            precision = tp / np.maximum(tp + fp, np.finfo(np.float64).eps)
            ap = self.average_precision(recall, precision)
            ret.append((recall, precision, ap))

        return ret

    def average_precision(self,
                          recalls: ndarray,
                          precisions: ndarray,
                          mode='area') -> ndarray:
        """Calculate average precision (for single or multiple scales).

        Args:
            recalls (np.ndarray): Recalls with shape of (num_scales, num_dets)
                or (num_dets, ).
            precisions (np.ndarray): Precisions with shape of
                (num_scales, num_dets) or (num_dets, ).
            mode (str): 'area' or '11points', 'area' means calculating the area
                under precision-recall curve, '11points' means calculating
                the average precision of recalls at [0, 0.1, ..., 1]

        Returns:
            np.ndarray: Calculated average precision.
        """
        if recalls.ndim == 1:
            recalls = recalls[np.newaxis, :]
            precisions = precisions[np.newaxis, :]

        assert recalls.shape == precisions.shape
        assert recalls.ndim == 2

        num_scales = recalls.shape[0]
        ap = np.zeros(num_scales, dtype=np.float32)
        if mode == 'area':
            zeros = np.zeros((num_scales, 1), dtype=recalls.dtype)
            ones = np.ones((num_scales, 1), dtype=recalls.dtype)
            mrec = np.hstack((zeros, recalls, ones))
            mpre = np.hstack((zeros, precisions, zeros))
            for i in range(mpre.shape[1] - 1, 0, -1):
                mpre[:, i - 1] = np.maximum(mpre[:, i - 1], mpre[:, i])
            for i in range(num_scales):
                ind = np.where(mrec[i, 1:] != mrec[i, :-1])[0]
                ap[i] = np.sum(
                    (mrec[i, ind + 1] - mrec[i, ind]) * mpre[i, ind + 1])
        elif mode == '11points':
            for i in range(num_scales):
                for thr in np.arange(0, 1 + 1e-3, 0.1):
                    precs = precisions[i, recalls[i, :] >= thr]
                    prec = precs.max() if precs.size > 0 else 0
                    ap[i] += prec
                ap /= 11
        else:
            raise ValueError(
                'Unrecognized mode, only "area" and "11points" are supported')
        return ap

    @property
    def classes(self) -> list:
        """Get classes from self.dataset_meta."""
        if hasattr(self, '_classes'):
            return self._classes  # type: ignore

        if self.dataset_meta and 'classes' in self.dataset_meta:
            classes = self.dataset_meta['classes']
        self._classes = classes
        return classes
