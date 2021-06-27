#!/bin/bash

# Usage:

nmap -Pn -p 554 $1 | grep -B 4 open