#!/usr/bin/env python3

# This only seems to support MP3 files because it uses the old 'Markers' format
# which does not permit labelling the cues

import sqlite3
import mutagen
from mutagen.id3 import ID3, error, delete, ID3FileType
import struct
import textwrap
import base64

def determine_filetype(inputfile):
    audio = mutagen.File(inputfile)
    return audio.mime[0]

def serato32encode(data):
    """Encode 4 byte plain text into 4 byte Serato binary format."""
    a, b, c = struct.unpack('xBBB', data)
    z = c & 0x7F
    y = ((c >> 7) | (b << 1)) & 0x7F
    x = ((b >> 6) | (a << 2)) & 0x7F
    w = (a >> 5)
    return bytes(bytearray([w, x, y, z]))

def mixxx_cuepos_to_serato_cuepos(cuepos,samplerate,channels):
    ms = int(float(cuepos) / (int(samplerate) * int(channels)) * 1000)
    return serato32encode(struct.pack('>I',ms))

def serato_cues_for_track(con, path, samplerate, channels):
    countcur = con.cursor()
    serato_cues = []
    for cue in cur.execute(f'select cues.position, cues.hotcue, cues.label from track_locations inner join cues on cues.track_id = track_locations.id inner join library on library.id = track_locations.id where track_locations.location = (?) and cues.type = 1 order by track_locations.location', (path,)):
        serato_cues.append((mixxx_cuepos_to_serato_cuepos(cue[0], samplerate, channels), cue[1], cue[2]))
    return serato_cues

def gen_serato_markers(con, file, samplerate, channels):
    # https://github.com/Holzhaus/serato-tags/blob/master/docs/serato_markers_.md
    cues = serato_cues_for_track(con, file, samplerate, channels)
    markers = b'\x02\x05' + struct.pack('>i', len(cues))

    for cue in cues:
      markers += b'\x00' + cue[0]            # Yes, this is a cue which starts here
      markers += b'\x7f\x7f\x7f\x7f\x7f'     # No, there isn't finish time, beccause this is a cue, not a loop.
      markers += b'\x00\x7f\x7f\x7f\x7f\x7f' # Some fixed 'magic'
      markers += b'\x06\x30\x00\x00'         # Red colour for everything
      markers += b'\x01\x00'                 # Again, this is a cue, not a loop

    markers += b'\x07\x7f\x7f\x7f'        # Track should be displayed in the library in white
    return markers

def write_mp3(con, mp3file, samplerate, channels):
    audio = ID3(mp3file)

    audio['GEOB:Serato Markers_'] = mutagen.id3.GEOB(
        encoding=0,
        mime='application/octet-stream',
        desc='Serato Markers_',
        data=gen_serato_markers(con, mp3file, samplerate, channels),
    )
    audio.save()

con = sqlite3.connect('mixxxdb.sqlite')
cur = con.cursor()
cur.execute('select track_locations.location, library.rating, library.artist, library.title, library.datetime_added, library.comment, library.album, library.samplerate, library.channels from track_locations inner join library on library.id = track_locations.id where library.rating = 5 and UPPER(track_locations.location) like "%.MP3"')
tracks = cur.fetchall()

for track in tracks:
    print(track[0])
    filetype = determine_filetype(track[0])

    if filetype == 'audio/mp3':
        write_mp3(con, track[0], track[7], track[8])
    else:
        print(f'Sorry, {filetype} files are not supported')
