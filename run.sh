#!/bin/bash

video_dir=./DATA/video
output_dir=./DATA/tmp
stage=0

mkdir -p ${output_dir} || exit 1

if [ $stage -le 0 ]; then
    echo "Stage 0: Face detection and face recognition."
    # input video, output time stamp.
    python face_det.py --video_dir=${video_dir} --output_dir=${output_dir} || exit 1
    echo "Finished"
    exit 0
fi

if [ $stage -le 1 ]; then
    echo "Stage 1: Seperate into clips with subtitle time stamps."
    # input 2fps_timestamp, output clip_timestamp, save time stamps (json) and subtitle (text)
    python clip_with_subtitle.py --input_file=${output_dir}/2fps_timestamp
    echo "Stage 1 finished."
fi

if [ $stage -le 2 ]; then
    echo "Stage 2: Get clip face bbox."
    
fi

if [ $stage -le 3]; then
    echo "Stage 3: Get clip upper body bbox"
    
fi
    
