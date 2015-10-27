#! /usr/bin/env python3
"""Utility to build MacOSX keylayout files from simple json format.
"""
import os
import io
import sys
import json


class KeyTree(object):
    __slots__ = ('code', 'output', 'children',)

    def __init__(self, code, output=None):
        self.code = code
        self.output = output
        self.children = []

    def add(self, path, output):
        codes = []
        for name in path:
            code = NAME_TO_CODE.get(name)
            if code is None:
                sys.stderr.write("[error] Invalid code name '{}'\n".format(name))
                sys.exit(1)
            codes.append(code)
        if not codes:
            sys.stderr.write("[error] Empty code path\n")
            sys.exit(1)
        node = self
        for code in codes:
            children = {child.code: child for child in node.children}
            child = children.get(code)
            if child is None:
                child = KeyTree(code)
                node.children.append(child)
            node = child
        if node.output is not None:
            sys.stderr.write("[error] Duplicating path '{}'\n".format(path))
            sys.exit(1)
        node.output = escape(output)

    def compile(self):
        actions = {}
        terms   = {}
        state   = state_factory()
        def traverse(node, path=''):
            action = actions.get(node.code)
            if action is None:
                action = {}
                actions[node.code] = action
            next = path + CODE_TO_NAME[node.code]
            if node.children:
                action[state(path)] = ("next", state(next))
                if node.output:
                    terms[state(next)] = node.output
                for child in node.children:
                    traverse(child, next)
            elif node.output:
                action[state(path)] = ("output", node.output)
        if self.code is None:
            for child in self.children:
                traverse(child)
        else:
            traverse(self)
        keys = {}
        for code, action in list(actions.items()):
            if len(action) == 1 and action.get("none", ('_',))[0] == "output":
                keys[code] = ("output", action["none"][1])
                del actions[code]
            else:
                keys[code] = ("action", code)
        return keys, actions, terms

    def __str__(self):
        if self.code is None:
            return '\n'.join(str(child) for child in sorted(self.children, key=lambda n: n.code))
        code = CODE_TO_NAME[self.code]
        return "({} {}{}{})".format(code, self.output, ' ' if self.children else '',
                                    ' '.join(str(child) for child in self.children))

    def __rerp__(self):
        return str(self)


def main():
    if len(sys.argv) < 2:
        sys.stderr.write('Usage: {} <layout.json>\n'.format(os.path.basename(sys.argv[0])))
        sys.exit(1)
    if sys.version_info[0] < 3:
        sys.stderr.write('[error] Python version is less then 3.0\n')
        sys.exit(1)
    with open(sys.argv[1]) as layout_file:
        layout = json.load(layout_file)
    # validate
    for name, validate in {
        "name": lambda name: isinstance(name, str),
        "keys": lambda keys: isinstance(keys, dict) \
                        and all(isinstance(out, str) for out in keys.values())
    }.items():
        val = layout.get(name)
        if val is None:
            sys.stderr.write("[error] Required field {} is not specified\n"
                             .format(name))
            sys.exit(1)
        if not validate(val):
            sys.stderr.write("[error] Field '{}' has incorrect format\n".format(name))
            sys.exit(1)

    # build key tree
    tree = KeyTree(None)
    for path, output in layout["keys"].items():
        tree.add(path, output)
    keys, actions, terms = tree.compile()

    # formatters
    align = lambda count: '    ' * count
    def keys_fmt(keys, depth):
        stream = io.StringIO()
        for code, action in sorted(keys.items()):
            stream.write('{}<key code="{}" {}="{}" />\n'
                         .format(align(depth), code, action[0], action[1]))
        return stream.getvalue().rstrip()
    def actions_fmt(actions, depth):
        stream = io.StringIO()
        def action_key(action):
            """none element must always be the first one"""
            state = action[0]
            return '\x00' + state if state == 'none' else state
        for code, action in sorted(actions.items()):
            stream.write('{}<action id="{}">\n'.format(align(depth), code))
            for state, next in sorted(action.items(), key=action_key):
                stream.write('{}<when state="{}" {}="{}" />\n'
                             .format(align(depth+1), state, next[0], next[1]))
            stream.write('{}</action>\n'.format(align(depth)))
        return stream.getvalue().rstrip()
    def terms_fmt(terms, depth):
        stream = io.StringIO()
        for state, output in sorted(terms.items()):
            stream.write('{}<when state="{}" output="{}" />\n'
                         .format(align(depth), state, output))
        return stream.getvalue().rstrip()

    keys_default = {c: ("output", escape(o)) for c, o in US_LAYOUT.items()}
    keys_caps_default = {c: ("output", escape(o)) for c, o in US_CAPS_LAYOUT.items()}
    sys.stdout.write(KEY_LAYOUT_TEMPLATE.format(**{
        'name'        : layout['name'],
        'group'       : 7,
        'index'       : 19458,
        'keys'        : keys_fmt({k: v for k, v in keys.items() if k <= 0xff}, 3),
        'keys_caps'   : keys_fmt({k & 0xff: v for k, v in keys.items() if k > 0xff}, 3),
        'keys_default': keys_fmt(keys_default, 3),
        'keys_caps_default': keys_fmt(keys_caps_default, 3),
        'actions'     : actions_fmt(actions, 2),
        'terminators' : terms_fmt(terms, 2),
    }))


def state_factory():
    """Returns function which allocates sequential indexes based on value
    """
    states = {}
    def state(value):
        if value == '':
            return 'none'
        index = states.get(value)
        if index is None:
            index, states[value] = (len(states) + 1,) * 2
        return ':{}'.format(index)
    return state

def escape(string):
    """Escape string converting it to xml hexidemical format
    """
    return ''.join('&#x{:0>4x};'.format(ord(c)) for c in string)

# Reference file for name on MacOS system
# /System/Library/Frameworks/Carbon.framework/Versions/A/Frameworks/HIToolbox.framework/Versions/A/Headers/Events.
s = lambda c: c | 0x100
NAME_TO_CODE = {
  'a': 0x00, 'A': s(0x00),
  's': 0x01, 'S': s(0x01),
  'd': 0x02, 'D': s(0x02),
  'f': 0x03, 'F': s(0x03),
  'h': 0x04, 'H': s(0x04),
  'g': 0x05, 'G': s(0x05),
  'z': 0x06, 'Z': s(0x06),
  'x': 0x07, 'X': s(0x07),
  'c': 0x08, 'C': s(0x08),
  'v': 0x09, 'V': s(0x09),
  'b': 0x0b, 'B': s(0x0b),
  'q': 0x0c, 'Q': s(0x0c),
  'w': 0x0d, 'W': s(0x0d),
  'e': 0x0e, 'E': s(0x0e),
  'r': 0x0f, 'R': s(0x0f),
  'y': 0x10, 'Y': s(0x10),
  't': 0x11, 'T': s(0x11),
  '1': 0x12, '!': s(0x12),
  '2': 0x13, '@': s(0x13),
  '3': 0x14, '#': s(0x14),
  '4': 0x15, '$': s(0x15),
  '6': 0x16, '^': s(0x16),
  '5': 0x17, '%': s(0x17),
  '=': 0x18, '+': s(0x18),
  '9': 0x19, '(': s(0x19),
  '7': 0x1a, '&': s(0x1a),
  '-': 0x1b, '_': s(0x1b),
  '8': 0x1c, '*': s(0x1c),
  '0': 0x1d, ')': s(0x1d),
  ']': 0x1e, '}': s(0x1e),
  'o': 0x1f, 'O': s(0x1f),
  'u': 0x20, 'U': s(0x20),
  '[': 0x21, '{': s(0x21),
  'i': 0x22, 'I': s(0x22),
  'p': 0x23, 'P': s(0x23),
  'l': 0x25, 'L': s(0x25),
  'j': 0x26, 'J': s(0x26),
  '\'': 0x27, '"': s(0x27),
  'k': 0x28, 'K': s(0x28),
  ';': 0x29, ':': s(0x29),
  '\\': 0x2a, '|': s(0x2a),
  ',': 0x2b, '<': s(0x2b),
  '/': 0x2c, '?': s(0x2c),
  'n': 0x2d, 'N': s(0x2d),
  'm': 0x2e, 'M': s(0x2e),
  '.': 0x2f, '>': s(0x2f),
  '`': 0x32, '~': s(0x32),
}
CODE_TO_NAME = {code: name for name, code in NAME_TO_CODE.items()}

US_LAYOUT = {
    0: "a", 1: "s", 2: "d", 3: "f", 4: "h", 5: "g", 6: "z", 7: "x",
    8: "c", 9: "v", 10: "\u00a7", 11: "b", 12: "q", 13: "w", 14: "e",
    15: "r", 16: "y", 17: "t", 18: "1", 19: "2", 20: "3", 21: "4",
    22: "6", 23: "5", 24: "=", 25: "9", 26: "7", 27: "-", 28: "8",
    29: "0", 30: "]", 31: "o", 32: "u", 33: "[", 34: "i", 35: "p",
    36: "\r", 37: "l", 38: "j", 39: "'", 40: "k", 41: ";", 42: "\\",
    43: ",", 44: "/", 45: "n", 46: "m", 47: ".", 48: "\t", 49: " ",
    50: "`", 51: "\b", 52: "\u0003", 53: "\u001b", 65: ".", 66: "\u001d",
    67: "*", 69: "+", 70: "\u001c", 71: "\u001b", 72: "\u001f", 75: "/",
    76: "\u0003", 77: "\u001e", 78: "-", 81: "=", 82: "0", 83: "1",
    84: "2", 85: "3", 86: "4", 87: "5", 88: "6", 89: "7", 91: "8",
    92: "9", 96: "\u0010", 97: "\u0010", 98: "\u0010", 99: "\u0010",
    100: "\u0010", 101: "\u0010", 102: "\u0010", 103: "\u0010",
    104: "\u0010", 105: "\u0010", 106: "\u0010", 107: "\u0010",
    108: "\u0010", 109: "\u0010", 110: "\u0010", 111: "\u0010",
    112: "\u0010", 113: "\u0010", 114: "\u0005", 115: "\u0001",
    116: "\u000b", 117: "\u007f", 118: "\u0010", 119: "\u0004",
    120: "\u0010", 121: "\f", 122: "\u0010", 123: "\u001c",
    124: "\u001d", 125: "\u001f", 126: "\u001e"
}

US_CAPS_LAYOUT = {
    0: "A", 1: "S", 2: "D", 3: "F", 4: "H", 5: "G", 6: "Z", 7: "X",
    8: "C", 9: "V", 10: "\u00b1", 11: "B", 12: "Q", 13: "W", 14: "E",
    15: "R", 16: "Y", 17: "T", 18: "!", 19: "@", 20: "#", 21: "$",
    22: "^", 23: "%", 24: "+", 25: "(", 26: "&", 27: "_", 28: "*",
    29: ")", 30: "}", 31: "O", 32: "U", 33: "{", 34: "I", 35: "P",
    36: "\r", 37: "L", 38: "J", 39: "\"", 40: "K", 41: ":", 42: "|",
    43: "<", 44: "?", 45: "N", 46: "M", 47: ">", 48: "\t", 49: " ",
    50: "~", 51: "\b", 52: "\u0003", 53: "\u001b", 65: ".", 66: "*",
    67: "*", 69: "+", 70: "+", 71: "\u001b", 72: "=", 75: "/",
    76: "\u0003", 77: "/", 78: "-", 81: "=", 82: "0", 83: "1",
    84: "2", 85: "3", 86: "4", 87: "5", 88: "6", 89: "7", 91: "8",
    92: "9", 96: "\u0010", 97: "\u0010", 98: "\u0010", 99: "\u0010",
    100: "\u0010", 101: "\u0010", 102: "\u0010", 103: "\u0010",
    104: "\u0010", 105: "\u0010", 106: "\u0010", 107: "\u0010",
    108: "\u0010", 109: "\u0010", 110: "\u0010", 111: "\u0010",
    112: "\u0010", 113: "\u0010", 114: "\u0005", 115: "\u0001",
    116: "\u000b", 117: "\u007f", 118: "\u0010", 119: "\u0004",
    120: "\u0010", 121: "\f", 122: "\u0010", 123: "\u001c",
    124: "\u001d", 125: "\u001f", 126: "\u001e"
}

# Keylayout file template
# For full documentation: https://developer.apple.com/library/mac/technotes/tn2056/_index.html
KEY_LAYOUT_TEMPLATE = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE keyboard SYSTEM "file://localhost/System/Library/DTDs/KeyboardLayout.dtd">
<!-- Layout is generated with "gen-keylayout.py"
     Author: Pavel Aslanov
     Home  : https://github.com/aslpavel/gen-keylayout
-->
<keyboard group="126" id="-7777" name="{name}" maxout="1">
    <layouts>
        <!-- Expect to use it only with ANSI keyboard -->
        <layout first="0" last="207" modifiers="modifiers" mapSet="ANSI" />
    </layouts>
    <modifierMap id="modifiers" defaultIndex="2">
        <keyMapSelect mapIndex="0">
            <modifier keys="" />
        </keyMapSelect>
        <keyMapSelect mapIndex="1">
            <modifier keys="anyShift" />
            <modifier keys="caps" />
        </keyMapSelect>
    </modifierMap>
    <keyMapSet id="ANSI">
        <keyMap index="0" baseIndex="2" baseMapSet="ANSI">
{keys}
        </keyMap>
        <keyMap index="1" baseIndex="3" baseMapSet="ANSI">
{keys_caps}
        </keyMap>
        <!-- default US keylayout -->
        <keyMap index="2">
{keys_default}
        </keyMap>
        <keyMap index="3">
{keys_caps_default}
        </keyMap>
    </keyMapSet>
    <actions>
{actions}
    </actions>
    <terminators>
{terminators}
    </terminators>
</keyboard>
"""

if __name__ == '__main__':
    main()
