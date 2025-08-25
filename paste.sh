#!/usr/bin/bash

# Read from clipboard and type it
# xclip -o defaults to the mouse selection
# if there is none, then use the clipboard
CLIP=$(xclip -o 2>/dev/null || xclip -o -selection clipboard 2>/dev/null)
xdotool type --clearmodifiers --delay 0 --file <(echo "$CLIP")
