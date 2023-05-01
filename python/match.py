import cv2
import numpy as np
import logging
import yaml
import os

csd = os.path.dirname(os.path.abspath(__file__))
config = yaml.safe_load(open(csd + "/config.yaml"))
offset_pix = config['vision']['match_template']['limits']['offset_pix']
match_threshold = config['vision']['match_template']['limits']['match_threshold']
delta_angle = config['vision']['match_template']['limits']['delta_angle']
delta_scale = config['vision']['match_template']['limits']['delta_scale']

templateDir = config['vision']['match_template']['templateDir']
resolution_x = config['vision']['pipline']['resolution_x']
resolution_y = config['vision']['pipline']['resolution_y']

#logger
logger_level = config['logger']['level']
logger_debug_file = config['logger']['debug_file']
logger_format = config['logger']['format']


class MatchCapture:
    def __init__(self, depth_colormap, templates):
        self.logger = logging.getLogger("vision.matching")
        self.depth_colormap = depth_colormap
        self.templates = templates

    def rotate_image(self, image, angle):
        image_center = tuple(np.array(image.shape[1::-1]) / 2)
        rot_mat = cv2.getRotationMatrix2D(image_center, -angle, 1.0)
        result = cv2.warpAffine(image, rot_mat, image.shape[1::-1], flags=cv2.INTER_LINEAR)
        return result

    def scale_image(self, image, percent, maxwh):
        color_scale_rate = 0
        max_width = maxwh[1]
        max_height = maxwh[0]
        max_percent_width = max_width / image.shape[1] * 100
        max_percent_height = max_height / image.shape[0] * 100
        max_percent = 0
        if max_percent_width < max_percent_height:
            max_percent = max_percent_width
        else:
            max_percent = max_percent_height
        if percent > max_percent:
            percent = max_percent
        width = int(image.shape[1] * percent / 100)
        height = int(image.shape[0] * percent / 100)
        image = image + int(percent * color_scale_rate)
        result = cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)
        return result, percent

    def invariantMatchTemplate(self, rgbimage, rgbtemplate, method, matched_thresh, rot_range, rot_interval, scale_range,
                               scale_interval, rm_redundant):
        """
        rgbimage: RGB image where the search is running.
        rgbtemplate: RGB searched template. It must be not greater than the source image and have the same data type.
        method: [String] Parameter specifying the comparison method
        matched_thresh: [Float] Setting threshold of matched results(0~1).
        rgbdiff_thresh: [Float] Setting threshold of average RGB difference between template and source image.
        rot_range: [Integer] Array of range of rotation angle in degrees. Example: [0,360]
        rot_interval: [Integer] Interval of traversing the range of rotation angle in degrees.
        scale_range: [Integer] Array of range of scaling in percentage. Example: [50,200]
        scale_interval: [Integer] Interval of traversing the range of scaling in percentage.
        rm_redundant: [Boolean] Option for removing redundant matched results based on the width and height of the template.

        Returns: List of satisfied matched points in format [[point.x, point.y], angle, scale, matched_thresh].
        """
        image_maxwh = rgbimage.shape
        height, width, numchannel = rgbtemplate.shape
        all_points = []
        for next_angle in range(rot_range[0], rot_range[1], rot_interval):
            for next_scale in range(scale_range[0], scale_range[1], scale_interval):
                scaled_template, actual_scale = self.scale_image(rgbtemplate, next_scale, image_maxwh)
                if next_angle == 0:
                    rotated_template = scaled_template
                else:
                    rotated_template = self.rotate_image(scaled_template, next_angle)
                template_gray = cv2.cvtColor(rotated_template, cv2.COLOR_BGR2GRAY)
                contours, _ = cv2.findContours(template_gray, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
                areas = [cv2.contourArea(c) for c in contours]
                max_index = np.argmax(areas)
                cnt = contours[max_index]
                x, y, w, h = cv2.boundingRect(cnt)
                # print(x, y, w, h)
                rotated_template = rotated_template[y:y + h, x:x + w]
                matched_points = cv2.matchTemplate(rgbimage, rotated_template, method, None, rotated_template.copy())
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(matched_points)
                if max_val >= matched_thresh:
                    max_loc = (max_loc[0] - x, max_loc[1] - y)
                    all_points.append([max_loc, next_angle, actual_scale, max_val])
        all_points = sorted(all_points, key=lambda x: -x[3])
        if rm_redundant == True:
            lone_points_list = []
            visited_points_list = []
            for point_info in all_points:
                point = point_info[0]
                scale = point_info[2]
                all_visited_points_not_close = True
                if len(visited_points_list) != 0:
                    for visited_point in visited_points_list:
                        if ((abs(visited_point[0] - point[0]) < (width * scale / 100)) and (
                                abs(visited_point[1] - point[1]) < (height * scale / 100))):
                            all_visited_points_not_close = False
                    if all_visited_points_not_close == True:
                        lone_points_list.append(point_info)
                        visited_points_list.append(point)
                else:
                    lone_points_list.append(point_info)
                    visited_points_list.append(point)
            points_list = lone_points_list
        else:
            points_list = all_points
        return points_list

    def eval_match(self):
        # img_rgb = cv2.imread('./templates/2/part8.png')
        # template_rgb = cv2.imread('./templates/2/part9.png')
        # print (f"templates loop for {templates}")
        res_list = []
        for part, pics in self.templates.items():
            # print (f"look for part type {part}")
            for file in pics:
                # print (f"look for template {template}")
                template = cv2.imread(f"{templateDir}/{part}/{file}")
                points_list = self.invariantMatchTemplate(self.depth_colormap, template, cv2.TM_CCORR_NORMED,
                                                          match_threshold, [-delta_angle, delta_angle + 1], 1,
                                                          [100 - delta_scale, 100 + delta_scale + 1], 1, True)
                if len(points_list) > 0:
                    print(f"Part type {part} found")
                    res_list.append(
                        {"points": list(
                            filter(lambda x: (abs(x[0][0]) < offset_pix and abs(x[0][1]) < offset_pix), points_list)),
                         "part": part})
                    continue
                #for pos in poses: проверять шаблоны для каждой позиции

        if len(res_list) == 0:
            result = 'no matches'
        elif len(res_list) == 1:
            result = 'ok'
        else:
            result = 'many matches'
        return result, res_list
    def eval_match_forever(self):

        return 0
