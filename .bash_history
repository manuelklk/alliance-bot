python -c "import cv2, numpy; print('OpenCV Version:', cv2.__version__)"
pkg install dbus -y
pkg install x11-repo -y
pkg install libopencv-contrib -y
dpkg --configure -a
apt --fix-broken install -y
apt remove --purge "qt6-*" "opencv*" "python-opencv*" -y
apt autoremove -y
close
exit
pkg update && pkg upgrade -y
termux-setup-storage
pkg install python clang make cmake libjpeg-turbo libpng ffmpeg -y
pkg install python-numpy python-pillow
pkg install x11-repo
pkg install opencv-python
pip install opencv-python
exit
pkg update && pkg upgrade
pkg install python clang make libjpeg-turbo libpng
pip install --upgrade pip
pip install numpy
pip install opencv-python
pkg update && pkg upgrade -y
exit
