# Copyright (c) OpenMMLab. All rights reserved.
from typing import List, Optional, Union, Callable

import cv2
import numpy as np
import torch

from .color import Color, color_val

# a type alias declares the optional types of color argument
ColorType = Union[Color, str, tuple, int, np.ndarray]


def convert_color_factory(src: str, dst: str) -> Callable:
    code = getattr(cv2, f'COLOR_{src.upper()}2{dst.upper()}')

    def convert_color(img: np.ndarray) -> np.ndarray:
        out_img = cv2.cvtColor(img, code)
        return out_img

    convert_color.__doc__ = f"""Convert a {src.upper()} image to {dst.upper()}
        image.
    Args:
        img (ndarray or str): The input image.
    Returns:
        ndarray: The converted {dst.upper()} image.
    """
    return convert_color


bgr2rgb = convert_color_factory('bgr', 'rgb')


class OpencvBackendVisualizer():
    """Base visualizer with opencv backend support.

    Args:
        name (str): Name of the instance. Defaults to 'visualizer'.
        image (np.ndarray, optional): the origin image to draw. The format
            should be RGB. Defaults to None.
        vis_backends (list, optional): Visual backend config list.
            Defaults to None.
        save_dir (str, optional): Save file dir for all storage backends.
            If it is None, the backend storage will not save any data.
        fig_save_cfg (dict): Keyword parameters of figure for saving.
            Defaults to empty dict.
        fig_show_cfg (dict): Keyword parameters of figure for showing.
            Defaults to empty dict.
        backend (str): Backend used to draw elements on the image and display
            the image. Defaults to 'matplotlib'.
        alpha (int, float): The transparency of bboxes. Defaults to ``1.0``
    """

    def __init__(self,
                 name='visualizer',
                 backend: str = 'opencv',
                 *args,
                 **kwargs):
        assert backend in ('opencv', 'matplotlib'), f'the argument ' \
                                                    f'\'backend\' must be either \'opencv\' or \'matplotlib\', ' \
                                                    f'but got \'{backend}\'.'
        self.backend = backend

    def set_image(self, image: np.ndarray) -> None:
        """Set the image to draw.

        Args:
            image (np.ndarray): The image to draw.
        """
        assert image is not None
        image = image.astype('uint8')
        self._image = image
        self.width, self.height = image.shape[1], image.shape[0]
        self._default_font_size = max(
            np.sqrt(self.height * self.width) // 90, 10)

    def get_image(self) -> np.ndarray:
        """Get the drawn image. The format is RGB.

        Returns:
            np.ndarray: the drawn image which channel is RGB.
        """
        assert self._image is not None, 'Please set image using `set_image`'
        return self._image

    def draw_circles(self,
                     center: Union[np.ndarray, torch.Tensor],
                     radius: Union[np.ndarray, torch.Tensor],
                     face_colors: Union[str, tuple, List[str],
                     List[tuple]] = 'none',
                     alpha: float = 1.0,
                     **kwargs):
        """Draw single or multiple circles.
        Args:
            center (Union[np.ndarray, torch.Tensor]): The x coordinate of
                each line' start and end points.
            radius (Union[np.ndarray, torch.Tensor]): The y coordinate of
                each line' start and end points.
            edge_colors (Union[str, tuple, List[str], List[tuple]]): The
                colors of circles. ``colors`` can have the same length with
                lines or just single value. If ``colors`` is single value,
                all the lines will have the same colors. Reference to
                https://matplotlib.org/stable/gallery/color/named_colors.html
                for more details. Defaults to 'g.
            line_styles (Union[str, List[str]]): The linestyle
                of lines. ``line_styles`` can have the same length with
                texts or just single value. If ``line_styles`` is single
                value, all the lines will have the same linestyle.
                Reference to
                https://matplotlib.org/stable/api/collections_api.html?highlight=collection#matplotlib.collections.AsteriskPolygonCollection.set_linestyle
                for more details. Defaults to '-'.
            line_widths (Union[Union[int, float], List[Union[int, float]]]):
                The linewidth of lines. ``line_widths`` can have
                the same length with lines or just single value.
                If ``line_widths`` is single value, all the lines will
                have the same linewidth. Defaults to 2.
            face_colors (Union[str, tuple, List[str], List[tuple]]):
                The face colors. Defaults to None.
            alpha (Union[int, float]): The transparency of circles.
                Defaults to 0.8.
        """

        if isinstance(face_colors, str):
            face_colors = color_val(face_colors)[::-1]

        if alpha == 1.0:
            self._image = cv2.circle(self._image,
                                     (int(center[0]), int(center[1])),
                                     int(radius), face_colors, -1)
        else:
            img = cv2.circle(self._image.copy(),
                             (int(center[0]), int(center[1])), int(radius),
                             face_colors, -1)
            self._image = cv2.addWeighted(self._image, 1 - alpha, img,
                                          alpha, 0)

    def draw_texts(
            self,
            texts: Union[str, List[str]],
            positions: Union[np.ndarray, torch.Tensor],
            font_sizes: Optional[Union[int, List[int]]] = None,
            colors: Union[str, tuple, List[str], List[tuple]] = 'g',
            vertical_alignments: Union[str, List[str]] = 'top',
            horizontal_alignments: Union[str, List[str]] = 'left',
            bboxes: Optional[Union[dict, List[dict]]] = None,
            **kwargs,
    ):
        """Draw single or multiple text boxes.

        Args:
            texts (Union[str, List[str]]): Texts to draw.
            positions (Union[np.ndarray, torch.Tensor]): The position to draw
                the texts, which should have the same length with texts and
                each dim contain x and y.
            font_sizes (Union[int, List[int]], optional): The font size of
                texts. ``font_sizes`` can have the same length with texts or
                just single value. If ``font_sizes`` is single value, all the
                texts will have the same font size. Defaults to None.
            colors (Union[str, tuple, List[str], List[tuple]]): The colors
                of texts. ``colors`` can have the same length with texts or
                just single value. If ``colors`` is single value, all the
                texts will have the same colors. Reference to
                https://matplotlib.org/stable/gallery/color/named_colors.html
                for more details. Defaults to 'g.
            vertical_alignments (Union[str, List[str]]): The verticalalignment
                of texts. verticalalignment controls whether the y positional
                argument for the text indicates the bottom, center or top side
                of the text bounding box.
                ``vertical_alignments`` can have the same length with
                texts or just single value. If ``vertical_alignments`` is
                single value, all the texts will have the same
                verticalalignment. verticalalignment can be 'center' or
                'top', 'bottom' or 'baseline'. Defaults to 'top'.
            horizontal_alignments (Union[str, List[str]]): The
                horizontalalignment of texts. Horizontalalignment controls
                whether the x positional argument for the text indicates the
                left, center or right side of the text bounding box.
                ``horizontal_alignments`` can have
                the same length with texts or just single value.
                If ``horizontal_alignments`` is single value, all the texts
                will have the same horizontalalignment. Horizontalalignment
                can be 'center','right' or 'left'. Defaults to 'left'.
            font_families (Union[str, List[str]]): The font family of
                texts. ``font_families`` can have the same length with texts or
                just single value. If ``font_families`` is single value, all
                the texts will have the same font family.
                font_familiy can be 'serif', 'sans-serif', 'cursive', 'fantasy'
                or 'monospace'.  Defaults to 'sans-serif'.
            bboxes (Union[dict, List[dict]], optional): The bounding box of the
                texts. If bboxes is None, there are no bounding box around
                texts. ``bboxes`` can have the same length with texts or
                just single value. If ``bboxes`` is single value, all
                the texts will have the same bbox. Reference to
                https://matplotlib.org/stable/api/_as_gen/matplotlib.patches.FancyBboxPatch.html#matplotlib.patches.FancyBboxPatch
                for more details. Defaults to None.
            font_properties (Union[FontProperties, List[FontProperties]], optional):
                The font properties of texts. FontProperties is
                a ``font_manager.FontProperties()`` object.
                If you want to draw Chinese texts, you need to prepare
                a font file that can show Chinese characters properly.
                For example: `simhei.ttf`, `simsun.ttc`, `simkai.ttf` and so on.
                Then set ``font_properties=matplotlib.font_manager.FontProperties(fname='path/to/font_file')``
                ``font_properties`` can have the same length with texts or
                just single value. If ``font_properties`` is single value,
                all the texts will have the same font properties.
                Defaults to None.
                `New in version 0.6.0.`
        """  # noqa: E501

        font_scale = max(0.1, font_sizes / 30)
        thickness = max(1, font_sizes // 15)

        text_size, text_baseline = cv2.getTextSize(texts,
                                                   cv2.FONT_HERSHEY_DUPLEX,
                                                   font_scale, thickness)

        x = int(positions[0])
        if horizontal_alignments == 'right':
            x = max(0, x - text_size[0])
        elif horizontal_alignments == 'center':
            x = max(0, x - text_size[0] // 2)
        y = int(positions[1])
        if vertical_alignments == 'top':
            y = min(self.height, y + text_size[1])
        elif vertical_alignments == 'center':
            y = min(self.height, y + text_size[1] // 2)

        if bboxes is not None:
            bbox_color = bboxes[0]['facecolor']
            if isinstance(bbox_color, str):
                bbox_color = color_val(bbox_color)[::-1]

            y = y - text_baseline // 2
            self._image = cv2.rectangle(
                self._image, (x, y - text_size[1] - text_baseline // 2),
                (x + text_size[0], y + text_baseline // 2), bbox_color,
                cv2.FILLED)

        self._image = cv2.putText(self._image, texts, (x, y),
                                  cv2.FONT_HERSHEY_SIMPLEX, font_scale,
                                  colors, thickness - 1)

    def draw_bboxes(self,
                    bboxes: Union[np.ndarray, torch.Tensor],
                    edge_colors: Union[str, tuple, List[str],
                    List[tuple]] = 'g',
                    line_widths: Union[Union[int, float],
                    List[Union[int, float]]] = 2,
                    **kwargs):
        """Draw single or multiple bboxes.

        Args:
            bboxes (Union[np.ndarray, torch.Tensor]): The bboxes to draw with
                the format of(x1,y1,x2,y2).
            edge_colors (Union[str, tuple, List[str], List[tuple]]): The
                colors of bboxes. ``colors`` can have the same length with
                lines or just single value. If ``colors`` is single value, all
                the lines will have the same colors. Refer to `matplotlib.
                colors` for full list of formats that are accepted.
                Defaults to 'g'.
            line_styles (Union[str, List[str]]): The linestyle
                of lines. ``line_styles`` can have the same length with
                texts or just single value. If ``line_styles`` is single
                value, all the lines will have the same linestyle.
                Reference to
                https://matplotlib.org/stable/api/collections_api.html?highlight=collection#matplotlib.collections.AsteriskPolygonCollection.set_linestyle
                for more details. Defaults to '-'.
            line_widths (Union[Union[int, float], List[Union[int, float]]]):
                The linewidth of lines. ``line_widths`` can have
                the same length with lines or just single value.
                If ``line_widths`` is single value, all the lines will
                have the same linewidth. Defaults to 2.
            face_colors (Union[str, tuple, List[str], List[tuple]]):
                The face colors. Defaults to None.
            alpha (Union[int, float]): The transparency of bboxes.
                Defaults to 0.8.
        """

        self._image = self.imshow_bboxes(
            self._image,
            bboxes,
            edge_colors,
            top_k=-1,
            thickness=line_widths)

    def draw_lines(self,
                   x_datas: Union[np.ndarray, torch.Tensor],
                   y_datas: Union[np.ndarray, torch.Tensor],
                   colors: Union[str, tuple, List[str], List[tuple]] = 'g',
                   line_widths: Union[Union[int, float],
                   List[Union[int, float]]] = 2,
                   **kwargs):
        """Draw single or multiple line segments.

        Args:
            x_datas (Union[np.ndarray, torch.Tensor]): The x coordinate of
                each line' start and end points.
            y_datas (Union[np.ndarray, torch.Tensor]): The y coordinate of
                each line' start and end points.
            colors (Union[str, tuple, List[str], List[tuple]]): The colors of
                lines. ``colors`` can have the same length with lines or just
                single value. If ``colors`` is single value, all the lines
                will have the same colors. Reference to
                https://matplotlib.org/stable/gallery/color/named_colors.html
                for more details. Defaults to 'g'.
            line_styles (Union[str, List[str]]): The linestyle
                of lines. ``line_styles`` can have the same length with
                texts or just single value. If ``line_styles`` is single
                value, all the lines will have the same linestyle.
                Reference to
                https://matplotlib.org/stable/api/collections_api.html?highlight=collection#matplotlib.collections.AsteriskPolygonCollection.set_linestyle
                for more details. Defaults to '-'.
            line_widths (Union[Union[int, float], List[Union[int, float]]]):
                The linewidth of lines. ``line_widths`` can have
                the same length with lines or just single value.
                If ``line_widths`` is single value, all the lines will
                have the same linewidth. Defaults to 2.
        """

        if isinstance(colors, str):
            colors = color_val(colors)[::-1]
        self._image = cv2.line(
            self._image, (x_datas[0], y_datas[0]),
            (x_datas[1], y_datas[1]),
            colors,
            thickness=line_widths)

    def draw_polygons(self,
                      polygons: Union[Union[np.ndarray, torch.Tensor],
                      List[Union[np.ndarray, torch.Tensor]]],
                      edge_colors: Union[str, tuple, List[str],
                      List[tuple]] = 'g',
                      alpha: float = 1.0,
                      **kwargs):
        """Draw single or multiple bboxes.

        Args:
            polygons (Union[Union[np.ndarray, torch.Tensor],\
                List[Union[np.ndarray, torch.Tensor]]]): The polygons to draw
                with the format of (x1,y1,x2,y2,...,xn,yn).
            edge_colors (Union[str, tuple, List[str], List[tuple]]): The
                colors of polygons. ``colors`` can have the same length with
                lines or just single value. If ``colors`` is single value,
                all the lines will have the same colors. Refer to
                `matplotlib.colors` for full list of formats that are accepted.
                Defaults to 'g.
            line_styles (Union[str, List[str]]): The linestyle
                of lines. ``line_styles`` can have the same length with
                texts or just single value. If ``line_styles`` is single
                value, all the lines will have the same linestyle.
                Reference to
                https://matplotlib.org/stable/api/collections_api.html?highlight=collection#matplotlib.collections.AsteriskPolygonCollection.set_linestyle
                for more details. Defaults to '-'.
            line_widths (Union[Union[int, float], List[Union[int, float]]]):
                The linewidth of lines. ``line_widths`` can have
                the same length with lines or just single value.
                If ``line_widths`` is single value, all the lines will
                have the same linewidth. Defaults to 2.
            face_colors (Union[str, tuple, List[str], List[tuple]]):
                The face colors. Defaults to None.
            alpha (Union[int, float]): The transparency of polygons.
                Defaults to 0.8.
        """


        if alpha == 1.0:
            self._image = cv2.fillConvexPoly(self._image, polygons,
                                             edge_colors)
        else:
            img = cv2.fillConvexPoly(self._image.copy(), polygons,
                                     edge_colors)
            self._image = cv2.addWeighted(self._image, 1 - alpha, img,
                                          alpha, 0)


    def show(self,
             drawn_img: Optional[np.ndarray] = None,
             win_name: str = 'image',
             wait_time: float = 0.,
             continue_key=' ') -> None:
        """Show the drawn image.

        Args:
            drawn_img (np.ndarray, optional): The image to show. If drawn_img
                is None, it will show the image got by Visualizer. Defaults
                to None.
            win_name (str):  The image title. Defaults to 'image'.
            wait_time (float): Delay in seconds. 0 is the special
                value that means "forever". Defaults to 0.
            continue_key (str): The key for users to continue. Defaults to
                the space key.
        """

        # Keep images are shown in the same window, and the title of window
        # will be updated with `win_name`.
        if not hasattr(self, win_name):
            self._cv_win_name = win_name
            cv2.namedWindow(winname=f'{id(self)}')
            cv2.setWindowTitle(f'{id(self)}', win_name)
        else:
            cv2.setWindowTitle(f'{id(self)}', win_name)
        shown_img = self.get_image() if drawn_img is None else drawn_img
        cv2.imshow(str(id(self)), bgr2rgb(shown_img))
        cv2.waitKey(int(np.ceil(wait_time * 1000)))


    def imshow_bboxes(img: Union[str, np.ndarray],
                      bboxes: Union[list, np.ndarray],
                      colors: ColorType = 'green',
                      top_k: int = -1,
                      thickness: int = 1):
        """Draw bboxes on an image.

        Args:
            img (str or ndarray): The image to be displayed.
            bboxes (list or ndarray): A list of ndarray of shape (k, 4).
            colors (Color or str or tuple or int or ndarray): A list of colors.
            top_k (int): Plot the first k bboxes only if set positive.
            thickness (int): Thickness of lines.

        Returns:
            ndarray: The image with bboxes drawn on it.
        """
        img = np.ascontiguousarray(img)

        if isinstance(bboxes, np.ndarray):
            bboxes = [bboxes]
        if not isinstance(colors, list):
            colors = [colors for _ in range(len(bboxes))]
        colors = [color_val(c) for c in colors]
        assert len(bboxes) == len(colors)

        for i, _bboxes in enumerate(bboxes):
            _bboxes = _bboxes.astype(np.int32)
            if top_k <= 0:
                _top_k = _bboxes.shape[0]
            else:
                _top_k = min(top_k, _bboxes.shape[0])
            for j in range(_top_k):
                left_top = (_bboxes[j, 0], _bboxes[j, 1])
                right_bottom = (_bboxes[j, 2], _bboxes[j, 3])
                cv2.rectangle(
                    img, left_top, right_bottom, colors[i], thickness=thickness)
        return img
