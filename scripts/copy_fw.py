# scripts/copy_fw.py
Import("env")
import os, shutil

OUT = os.path.join(".pio", "build", "wokwi")
os.makedirs(OUT, exist_ok=True)

def _copy_to_wokwi(target, source, env):  # callback signature: (target, source, env)
    src = str(target[0])                  # path to the built file
    shutil.copy2(src, os.path.join(OUT, os.path.basename(src)))
    print(f"[wokwi] copied {os.path.basename(src)}")

# run after build finishes producing these files
env.AddPostAction("$BUILD_DIR/${PROGNAME}.bin", _copy_to_wokwi)
env.AddPostAction("$BUILD_DIR/${PROGNAME}.elf", _copy_to_wokwi)
