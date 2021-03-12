#!/usr/bin/env python3

import sqlite3
import mutagen
from mutagen.id3 import ID3, error, delete, ID3FileType
import struct
import textwrap
import base64

def determine_filetype(inputfile):
    audio = mutagen.File(inputfile)
    return audio.mime[0]

def mixxx_cuepos_to_ms(cuepos,samplerate,channels):
    return int(float(cuepos) / (int(samplerate) * int(channels)) * 1000)

def serato_cues_for_track(con, path, samplerate, channels):
    countcur = con.cursor()
    serato_cues = []
    for cue in cur.execute(f'select cues.position, cues.hotcue, cues.label from track_locations inner join cues on cues.track_id = track_locations.id inner join library on library.id = track_locations.id where track_locations.location = (?) and cues.type = 1 order by track_locations.location', (path,)):
        serato_cues.append((mixxx_cuepos_to_ms(cue[0], samplerate, channels), cue[1], cue[2]))
    return serato_cues

def gen_serato_markers(con, file, samplerate, channels):
    # https://github.com/Holzhaus/serato-tags/blob/master/docs/serato_markers2.md
    cues = serato_cues_for_track(con, file, samplerate, channels)
    print(cues)
    markers = b''

    for cue in cues:
      markers += b'CUE\x00'
      markers += struct.pack('>i', len(cue[2]) + 13)  # Label determines the number of bytes in this CUE block
      markers += b'\x00'                              # Magic value
      markers += struct.pack('B', cue[1])             # Cue index
      markers += struct.pack('>i', cue[0])            # Position in track of this cue in milliseconds
      markers += b'\x00'                              # Magic value
      markers += b'\xcc\x00\x00'                      # Red colour for everything
      markers += b'\x00\x00'                          # Magic value
      markers += cue[2].encode('utf8')                # Insert any label for this cue
      markers += b'\x00'                              # Magic value

    markers += b'\x00' * 470
    return markers

def write_flac(con, flacfile, samplerate, channels):
    audio = mutagen.File(flacfile)

    markers = b'application/octet-stream' + b'\x00\x00' + b'Serato Markers2' + b'\x00\x01\x01'
    markers += textwrap.fill(base64.b64encode(gen_serato_markers(con, flacfile, samplerate, channels)).decode('ascii'), width=72).encode('utf8')
    audio["SERATO_MARKERS_V2"] = textwrap.fill(base64.b64encode(markers).decode('ascii'), width=72)
    audio.save()

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
cur.execute('select track_locations.location, library.rating, library.artist, library.title, library.datetime_added, library.comment, library.album, library.samplerate, library.channels from track_locations inner join library on library.id = track_locations.id where library.rating = 5 and track_locations.location like "%.flac" limit 1')
tracks = cur.fetchall()

for track in tracks:
    print(track[0])
    filetype = determine_filetype(track[0])

    if filetype == 'audio/flac':
        write_flac(con, track[0], track[7], track[8])
    elif filetype == 'audio/mp3':
        write_mp3(con, track[0], track[7], track[8])
    else:
        print(f'Sorry, {filetype} files are not supported')
