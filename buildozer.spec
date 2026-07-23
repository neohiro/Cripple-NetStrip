[app]
# (str) Title of your application
title = NetStrip

# (str) Package name
package.name = netstrip

# (str) Package domain (needed for android/ios packaging)
package.domain = org.cripple

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,json,md,txt,db,yml

# (str) Application versioning
version = 3.1.0

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3,kivy,pyjnius,cryptography,dnslib,maxminddb,requests,psutil,packaging

# (str) Icon of the application
icon.filename = %(source.dir)s/assets/cripple_logo.png

# (str) Supported orientations (landscape, sensorLandscape, portrait or all)
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (string) Presplash background color (for android toolchain)
android.presplash_color = #06060b

# (list) Permissions
android.permissions = INTERNET, BIND_VPN_SERVICE, ACCESS_NETWORK_STATE, FOREGROUND_SERVICE, FOREGROUND_SERVICE_SPECIAL_USE, ACCESS_FINE_LOCATION, ACCESS_WIFI_STATE

# (int) Target Android API, should be as high as possible.
android.api = 33

# (int) Minimum API your APK will support.
android.minapi = 21

# (list) List of Java files to add to the android project
android.add_src = src

# (str) Extra xml file to write directly inside the <manifest><application> tag
android.extra_manifest_application = extra_manifest_app.xml

# (bool) If True, then automatically accept SDK license
android.accept_sdk_license = True

# (str) Android entry point, default is ok for Kivy-based app
android.entrypoint = android_main.py

# (list) The Android archs to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
android.archs = arm64-v8a

# (bool) allows android app to backup to Google Drive
android.allow_backup = True

[buildozer]
# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1
