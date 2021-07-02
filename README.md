# gen-keylayout
Generate MacOS keylayout based on JSON description.

## Rationale
Constructing xml keyboard layout by hand or even with tools like [Ukelele][ukelele] is a tedious task.
So I wrote simple python script with no external dependancies, to make your life easier if 
found yourself in a situation where all existing keyboards do not work as you want them to.

## Usage
```bash
# generating layout and saving it to my.keylayout file
python3 ./gen-keylayout.py <your-json-layout> > my.keylayout
# putting file to "~/Library/Keyboard Layouts"
mv my.keylayout ~Library/Keyboard\ Layouts
# Go to "System preferences" -> "Keyboard" -> "Input sources" -> "+" -> "Others" -> "YOUR LAYOUT NAME"
```

## Format
Json layout file contains two required attirbutes `name` and `keys`. `name` is arbitrary UTF-8
string and it will be used as idendification in preference settings. `keys` is a mapping
from key sequence to desired output, where key sequence is ANSI names of desired keys.
Minimal example `{"name":"example","keys":{"/t":"щ"}}` will result in handling sequence of
key presses `/` `t` outputing symbol `щ`. Complete example for russian transliteration keyboard
can be found in [example folder](example).

## Known limitations
* Works only with python of version 3 and higher.
* Fallbacks to US keyboard with all modifiers except *shift* and *caps*
  it helps to use default hotkeys

## Links
* Installable Keyboard Layouts [reference][reference].
* [Ukelele][ukelele] utility.

[ukelele]: http://scripts.sil.org/cms/scripts/page.php?site_id=nrsi&id=ukelele
[reference]: https://developer.apple.com/library/mac/technotes/tn2056/_index.html
