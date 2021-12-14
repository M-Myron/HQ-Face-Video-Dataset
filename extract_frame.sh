mkdir apple
mkdir apple_2fps
ffmpeg -i apple.webm -f image2 -vf fps=2 -qscale:v 2 ./apple_2fps/img_%05d.jpg
ffmpeg -i apple.webm -f image2 -vf fps=30 -qscale:v 2 ./apple/img_%05d.jpg
