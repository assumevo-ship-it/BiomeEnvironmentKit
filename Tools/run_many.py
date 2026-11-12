"""Dev helper: runs the scripts named in BAM_RUN (comma separated, relative to Tools) in one editor session."""
import os
import runpy

import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
quit_after = os.environ.get("BAM_QUIT") == "1"
os.environ["BAM_QUIT"] = "0"
for rel in [x for x in os.environ.get("BAM_RUN", "").split(",") if x]:
    unreal.log(f"[BAM] run {rel}")
    try:
        runpy.run_path(os.path.join(HERE, rel), run_name="__main__")
    except Exception:  # noqa
        import traceback
        unreal.log_error("[BAM] " + traceback.format_exc())
if quit_after:
    unreal.SystemLibrary.quit_editor()
