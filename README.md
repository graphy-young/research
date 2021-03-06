# Raspmeasure
Raspmeasure is a portable measuring device for fine particles.
Hardware is based on Raspberry Pi, not compatible with Arduino.
This project is a part of research conducting in ENDS LAB in Kookmin University.
Some codes won't be open for security.

# Requirements
* Raspberry Pi 3 or newer (older model is recommended for more uptime)
  * Raspberry Pi OS (former Raspbian Stretch)
  * Python 3.6 or higher
* Honeywell HPMA115S0-XXX
* Geekworm X750 UPS module & 18650 cells Lithium Ion batteries * 4
* DS3231 RTC moudle
* External MySQL DB server to record measured data
* Wi-Fi Network for portable use

# Hardware setup


# Instruction
* Enable Raspberry Pi's SSH connection in `raspi-config` or making `/boot/ssh` if your environment is headless.
* install MySQL Server (higher version recommended) & MySQL Workbench on your external database server
* Using `database/raspmeasure_model.mwb`, excecute forward engineering via MySQL Workbench
* Create `keys.py` to conenct Wireless network & MySQL DB server. file should be like below
```
ssid = 'network name'
wpa_key = 'wifi password'

host = 'hostaddress.com'
port = 1000
userName = 'userName'
password = 'password'
dbName = 'dbName'

...(more codes)
```
  * `root` account is not recommended as it can make security threats
* Excecute `init.sh` on your RPi

# Memo
* `keys.py` Required which have database connection information in same directory 
* Original Arduino(.ino) file were removed for some hardware changes!

# Dependency
* Honeywell HPMA115S0 Particulate Sensor Python interface (https://github.com/FEEprojects/honeywell-hpma115s0)
* Raspberry Pi Python Library for SwitchDoc Labs DS3231/AT24C32 RTC Module (https://github.com/switchdoclabs/RTC_SDL_DS3231)
