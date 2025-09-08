import math

import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
from .opencv_backend_visualizer import OpencvBackendVisualizer


class PoseVisualizer(OpencvBackendVisualizer):


    def __init__(self,
                 name: str = 'visualizer',
                 image: Optional[np.ndarray] = None,
                 vis_backends: Optional[Dict] = None,
                 save_dir: Optional[str] = None,
                 bbox_color: Optional[Union[str, Tuple[int]]] = 'green',
                 kpt_color: Optional[Union[str, Tuple[Tuple[int]]]] = 'red',
                 link_color: Optional[Union[str, Tuple[Tuple[int]]]] = None,
                 text_color: Optional[Union[str,
                                            Tuple[int]]] = (255, 255, 255),
                 skeleton: Optional[Union[List, Tuple]] = None,
                 line_width: Union[int, float] = 1,
                 radius: Union[int, float] = 3,
                 show_keypoint_weight: bool = False,
                 backend: str = 'opencv',
                 alpha: float = 1.0):


        super().__init__(
            name=name,
            image=image,
            vis_backends=vis_backends,
            save_dir=save_dir,
            backend=backend)

        self.bbox_color = bbox_color
        self.kpt_color = kpt_color
        self.link_color = link_color
        self.line_width = line_width
        self.text_color = text_color
        self.skeleton = skeleton
        self.radius = radius
        self.alpha = alpha
        self.show_keypoint_weight = show_keypoint_weight
        self.dataset_meta = {}

    def _draw_instances_kpts_openpose(self,
                                      image: np.ndarray,
                                      keypoints,
                                      kpt_thr: float = 0.3):

        self.set_image(image)
        img_h, img_w, _ = image.shape

        keypoints_visible = np.ones(keypoints.shape[:-1])

        keypoints_info = np.concatenate(
        (keypoints, keypoints_visible[..., None]), axis=-1)

        # compute neck joint
        neck = np.mean(keypoints_info[:, [5, 6]], axis=1)
        # neck score when visualizing pred
        neck[:, 2:3] = np.logical_and(
            keypoints_info[:, 5, 2:3] > kpt_thr,
            keypoints_info[:, 6, 2:3] > kpt_thr).astype(int)
        new_keypoints_info = np.insert(keypoints_info, 17, neck, axis=1)

        mmpose_idx = [17, 6, 8, 10, 7, 9, 12, 14, 16, 13, 15, 2, 1, 4, 3]
        openpose_idx = [1, 2, 3, 4, 6, 7, 8, 9, 10, 12, 13, 14, 15, 16, 17]
        new_keypoints_info[:, openpose_idx] = \
            new_keypoints_info[:, mmpose_idx]
        keypoints_info = new_keypoints_info

        keypoints, keypoints_visible = keypoints_info[
            ..., :2], keypoints_info[..., 2]

        for kpts, visible in zip(keypoints, keypoints_visible):
            kpts = np.array(kpts, copy=False)

            if self.kpt_color is None or isinstance(self.kpt_color, str):
                kpt_color = [self.kpt_color] * len(kpts)
            elif len(self.kpt_color) == len(kpts):
                kpt_color = self.kpt_color
            else:
                raise ValueError(
                    f'the length of kpt_color '
                    f'({len(self.kpt_color)}) does not matches '
                    f'that of keypoints ({len(kpts)})')

            # draw links
            if self.skeleton is not None and self.link_color is not None:
                if self.link_color is None or isinstance(
                        self.link_color, str):
                    link_color = [self.link_color] * len(self.skeleton)
                elif len(self.link_color) == len(self.skeleton):
                    link_color = self.link_color
                else:
                    raise ValueError(
                        f'the length of link_color '
                        f'({len(self.link_color)}) does not matches '
                        f'that of skeleton ({len(self.skeleton)})')

                for sk_id, sk in enumerate(self.skeleton):
                    pos1 = (int(kpts[sk[0], 0]), int(kpts[sk[0], 1]))
                    pos2 = (int(kpts[sk[1], 0]), int(kpts[sk[1], 1]))

                    if (pos1[0] <= 0 or pos1[0] >= img_w or pos1[1] <= 0
                            or pos1[1] >= img_h or pos2[0] <= 0
                            or pos2[0] >= img_w or pos2[1] <= 0
                            or pos2[1] >= img_h or visible[sk[0]] < kpt_thr
                            or visible[sk[1]] < kpt_thr
                            or link_color[sk_id] is None):
                        # skip the link that should not be drawn
                        continue

                    X = np.array((pos1[0], pos2[0]))
                    Y = np.array((pos1[1], pos2[1]))
                    color = link_color[sk_id]
                    if not isinstance(color, str):
                        color = tuple(int(c) for c in color)
                    transparency = self.alpha
                    if self.show_keypoint_weight:
                        transparency *= max(
                            0,
                            min(1,
                                0.5 * (visible[sk[0]] + visible[sk[1]])))

                    if sk_id <= 16:
                        # body part
                        mX = np.mean(X)
                        mY = np.mean(Y)
                        length = ((Y[0] - Y[1])**2 + (X[0] - X[1])**2)**0.5
                        transparency = 0.6
                        angle = math.degrees(
                            math.atan2(Y[0] - Y[1], X[0] - X[1]))
                        polygons = cv2.ellipse2Poly(
                            (int(mX), int(mY)),
                            (int(length / 2), int(self.line_width)),
                            int(angle), 0, 360, 1)

                        self.draw_polygons(
                            polygons,
                            edge_colors=color,
                            face_colors=color,
                            alpha=transparency)

                    else:
                        # hand part
                        self.draw_lines(X, Y, color, line_widths=2)

            # draw each point on image
            for kid, kpt in enumerate(kpts):
                if visible[kid] < kpt_thr or kpt_color[
                        kid] is None:
                    # or kpt_color[kid].sum() == 0:
                    # skip the point that should not be drawn
                    continue

                color = kpt_color[kid]
                if not isinstance(color, str):
                    color = tuple(int(c) for c in color)
                transparency = self.alpha
                if self.show_keypoint_weight:
                    transparency *= max(0, min(1, visible[kid]))

                # draw smaller dots for face & hand keypoints
                radius = self.radius // 2 if kid > 17 else self.radius

                self.draw_circles(
                    kpt,
                    radius=np.array([radius]),
                    face_colors=color,
                    edge_colors=color,
                    alpha=transparency,
                    line_widths=radius)

        return self.get_image()