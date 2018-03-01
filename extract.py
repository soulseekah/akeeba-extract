import sys, os, zlib
from struct import unpack

# https://www.akeebabackup.com/documentation/akeeba-backup-documentation/appendices.html

if len(sys.argv) < 2:
	raise Exception('Usage %s <akeeba-archive> [extract-path]' % sys.argv[0])

archive = open(sys.argv[1], 'rb')
magic = archive.read(3)

if len(sys.argv) > 2:
	target = sys.argv[2]
else:
	target = '.'

if magic != 'JPA':
	raise Exception('This does not seem to be an Akeeba Backup archive')

header_size, = unpack('<H', archive.read(2))
vmaj, vmin = unpack('<BB', archive.read(2))
print('JPA Version: %d.%d' % (vmaj, vmin))

entitycount, = unpack('<L', archive.read(4))
print('Entities: %d' % entitycount)

usize, csize = unpack('<LL', archive.read(8))
print('Uncompressed size: %d bytes, compressed: %d bytes' % (usize, csize))

span_or_file = archive.read(3)
if span_or_file == 'JP\1':
	archive.read(1 + 2) # Consume 4th magic and fixed header size
	spans, = unpack('<H', archive.read(2))
	print('Spans: %d' % spans)
	if spans > 1:
		raise NotImplementedError('Span support is absent')
	span_or_file = archive.read(3)

print

while span_or_file != '': # EOF
	if span_or_file != 'JPF':
		raise Exception('Invalid file header magic')

	header_size, = unpack('<H', archive.read(2))
	path_len, = unpack('<H', archive.read(2))
	path = archive.read(path_len)
	_type = ['dir', 'file', 'link'][unpack('<B', archive.read(1))[0]]
	compression = ['none', 'gzip', 'bzip2'][unpack('<B', archive.read(1))[0]]

	csize, usize, chmod = unpack('<LLL', archive.read(12))

	print('%s [%s] (compression: %s) %d bytes %o' % (path, _type, compression, usize, chmod))

	if header_size > (3 + 2 + 2 + path_len + 1 + 1 + 12):
		extra, elen = unpack('<HH', archive.read(4))
		if extra != 256:
			print extra
			raise Exception('Unkown extra field')
		archive.read(4) # Timestamp

	if _type == 'file':
		to = os.path.join(target, path)
		if not os.path.exists(os.path.dirname(to)):
			os.makedirs(os.path.dirname(to))
		data = archive.read(csize) # todo: memory
		if compression == 'gzip':
			open(to, 'wb').write(zlib.decompress(data, -15))
		elif compression == 'none':
			open(to, 'wb').write(data)
		else:
			raise NotImplementedError('Unkown compression')
	elif _type == 'dir':
		to = os.path.join(target, path)
		if not os.path.exists(to):
			os.makedirs(to)
	else:
		raise NotImplementedError('Unkown entity type')

	span_or_file = archive.read(3)
