import cv2
import dlib
import numpy as np
import os
import shutil

video_path = './apple'
video_2fps_path = './apple_2fps'
face_path = 'face.png'

# extract the frames
# print("start extract_frame.sh")
# os.system('sh extract_frame.sh')

detector = dlib.get_frontal_face_detector()
predictor_path = 'shape_predictor_68_face_landmarks.dat'
predictor = dlib.shape_predictor(predictor_path)
face_rec_model_path = 'dlib_face_recognition_resnet_model_v1.dat'
facerec = dlib.face_recognition_model_v1(face_rec_model_path)


def distance(a, b):
    a, b = np.array(a), np.array(b)
    sub = np.sum((a - b) ** 2)
    add = (np.sum(a ** 2) + np.sum(b ** 2)) / 2.
    return sub / add


def get_feature(p):
    img = cv2.imread(p)
    scale_percent = img.shape[0] / 512  # percent of original size
    width = int(img.shape[1] / scale_percent)
    height = int(img.shape[0] / scale_percent)
    dim = (width, height)
    img = cv2.resize(img, dim)
    dets = detector(img)
    face_vector_list = []
    for i, d in enumerate(dets):
        shape = predictor(img, d)
        face_vector = facerec.compute_face_descriptor(img, shape)
        face_vector_list.append(face_vector)
    return face_vector_list


def classifier(a, b, t=0.09):
    if distance(a, b) <= t:
        ret = True
    else:
        ret = False
    return ret


face_gt_feature = get_feature(face_path)[0]

# get the valid period
period = []
g = os.walk(video_2fps_path)
for path, dir_list, file_list in g:
    file_list.sort()
    for file_name in file_list:
        file_path = os.path.join(video_2fps_path, file_name)
        features = get_feature(file_path)
        print(file_name)
        # print(len(features))
        for f in features:
            if classifier(f, face_gt_feature) is True:
                t = int(file_name.split('.')[0].split('_')[1]) * 15
                period.append(t)
                break

t0 = period[0]
period_30fps = []
for i in range(1, len(period)):
    if period[i] != period[i-1] + 15:
        p = (t0, period[i-1])
        period_30fps.append(p)
        t0 = period[i]
period_30fps.append((t0, period[-1]))
print(period_30fps)

# remove frame of 2fps
# shutil.rmtree(video_2fps_path)

# VAD get clip frame

# get face bbox
