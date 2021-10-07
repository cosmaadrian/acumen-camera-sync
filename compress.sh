#!/bin/bash
set -e

readarray -t videos < captured_videos.txt

for video in "${videos[@]}"
do
    filename=$(basename -- "$video")
    extension="${filename##*.}"
    filename="${filename%.*}"
    source_dir=`dirname $video`
    output_file=${source_dir}/${filename}-265.${extension}

    ffmpeg -y -i $video -vcodec libx265 -crf 28 $output_file
    sed -i .bak "/$filename/d" captured_videos.txt
    rm -fr $video
done

