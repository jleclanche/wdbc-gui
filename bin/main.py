#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.path.pardir))

if __name__ == "__main__":
	from qtab.main import main
	main()
