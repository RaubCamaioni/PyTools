#!/bin/bash

# reduces time complexity, not security relevant
# echo off > /sys/devices/system/cpu/smt/control

echo never > /sys/kernel/mm/transparent_hugepage/enabled
echo never > /sys/kernel/mm/transparent_hugepage/defrag
echo 0 > /sys/kernel/mm/transparent_hugepage/khugepaged/defrag
sysctl -w kernel.randomize_va_space=0
sysctl -w kernel.core_pattern="core"
