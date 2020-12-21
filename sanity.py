import sys
import bson
from app.models import UploadedFile, ModRelease


RESTORE = False
print('Loading releases backup...')

rel_bak = {}
with open('4_jul_dump/nebula/mod_release.bson', 'rb') as stream:
  for doc in bson.decode_file_iter(stream):
    rel_bak[doc['mod'] + '_' + doc['version']] = doc

print('Fetching files...')
ft = {}
vpt = {}
for f in UploadedFile.objects:
  ft[f.checksum] = f
  if f.vp_checksum:
    vpt[f.vp_checksum] = f

print('Processing current releases...')
errors = 0
fixes = 0
backups = 0
restored = 0
for mr in ModRelease.objects(hidden=False):
  if mr.mod.id == 'FSO':
    continue

  print(mr.mod.id, mr.version)
  bak = rel_bak.get(mr.mod.id + '_' + mr.version)
  #if not bak:
  #  print(list(rel_bak.keys())[0])
  #  break

  changed = False

  for i, pkg in enumerate(mr.packages):
    for ai, ar in enumerate(pkg.files):
      if ar.checksum not in ft:
        print(pkg.name, '>', ar.checksum, 'Missing!')
        errors += 1
        continue

      f = ft[ar.checksum]
      has_error = False
      if ar.filesize != f.filesize:
        print(pkg.name, '>', ar.checksum, 'Size mismatch!')
        if RESTORE:
          ar.checksum = bak['packages'][i]['files'][ai]['checksum']
          changed = True
          restored += 1
        else:
          errors += 1
          has_error = True

      if len(pkg.filelist) == 1 and f.vp_checksum:
        vp = pkg.filelist[0]
        if vp.filename.lower().endswith('.vp'):
          if vp.checksum[1] != f.vp_checksum:
            print(pkg.name, '>', ar.checksum, 'VP mismatch!', vp.filename)
            if not has_error:
              errors += 1
              has_error = True

            alt = vpt.get(vp.checksum[1])
            if alt and ar.filesize == alt.filesize:
              print(pkg.name, '>', 'Alternative:', alt.checksum)
              fixes += 1

      if has_error and bak:
        print(pkg.name, '>', 'Backup', bak['packages'][i]['files'])
        backups += 1

  if changed:
    mr.save()

print(errors, 'errors detected')
print(fixes, 'fixable')
print(backups, 'backups')
print(restored, 'restored')

