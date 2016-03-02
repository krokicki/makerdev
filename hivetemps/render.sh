#!/bin/sh
ffmpeg -framerate 60 -i render_%06d.png -c:v libx264 -r 60 -pix_fmt yuv420p out.mp4

