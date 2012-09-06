#!/bin/bash

cd /proc/asound || exit 1
list=$(ls | grep -E "^card" | grep -v cards)
firstcard=1
for card in $list; do
  cardno=$(echo $card | colrm 1 4)
  if test -d /sys/class/sound/mixer$cardno; then
    # RHEL 5
    path=$(ls -l /sys/class/sound/mixer$cardno/device 2> /dev/null | awk '{ print $NF }')
    if test -z "$path"; then
      continue
    fi
    cd /sys/class/sound/mixer$cardno/$path || exit 1
    path=$(pwd)
    driver=$(ls -l $path/driver | awk '{ FS="/"; split($NF, a); print a[length(a)] }')
    if test "$driver" != "snd_hda_intel" -a "$driver" != "snd-hda-intel"; then
      continue
    fi    
  else
    # RHEL 6
    driver=$(ls -l /sys/class/sound/$card/device/driver/module | awk '{ FS="/"; split($NF, a); print a[length(a)] }')
    if test "$driver" != "snd_hda_intel" -a "$driver" != "snd-hda-intel"; then
      continue
    fi
    path=$(ls -l /sys/class/sound/$card/device/driver/*:*:* 2> /dev/null | awk '{ print $NF }')
    if test -z "$path"; then
      continue
    fi
    cd /sys/class/sound/$card/device/driver/$path || exit 1
    path=$(pwd)
  fi
  vendor=$(cat $path/vendor)
  device=$(cat $path/device)
  svendor=$(cat $path/subsystem_vendor)
  sdevice=$(cat $path/subsystem_device)
  cd /proc/asound/$card || exit 1
  if test -z "$firstcard"; then
    echo "----"
  fi
  echo "ALSA Card: $card"
  echo "Driver: $driver"
  echo "Device path: $path"
  echo "PCI Device ID: $vendor:$device"
  echo "PCI Subsystem Device ID: $svendor:$sdevice"
  codecs=$(ls | grep -E "^codec#")
  for codec in $codecs; do
    echo "  ----"
    awk '/^Codec: / { print "  " $0 }
         /^Address: / { print "  " $0 }
         /Function Id:/ { print "  " $0 }
         /^Vendor Id:/ { print "  " $0 }
         /^Subsystem Id:/ { print "  " $0 }
         /^Revision Id:/ { print "  " $0 }' \
        /proc/asound/$card/$codec
  done
  firstcard=
done
 