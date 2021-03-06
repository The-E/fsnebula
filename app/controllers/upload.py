import os.path
import time
import magic
from io import SEEK_END
from flask import request, jsonify, abort

from .. import app
from ..helpers import verify_token, gen_hash
from ..models import UploadedFile


@app.route('/api/1/upload/check', methods={'POST'})
def check_uploaded():
    user = verify_token()
    if not user:
        abort(403)

    if 'content_checksum' in request.form:
        file = UploadedFile.objects(content_checksum=request.form['content_checksum']).first()
    else:
        file = UploadedFile.objects(checksum=request.form['checksum']).first()

    if file:
        return jsonify(result=True, checksum=file.checksum, filesize=file.filesize, vp_checksum=file.vp_checksum)
    else:
        return jsonify(result=False)


@app.route('/api/1/upload/file', methods={'POST'})
def upload_file():
    user = verify_token()
    if not user:
        abort(403)

    if 'checksum' not in request.form or 'file' not in request.files:
        abort(400)

    file = request.files['file']
    checksum = request.form['checksum']
    if gen_hash(file.stream, 'sha256') != checksum:
        return jsonify(result=False, reason='checksum')

    file.seek(0)
    mime = magic.from_buffer(file.read(1024), mime=True)
    if mime in app.config['MIME_BLACKLIST']:
        return jsonify(result=False, reason='invalid mime')

    file.seek(0, SEEK_END)
    record = UploadedFile(expires=time.time() + 24 * 60 * 60,
                          checksum=checksum,
                          content_checksum=request.form.get('content_checksum'),
                          vp_checksum=request.form.get('vp_checksum'),
                          filesize=file.tell())

    if mime in ('image/jpg', 'image/jpeg'):
        record.file_ext = 'jpg'
    elif mime == 'image/png':
        record.file_ext = 'png'
    elif mime == 'image/x-ms-bmp':
        record.file_ext = 'bmp'

    record.gen_filename()
    record.save()

    full_path = os.path.join(app.config['FILE_STORAGE'], os.path.normpath(record.filename))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    file.seek(0)
    file.save(full_path)

    return jsonify(result=True)
