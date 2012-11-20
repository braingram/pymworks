#!/bin/bash

src="$HOME/Repositories/braingram/makeapp/makeapp.py"
template="template"

$src -n tkmworks -l main.py $template clientmodel.py widgets.py
