# To Love-Dump
 
Collection of dumpers and tools for asset extraction in *To Love-Ru Darkness: Battle Ecstasy* (PS Vita).
 
The goal of this repo is to document how each of the game's proprietary asset formats works, and to provide Python scripts that convert those formats into common, widely-supported ones (PNG, WAV, glTF, plain text, etc.).
 
## Documentation
 
Technical specifications for every reverse-engineered file format live in the [wiki](../../wiki). The wiki documents **the formats themselves**, not the scripts — what bytes mean what, how containers are laid out, where the offsets point, and so on.
 
## Scripts
 
The Python scripts in this repo consume the formats described in the wiki and produce standard output files. They are working tools, not documentation; read the source if you need to know what a specific script does.
 
## Status
 
Experimental. Both the format documentation and the scripts are work in progress and may change as more of the engine gets reversed.
 
## License
 
[MIT](LICENSE)
