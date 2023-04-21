import pyrealsense2 as rs
import numpy as np
# import matplotlib.pyplot as plt

import cv2

# var huck
found_part_num = 0
teach_part_num = 0

# separate file - configurations of parts and settings
tolerance = 0.05
resolution_x, resolution_y = 640, 480
# resolution_x,resolution_y=1280,720
fps = 30
parts = [dict(code='8АТ-1250-11', part_name='Корпус маятника', step_name='Установ А', h=212, w=89, Zavg=400),
         dict(code='8АТ-1250-11', part_name='Корпус маятника', step_name='Установ B', h=208, w=87, Zavg=400),
         dict(code='8АТ-1250-11', part_name='Корпус маятника', step_name='Установ C', h=208, w=80.6, Zavg=400),
         dict(code='8АТ-1250-11', part_name='Корпус маятника', step_name='Установ D', h=208, w=80, Zavg=400),
         dict(code='8АТ-1250-11', part_name='Корпус маятника', step_name='Установ E', h=528, w=268, Zavg=400),
         dict(code='17115.2900.77', part_name='Переходник', step_name='Установ А', h=273, w=206, Zavg=400),
         dict(code='17115.2900.77', part_name='Переходник', step_name='Установ B', h=209.03, w=206, Zavg=400)]


# from transform import hough_windowed_rectangle, hough_cricles
# from utils import plot_hough_space, graph_output, graph_rectangles_and_circles, countMoney
# from skimage.io import imshow
# import matplotlib.pyplot as plt


part1_img = cv2.imread("part1.png")

# Configure depth and color streams
pipeline = rs.pipeline()
config = rs.config()

# Get device product line for setting a supporting resolution
pipeline_wrapper = rs.pipeline_wrapper(pipeline)
pipeline_profile = config.resolve(pipeline_wrapper)
device = pipeline_profile.get_device()
# depth_sensor = device.first_depth_sensor()
device_product_line = str(device.get_info(rs.camera_info.product_line))
print('device_product_line', device_product_line)

found_rgb = False
for s in device.sensors:
    if s.get_info(rs.camera_info.name) == 'RGB Camera':
        found_rgb = True
        break
if not found_rgb:
    print("The demo requires Depth camera with Color sensor")
    exit(0)
align = rs.align(rs.stream.color)
config.enable_stream(rs.stream.depth, resolution_x, resolution_y, rs.format.z16, fps)
config.enable_stream(rs.stream.color, resolution_x, resolution_y, rs.format.bgr8, fps)

# Start streaming
pipeline.start(config)
try:
    while True:
        # Wait for a coherent pair of frames: depth and color
        frames = pipeline.wait_for_frames()
        depth_frame = frames.get_depth_frame()
        color_frame = frames.get_color_frame()
        if not depth_frame or not color_frame:
            continue

        color_image = np.asanyarray(color_frame.get_data())

        frames = []
        for x in range(15):
            frameset = pipeline.wait_for_frames()
            frames.append(frameset.get_depth_frame())

        hole_filling = rs.hole_filling_filter()
        for x in range(15):
            frame = hole_filling.process(frames[x])
            frames[x] = np.asanyarray(frame.get_data())

        depth_image = np.min(frames, axis=0)
        # print(np.min(depth_image),np.max(depth_image))
        # depth_image = depth_image.astype(dtype=np.uint8)
        # #depth_image = cv2.cvtColor(depth_image,cv2.COLOR_BGR2GRAY)
        # depth_image = cv2.adaptiveThreshold(depth_image,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV,51,9)
        # #depth_image = cv2.adaptiveThreshold(depth_image,255,cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY,11,2)
        # #depth_image = cv2.adaptiveThreshold(depth_image,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY,11,2)

        # Calculate the min along the time axis
        # depth_image = np.min(frames, axis=0).astype(dtype=np.uint16)

        # hight normalization for template search
        resultimage = np.zeros((resolution_x, resolution_y))
        depth_image = cv2.normalize(depth_image, resultimage, 0, 100, cv2.NORM_MINMAX)

        depth_image = depth_image.astype(dtype=np.uint16)
        depth_image = cv2.medianBlur(depth_image, 5)

        # Apply colormap on depth image (image must be converted to 8-bit per pixel first)
        depth_image = cv2.convertScaleAbs(depth_image, alpha=10)
        depth_image2 = depth_image

        x, y = resolution_x // 4, resolution_y // 4
        w, h = x * 3, y * 3
        crop_img = depth_image[x:x + w, y:y + h]
        crop_img[crop_img < 5] = 255
        max_hight_color = np.min(crop_img)
        depth_image[depth_image < max_hight_color] = 255
        print('max_hight_color', max_hight_color)
        depth_image = depth_image - max_hight_color

        # constants
        centre_x, centre_y = resolution_x // 2 - 53, resolution_y // 2 + 27
        trust_interval = [320, 490]
        min_spot = 20

        x1, y1 = int(centre_x - min_spot // 2), int(centre_y - min_spot // 2)
        x2, y2 = int(centre_x + min_spot // 2), int(centre_y + min_spot // 2)
        cropped_image = depth_image[x1:x2, y1:y2]
        Cmean = np.mean(cropped_image)

        # monochrome view
        # depth_image[depth_image<Cmean-15]=0
        # depth_image[depth_image>Cmean+15]=0
        # depth_image[depth_image>0]=255

        # contours = cv2.findContours(depth_image, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        contours, _ = cv2.findContours(depth_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        # print(len(contours))
        bboxes = []
        rboxes = []
        cnts = []
        k = -1.5
        b = 565
        Zavg = k * Cmean + b
        for cnt in contours:
            ## Skip non-central area
            if cv2.pointPolygonTest(cnt, (centre_x, centre_y), True) < 0:
                continue
            ## Get the stright bounding rect
            bbox = cv2.boundingRect(cnt)
            x, y, w, h = bbox
            if w < 30 or h < 30 or w * h < 2000 or w > 500:
                continue

            ## Draw rect
            cv2.rectangle(depth_image, (x, y), (x + w, y + h), (255, 0, 0), 1, 16)

            ## Get the rotated rect
            rbox = cv2.minAreaRect(cnt)
            (x1, y1), (cw, ch), rot_angle = rbox
            x1 = int(x1)
            y1 = int(y1)
            cw = int(cw)
            ch = int(ch)
            # print ((x1,y1), (cw,ch))
            ## Draw rotated rect
            # !!!!!!!!!not worked!!!!!
            # cv2.rectangle(depth_image, (x1,y1), (x1+cw,y1+ch), (255,0,0), 1, 16)
            # print("rot_angle:", rot_angle)

            ## backup
            bboxes.append(bbox)
            rboxes.append(rbox)
            cnts.append(cnt)

            # cv2.putText(depth_colormap, f"Zavg {round(Zavg, 1)} mm", (int(x1 - 20), int(y1 - 20)), cv2.FONT_HERSHEY_PLAIN, 2, (100, 200, 0), 2)
            # cv2.putText(color_image, f"Zavg {round(Zavg, 1)} mm", (int(x1 - 20), int(y1 - 20)), cv2.FONT_HERSHEY_PLAIN, 2, (100, 200, 0), 2)
            # print(f'w {hw[1]} h {hw[0]} Zavg {Zavg}')
            pk = 0.003125
            pb = -0.125
            part_w = cw * (pk * Zavg + pb)
            part_h = ch * (pk * Zavg + pb)
            # print(f'part_w {part_w} part_h {part_h}')
            cv2.putText(depth_image, f"{round(part_h, 0)} x {round(part_w, 0)} mm", (int(x1 - 20), int(y1 - 20)),
                        cv2.FONT_HERSHEY_PLAIN, 2, (100, 200, 0), 2)
            cv2.putText(color_image, f"{round(part_h, 0)} x {round(part_w, 0)} mm", (int(x1 - 20), int(y1 - 20)),
                        cv2.FONT_HERSHEY_PLAIN, 2, (100, 200, 0), 2)

        depth_colormap = cv2.applyColorMap(depth_image, cv2.COLORMAP_JET)
        depth_colormap2 = cv2.applyColorMap(depth_image2, cv2.COLORMAP_JET)

        # rectangle = np.array([[x1,y1],[x2,y1],[x2,y2],[x1,y2],[x1,y1]], np.int32)
        # depth_colormap =cv2.polylines(depth_colormap, [rectangle], False, (255,0,0), thickness=1)
        # color_image =cv2.polylines(color_image, [rectangle], False, (255,0,0), thickness=1)

        last_found_part_num = found_part_num
        found_part_num = 0
        for num, part in enumerate(parts):
            h, w, Zavg = part['h'], part['w'], part['Zavg']
            part_name, step_name = part['part_name'], part['step_name']
            if trust_interval[0] < Zavg < trust_interval[1]:
                x1, y1 = int(centre_x - w // 2), int(centre_y - h // 2)
                x2, y2 = int(centre_x + w // 2), int(centre_y + h // 2)
                cropped_image = depth_colormap[x1:x2, y1:y2]
                Cavg = np.mean(cropped_image)
                CurZavg = k * Cavg + b

                if Zavg * (1 - tolerance) < CurZavg < Zavg * (1 + tolerance):
                    if found_part_num == 0:
                        found_part_name = part_name
                        found_part_step = step_name
                        found_part_num = num
                        rectangle = np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2], [x1, y1]], np.int32)

                        depth_colormap = cv2.polylines(depth_colormap, [rectangle], False, (0, 255, 0), thickness=1)
                        color_image = cv2.polylines(color_image, [rectangle], False, (0, 255, 0), thickness=1)
                        if last_found_part_num != found_part_num:
                            print(f'Part detected: {part_name} {step_name}')
                    else:
                        print(
                            f'warning! several parts detected {part_name} {step_name} and {found_part_name} {found_part_step}')
                        found_part_num = 0
                        break
            else:
                print(f'warning! part {num} have wrong Zavg {Zavg}. Trust interval is {trust_interval}')

        # diagonal draw
        # depth_colormap =cv2.polylines(depth_colormap, [np.array([[0,0],[resolution_x,resolution_y]], np.int32)], False, (0,255,0), thickness=1)
        # color_image =cv2.polylines(color_image, [np.array([[0,0],[resolution_x,resolution_y]], np.int32)], False, (0,255,0), thickness=1)

        depth_colormap_dim = depth_colormap.shape
        color_colormap_dim = color_image.shape

        # If depth and color resolutions are different, resize color image to match depth image for display
        if depth_colormap_dim != color_colormap_dim:
            resized_color_image = cv2.resize(color_image, dsize=(depth_colormap_dim[1], depth_colormap_dim[0]),
                                             interpolation=cv2.INTER_AREA)
            images = np.hstack((depth_colormap, resized_color_image))
        else:
            # images = np.hstack((depth_colormap, color_image))
            images = np.hstack((depth_colormap, depth_colormap2))

        # Show images
        cv2.startWindowThread()
        cv2.namedWindow('RealSense', cv2.WINDOW_AUTOSIZE)
        cv2.imshow('RealSense', images)
        cv2.waitKey(1)

finally:

    # Stop streaming
    pipeline.stop()