# mixxx-to-serato

## Overview

I had a need to move from Mixxx DJ to Serato Pro, and couldn't find any tools to help migrate an existing library, so I wrote this. The thing I absolutely needed to move were my cue points as these had been collected and set over multiple years. I didn't want to do that work again.


### What it WILL do

The `cues.py` script WILL add a `Serato Markers2` metadata block to each MP3 and FLAC file mentioned in your `mixxxdb.sqlite`.

Repeat: the script *WILL WRITE* to every one of the MP3 and FLAC files in your Mixxx library. It uses the very mature Python `mutagen` library to do this, so it's a very safe operation.

It will copy cuepoints from your Mixxx library so that Serato Pro will read them, and will copy any labels you've attached to each cue.

### What it WILL NOT do 

It does NOT write anything back to the `mixxxdb.sqlite`

It does NOT cover Mixxx loops or colours (I use Mixxx 2.2) 

## Installation

It needs only Python 3 itself, and the `mutagen` Python module which should be safe to install on your system Python installation.

```
pip3 install mutagen
```

## Find the database file.

You'll need to find where your Mixxx database lives. 

### Linux

This will almost certainly be `~/.mixxx/mixxxdb.sqlite`.

### Mac

It is well hidden on the Mac. Open a new `Terminal` and run this

```
find Library -type f -name mixxxdb.sqlite

```

### Windows

No idea, sorry. It'll probably be hidden in `Application Data` somewhere. Open a GitHub issue if you find it.

## Usage

```
python3 cues.py /full/path/to/your/mixxxdb.sqlite
```

That should be it - the script will print out the name of each track that it's processing. If anything goes wrong, please let me know by opening a GitHub Issue.

Cheers,
Gavin.
