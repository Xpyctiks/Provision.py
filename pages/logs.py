import logging
import os
from flask import render_template,redirect,Blueprint,current_app,flash,jsonify,request
from flask_login import login_required
from functions.site_actions import is_admin, is_mail_admin

logs_bp = Blueprint("logs", __name__)

LOG_PAGE_LINES = 500
LOG_MAX_PAGE_LINES = 5000
#reading backwards in blocks of this size until enough lines are collected
LOG_READ_BLOCK = 64 * 1024
#max amount of new data returned by one "tail" poll - if more was written since the last poll, the client reloads
LOG_MAX_TAIL_BYTES = 2 * 1024 * 1024

@logs_bp.route("/logs/", methods=['GET'])
@login_required
def showLogs():
  """Simple functions that shows up a current content of programm log file."""
  try:
    return render_template("template-logs.html",admin_panel=is_admin(),mail_admin=is_mail_admin(),version=current_app.config.get("VERSION",""))
  except Exception as err:
    logging.error(f"showLogs(): gereral error: {err}")
    flash(f"Загальна помилка сторінки логу!",'alert alert-danger')
    return redirect("/",302)

def _read_lines_before(f, before: int, count: int):
  """Reads up to `count` complete lines that end at byte offset `before` (which must be a line start or EOF).
  Returns (lines, start_offset) where start_offset is the byte offset of the first returned line."""
  pos = before
  data = b""
  #read backwards block by block until there are more than `count` line breaks, or the file start is reached
  while pos > 0 and data.count(b"\n") <= count:
    step = min(LOG_READ_BLOCK, pos)
    pos -= step
    f.seek(pos)
    data = f.read(step) + data
  lines = data.splitlines(keepends=True)
  #when not at the file start, the first piece is a partial line - it belongs to the previous page
  if pos > 0 and lines:
    pos += len(lines[0])
    lines = lines[1:]
  if len(lines) > count:
    pos += sum(len(l) for l in lines[:-count])
    lines = lines[-count:]
  return [l.decode("utf-8", errors="replace") for l in lines], pos

@logs_bp.route("/logs/api/")
@login_required
def logs_api():
  """JSON API for the log page, works with byte offsets in the log file:
  - no params / ?lines=N           -> the last N lines (default 500)
  - ?before=OFFSET&lines=N         -> N lines preceding OFFSET (scrolling back in history)
  - ?after=OFFSET                  -> complete lines appended after OFFSET (live tail polling)
  Every answer contains "start" (offset of the first returned line) and "end" (offset right after the last one).
  "reset": true means the file was rotated/truncated or grew too much - the client should reload from scratch."""
  log_file = current_app.config.get("LOG_FILE","")
  if not log_file or not os.path.exists(log_file):
    return jsonify({"error": "Log not found"}), 404
  try:
    lines_count = max(1, min(int(request.args.get("lines", LOG_PAGE_LINES)), LOG_MAX_PAGE_LINES))
    size = os.path.getsize(log_file)
    with open(log_file, "rb") as f:
      after = request.args.get("after")
      if after is not None:
        after = int(after)
        if after > size or size - after > LOG_MAX_TAIL_BYTES:
          return jsonify({"reset": True, "lines": [], "start": size, "end": size, "size": size})
        f.seek(after)
        data = f.read(size - after)
        #return only complete lines - a line still being written will come with the next poll
        cut = data.rfind(b"\n") + 1
        data = data[:cut]
        lines = [l.decode("utf-8", errors="replace") for l in data.splitlines(keepends=True)]
        return jsonify({"lines": lines, "start": after, "end": after + cut, "size": size})
      before = request.args.get("before")
      before = size if before is None else max(0, min(int(before), size))
      #on the first load don't show a half-written last line
      if request.args.get("before") is None:
        f.seek(max(0, size - LOG_READ_BLOCK))
        tail = f.read()
        before = size - (len(tail) - (tail.rfind(b"\n") + 1)) if b"\n" in tail else size
      lines, start = _read_lines_before(f, before, lines_count)
      return jsonify({"lines": lines, "start": start, "end": before, "size": size})
  except ValueError:
    return jsonify({"error": "Bad parameters"}), 400
  except Exception as err:
    logging.error(f"logs_api(): general error: {err}")
    return jsonify({"error": str(err)}), 500
