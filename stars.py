#!/usr/bin/env python3

limit=''
rating='library.rating > 2 and'

# remove the limit='limit 5' line in order to process your whole library, else it will only process the first five tracks
#limit='limit 1'

import sqlite3
import mutagen
from mutagen.id3 import ID3, error, delete, ID3FileType
import struct
import textwrap
import base64
import argparse

def try_to_open(filename):
    try:
        audio = mutagen.File(filename)
        return audio
    except mutagen.MutagenError:
        print(f"File {filename} not found!")
        return None

def determine_filetype(inputfile):
    audio = try_to_open(inputfile)
    if audio:
        return audio.mime[0]

def mixxx_cuepos_to_ms(cuepos,samplerate,channels):
    return int(float(cuepos) / (int(samplerate) * int(channels)) * 1000)

def serato_cues_for_track(con, path, samplerate, channels):
    countcur = con.cursor()
    serato_cues = []
    for cue in cur.execute(f'select cues.position, cues.hotcue, cues.label from track_locations inner join cues on cues.track_id = track_locations.id inner join library on library.id = track_locations.id where track_locations.location = (?) and cues.type = 1 and cues.hotcue >= 0 order by track_locations.location', (path,)):
        serato_cues.append((mixxx_cuepos_to_ms(cue[0], samplerate, channels), cue[1], cue[2]))
    return serato_cues

def gen_serato_markers(con, file, samplerate, channels):
    # https://github.com/Holzhaus/serato-tags/blob/master/docs/serato_markers2.md
    cues = serato_cues_for_track(con, file, samplerate, channels)
#    print(cues)
    markers = b'\x01\x01' + b'COLOR\x00' + b'\x00\x00\x00\x04' + b'\x00\xff\xff\xff'

    for cue in cues:
      markers += b'CUE\x00' + struct.pack('>i', len(cue[2]) + 13)  # label length can be zero or more bytes, the rest is always 13 bytes
      markers += b'\x00'                              # Magic value
      markers += struct.pack('B', cue[1])             # Cue index
      markers += struct.pack('>i', cue[0])            # Position in track of this cue in milliseconds
      markers += b'\x00'                              # Magic value
      markers += b'\xcc\x00\x00'                      # Red colour for everything
      markers += b'\x00\x00'                          # Magic value
      markers += cue[2].encode('utf8')                # Insert any label for this cue
      markers += b'\x00'                              # Magic value

    markers += b'BPMLOCK\x00' + b'\x00\x00\x00\x01' + b'\x00'
    markers += b'\x00'
    return markers

def write_flac(con, flacfile, rating, dateadded, samplerate, channels):
    audio = try_to_open(flacfile)

    markers = b'application/octet-stream' + b'\x00\x00' + b'Serato Markers2' + b'\x00\x01\x01'
    markers += textwrap.fill(base64.b64encode(gen_serato_markers(con, flacfile, samplerate, channels)).decode('ascii'), width=72).encode('utf8')
    markers += b'\x00' * 470
    audio["SERATO_MARKERS_V2"] = textwrap.fill(base64.b64encode(markers).decode('ascii'), width=72)
    audio.save()

def write_id3(con, id3file, rating, dateadded, samplerate, channels):
    audio = try_to_open(id3file)

    audio['TCOM'] = mutagen.id3.TCOM(
        encoding=3,
        text= '??????' * rating,
    )
    audio.save()

parser = argparse.ArgumentParser()
parser.add_argument('mixxx_database', metavar='INFILE', help="path to the mixxxdb.sqlite database file")
args = parser.parse_args()

con = sqlite3.connect(args.mixxx_database)
cur = con.cursor()
#cur.execute(f'select track_locations.location, library.rating, library.artist, library.title, library.datetime_added, library.comment, library.album, library.samplerate, library.channels from track_locations inner join library on library.id = track_locations.id where library.rating > 2 and mixxx_deleted = 0 and UPPER(track_locations.location) like "%.MP3" {limit}')
cur.execute(f'select track_locations.location, library.rating, library.datetime_added, library.samplerate, library.channels from track_locations inner join library on library.id = track_locations.id where {rating} mixxx_deleted = 0 {limit}')
tracks = cur.fetchall()

for track in tracks:
    print(track[0])
    filetype = determine_filetype(track[0])

    if filetype == 'audio/flac':
        write_flac(con, track[0], track[1], track[2], track[3], track[4])
    elif filetype == 'audio/mp3':
        write_id3(con, track[0], track[1], track[2], track[3], track[4])
    else:
        print(f'Sorry, {filetype} files are not supported')
