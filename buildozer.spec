[app]

title = Crown Battle
package.name = crownbattle
package.domain = org.crown.battle

source.dir = .
source.include_exts = py

version = 1.0

# --- THE FIX IS HERE ---
# Added pygame version, hostpython3, and setuptools to stop the clang crash
requirements = python3, pygame

orientation = landscape
fullscreen = 1

android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE

android.api = 33
android.minapi = 21
android.archs = arm64-v8a,armeabi-v7a

android.bootstrap = sdl2

[buildozer]

log_level = 2
warn_on_root = 1
