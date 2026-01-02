# littleguy

## initial setup

### enable hardware interfaces

- run `sudo raspi-config`
- navigate to Interface Options
- enable I2C
- make sure Legacy Camera is disabled
- `sudo reboot now`

## update and install dependencies

[] TODO: update this for pi os lite, it doesn't come with all the camera and opencv dependencies by default
[] TODO: make an init script that does this for you

- `sudo apt update && sudo apt upgrade -y`
- `sudo apt install -y python3-pip python3-full python3-venv i2c-tools libcamera-apps`
- `mkdir ~/roomba_vslam && cd ~/roomba_vslam`
- `python3 -m venv --system-site-packages venv`
- `source venv/bin/activate`
- `pip install mpu6050-raspberrypi flask opencv-python`

[] TODO: make env var to sourced python for sudo commands

## mount usb drive

- identify drive `lsblk` and find the right device/volume
- grab the uuid `sudo blkid /dev/sda1` where `sda1` is the volume
- copy the uuid string
- create a mount point `sudo mkdir -p /mnt/usb`
- `sudo chown pi:pi /mnt/usb` where `pi` is your username
- add the following line to the bottom of `/etc/fstab`: `UUID=COPIED-UUID  /mnt/usb  auto  user,rw,nofail,uid=1000,umask=1000  0  0` where uid and umask are the values from running `id`
- you might need to run `sudo apt install exfat-fuse ntfs-3g -y` if mounting doesnt work
- `systemctl daemon-reload`
- `sudo mount -a`
- check if you have rw access with `touch /mnt/usb/testfile.txt && ls /mnt/usb/`

## make sure camera and accelerometer are working

- if full os install, test video with `rpicam-hello --timeout 5000`
- if headless/lite os, take pic with `rpicam-still -o test.jpg`
- test mpu6050 connection `i2cdetect -y 1` and look for `68` in the grid


- 64A5-f009
- reload daemon after fstab update
- 
