#!/usr/bin/env python

import sys

from rqt_gui.main import Main

if __name__ == '__main__':
    main = Main()
    sys.exit(main.main(
        sys.argv,
        standalone='toolpath_reader/ToolpathServer',
        ))
