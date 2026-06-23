[app]
title = StreamPipe
package.name = streampipe
package.domain = org.streampipe
source.dir = .
source.include_exts = py,png,jpg,kv,yaml
source.exclude_dirs = .venv, .git, .github, streampipe.egg-info, __pycache__
version = 0.1.0

requirements = python3,kivy==2.3.0,yt-dlp,pyyaml,certifi,urllib3,charset-normalizer,requests,mutagen,brotli,websockets

orientation = portrait
fullscreen = 0

android.permissions = INTERNET, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 24
android.ndk = 25b
android.build_tools_version = 33.0.2
android.sdk = 33
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
