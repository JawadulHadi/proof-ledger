# Notes: mistakes and fixes

Log each mistake here with what you tried, what broke, and how you fixed it.
These become your interview answers for the failure-story question.

## 2026-10-11: Deploy scripts lost their executable bit

**What happened:** Commit e7ef3f6 changed `build.sh` and `start.sh` from mode 100755 to 100644 with no content change. Render runs `./build.sh`, so the next deploy would have failed with "permission denied".
**Root cause:** The files were re-uploaded from Windows, which does not keep the Unix executable bit.
**Fix:** The deploy config now runs both scripts through `sh`, so the file mode no longer matters, and the executable bit was restored (commit 0bd8b17).
**What I would do differently:** Never rely on the executable bit for scripts a host runs. Call them as `sh build.sh`, or set `git update-index --chmod=+x` when committing from Windows.
