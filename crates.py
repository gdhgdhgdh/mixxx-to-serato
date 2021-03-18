#!/usr/bin/env python3

limit=''
rating='library.rating > 2 and'
rating=''

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

def get_crates_string(con, path):
    cratecur = con.cursor()
    serato_crates = ""
# cues.hotcue, cues.label from track_locations inner join cues on cues.track_id = track_locations.id inner join library on library.id = track_locations.id where track_locations.location = (?) and cues.type = 1
# and cues.hotcue >= 0 order by track_locations.location', (path,)):
    track_id = None

    for id in cratecur.execute(f'SELECT id FROM track_locations WHERE location = (?)', (path,)):
        track_id = id[0]

    for crate in cratecur.execute(f'select crates.name from crates inner join crate_tracks on crates.id = crate_tracks.crate_id where track_id = (?)', (track_id,)):
        serato_crates += 'MIXXX_' + crate[0] + ' '
    return serato_crates

def write_flac(con, flacfile, rating, dateadded, samplerate, channels):
    audio = try_to_open(flacfile)

    audio["COMPOSER"] = text= '⭐' * rating + "  |  " + get_crates_string(con, flacfile)
    audio.save()

def write_id3(con, id3file, rating, dateadded, samplerate, channels):
    audio = try_to_open(id3file)

    audio['TCOM'] = mutagen.id3.TCOM(
        encoding=3,
        text= '⭐️' * rating + "  |  " + get_crates_string(con, id3file),
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
