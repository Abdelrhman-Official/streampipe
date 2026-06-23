[app]
title = StreamPipe
package.name = streampipe
package.domain = org.streampipe
source.dir = .
source.include_exts = py,png,jpg,kv,yaml
version = 0.1.0

requirements = python3,kivy==2.3.0,yt-dlp,pyyaml,certifi,urllib3,charset-normalizer,requests,mutagen,brotli,websockets

orientation = portrait
fullscreen = 0

android.permissions = INTERNET, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
