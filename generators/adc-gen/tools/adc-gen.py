#!/usr/bin/env python3.7
#------------------------------------------------------------------------------
# ADC GEN WRAPPER
# IDEA & POSH Integration Excercises
# Date: 06/05/2019
#------------------------------------------------------------------------------
#======== Verilog wrapper ==========
import sys
import getopt
import math
import subprocess as sp
import fileinput
import re
import shutil
import numpy as np
import argparse
import json
import glob

import operator
import function
import ADC_netlist
import ADC_netlist_pex
import readparamgen
import os
import time
from readparamgen import check_search_done, platformConfig, designName, args, jsonSpec, main
#from subprocess import call
#------------------------------------------------------------------------------
# Clean the workspace
#------------------------------------------------------------------------------
print('#----------------------------------------------------------------------')
print('# Cleaning the workspace...')
print('#----------------------------------------------------------------------')
#p = sp.Popen(['make','bleach_all'], cwd=flowDir)
#p.wait()
#Future: need to remove this after comparator aux cell is characterized
#for file in os.listdir(flowDir + '/src/'):
#   os.remove(flowDir + '/src/' + file)
# Define the internal variables used
genDir = os.path.join(os.path.dirname(os.path.relpath(__file__)),"../")

head_tail_0 = os.path.split(os.path.abspath(genDir))
head_tail_1 = os.path.split(head_tail_0[0])
privateGenDir = os.path.relpath(os.path.join(genDir, '../../', 'private', head_tail_1[1], head_tail_0[1]))
print(genDir)
print(privateGenDir)
#ptCell = 'PT_UNIT_CELL'

flowDir = os.path.join(privateGenDir , './flow')
extDir = genDir + '../../private/generators/adc-gen/extraction'
simDir = genDir + '../../private/generators/adc-gen/hspice'
srcDir = genDir + './src'


for file in os.listdir(simDir + '/'):
   if not os.path.isdir(simDir + '/' + file):
      os.remove(simDir + '/' + file)
if os.path.isdir(simDir + '/run'):
   shutil.rmtree(simDir + '/run', ignore_errors=True)
if os.path.isdir(extDir + '/run'):
   shutil.rmtree(extDir + '/run', ignore_errors=True)

#if (args.clean):
# print('Workspace cleaning done. Exiting the flow.')
# sys.exit(0)

p = sp.Popen(['make','bleach_all'], cwd=flowDir)
p.wait()

try:
   os.mkdir(extDir + '/run')
except OSError:
   print('Unable to create the "run" directory in "extraction" folder')

try:
   os.mkdir(simDir + '/run')
except OSError:
   print('Unable to create the "run" directory in "hspice" folder')
#------------------------------------------------------------------------------
# Initialize the config variables
#------------------------------------------------------------------------------


power_with_inx, fsampling, resolution, enob, area, nisw, ncsw = main()

print('Fsampling : ' , fsampling)
print('Resolution : ' , resolution)
print('ENOB : ' , enob)
print('Power : ' , power_with_inx)
print('Area : ' , area)
print('nisw : ' , nisw)
print('ncsw : ' , ncsw)

print('\n')
print('#----------------------------------------------------------------------')
print('# Verilog Generation')
print('#----------------------------------------------------------------------')


time.sleep(2) 


aux1 = 'SW_INPUT'
aux2 = 'SW_VCM'
aux3 = 'UNIT_CAP'
#aux4 = 'BUFX4RVT_ISOVDD'
#aux5 = 'HEADERX1RVT'
#aux6 = 'LC1P2TO3P6X1RVT_VDDX4'


###change

aLib1 = platformConfig['aux_lib'] + aux1 + '/latest/'
aLib2 = platformConfig['aux_lib'] + aux2 + '/latest/'
aLib3 = platformConfig['aux_lib'] + aux3 + '/latest/'

aLib = platformConfig['aux_lib']


calibreRulesDir = platformConfig['calibreRules']

ADC_netlist.gen_adc_netlist(resolution, nisw, ncsw, simDir, genDir, args.platform)

print('#----------------------------------------------------------------------')
print('# Verilog Generated')
print('#----------------------------------------------------------------------')
designAreaVerilog= 1000
jsonSpec['results'] = {'platform': args.platform}
jsonSpec['results'].update({'area': designAreaVerilog})
jsonSpec['results'].update({'enob': enob})
jsonSpec['results'].update({'power': power_with_inx})

with open(args.outputDir + '/' + designName + '.json', 'w') as resultSpecfile:
   json.dump(jsonSpec, resultSpecfile, indent=True)

with open(flowDir + '/src/cdac.v', 'r') as file:
  filedata = file.read()
if args.platform == 'tsmc65lp':
  filedata = re.sub('sw_input (\S*) \(\.in0l(\S+) \.in0r(\S+) \.in1(\S+) \.out(\S+) \.sw0(\S+) \.sw1(\S+)', 'SW_INPUT \g<1> (.IN0L\g<2> .IN0R\g<3> .IN1\g<4> .OUT\g<5> .SW0\g<6> .SW1\g<7>', filedata)
  filedata = re.sub('sw_vcm (\S*) \(.in(\S*) .out(\S*) .sw_ctrl(\S*)', 'SW_VCM \g<1> (.IN\g<2> .OUT\g<3> .SW_CTRL\g<4>', filedata)
  filedata = re.sub('unit_cap (\S*) \(.top(\S*) .bot(\S*)', 'UNIT_CAP \g<1> (.VTOP\g<2> .VBOT\g<3>', filedata)
with open(flowDir + '/src/cdac.v', 'w') as file:
  filedata = file.write(filedata)

time.sleep(2)

print()
if args.mode == 'verilog':
  print("Exiting tool....")
  #sys.exit(1)
  exit()
print('#----------------------------------------------------------------------')
print('# Configuring Synth and APR scripts...')
print('#----------------------------------------------------------------------')




with open(flowDir + '/include.mk', 'r') as file:
   filedata = file.read()
filedata = re.sub(r'export DESIGN_NAME :=.*', r'export DESIGN_NAME := ' + \
                  designName, filedata)
filedata = re.sub(r'export PLATFORM *:=.*', r'export PLATFORM    := ' + \
                  args.platform, filedata)
with open(flowDir + '/include.mk', 'w') as file:
   file.write(filedata)

# Update the verilog file list for Synthesis
with open(flowDir + '/scripts/dc/dc.filelist.tcl', 'r') as file:
   filedata = file.read()
filedata = re.sub(r'append MAIN_SOURCE_FILE.*', r'append MAIN_SOURCE_FILE ' + \
                  '\"' + designName + '.v\"', filedata)
filedata = re.sub(r'#+append', r'append', filedata)
with open(flowDir + '/scripts/dc/dc.filelist.tcl', 'w') as file:
   file.write(filedata)

with open(flowDir + '/scripts/dc/constraints.tcl', 'r') as file:
   filedata = file.read()
filedata = re.sub(r'#+set_dont_touch', r'set_dont_touch', filedata)
with open(flowDir + '/scripts/dc/constraints.tcl', 'w') as file:
   file.write(filedata)

flowPtExportDir = flowDir+"/blocks/PT_UNIT_CELL/export"
if not os.path.exists(flowPtExportDir):
  os.makedirs(flowPtExportDir)


shutil.copyfile(aLib + '/' + aux1 + '/latest/'  + aux1 + '.db',   flowPtExportDir + "/" + aux1 + '.db')
shutil.copyfile(aLib + '/' + aux2 + '/latest/'  + aux2 + '.db',   flowPtExportDir + "/" + aux2 + '.db')
shutil.copyfile(aLib + '/' + aux3 + '/latest/'  + aux3 + '.db',   flowPtExportDir + "/" + aux3 + '.db')

shutil.copyfile(aLib + '/' + aux1 + '/latest/'  + aux1 + '.lib',   flowPtExportDir + "/" + aux1 + '.lib')
shutil.copyfile(aLib + '/' + aux2 + '/latest/'  + aux2 + '.lib',   flowPtExportDir + "/" + aux2 + '.lib')
shutil.copyfile(aLib + '/' + aux3 + '/latest/'  + aux3 + '.lib',   flowPtExportDir + "/" + aux3 + '.lib')

shutil.copyfile(aLib + '/' + aux1 + '/latest/'  + aux1 + '.lef',   flowPtExportDir + "/" + aux1 + '.lef')
shutil.copyfile(aLib + '/' + aux2 + '/latest/'  + aux2 + '.lef',   flowPtExportDir + "/" + aux2 + '.lef')
shutil.copyfile(aLib + '/' + aux3 + '/latest/'  + aux3 + '.lef',   flowPtExportDir + "/" + aux3 + '.lef')

shutil.copyfile(aLib + '/' + aux1 + '/latest/'  + aux1 + '.cdl',   flowPtExportDir + "/" + aux1 + '.cdl')
shutil.copyfile(aLib + '/' + aux2 + '/latest/'  + aux2 + '.cdl',   flowPtExportDir + "/" + aux2 + '.cdl')
shutil.copyfile(aLib + '/' + aux3 + '/latest/'  + aux3 + '.cdl',   flowPtExportDir + "/" + aux3 + '.cdl')

shutil.copyfile(aLib + '/' + aux1 + '/latest/'  + aux1 + '.gds',   flowPtExportDir + "/" + aux1 + '.gds')
shutil.copyfile(aLib + '/' + aux2 + '/latest/'  + aux2 + '.gds',   flowPtExportDir + "/" + aux2 + '.gds')
shutil.copyfile(aLib + '/' + aux3 + '/latest/'  + aux3 + '.gds',   flowPtExportDir + "/" + aux3 + '.gds')

time.sleep(1)

print('#----------------------------------------------------------------------')
print('# Synthesis...')
print('#----------------------------------------------------------------------')
time.sleep(1)
print("Checking required files....")



# shutil.copyfile(srcDir+'/sar_logic.v', flowDir+'/src/sar_logic.v')


# Run the Synthesis flow
p = sp.Popen(['make','synth'], cwd=flowDir)
p.wait()

with open(flowDir + '/reports/dc/' + designName + '.mapped.area.rpt', \
     'r')as file:
   filedata = file.read()
m = re.search('Total cell area: *([0-9.]*)', filedata)
if m:
   coreCellArea = float(m.group(1))
else:
   print("Synthesis Failed")
   sys.exit(1)

# Calculate and update the core cell area dimensions
coreDim = 100
if args.platform == 'tsmc65lp':
   coreDim = math.ceil(math.sqrt(coreCellArea*2.3)/5)*25
else:
   coreDim = math.ceil(math.sqrt(coreCellArea*2.3)/5)*10
coreHeight = math.ceil(math.sqrt(coreCellArea*2.5)/5/1.25)*5
coreWidth = math.ceil(math.sqrt(coreCellArea*2.5)/5)*5*2.1

with open(flowDir + '/scripts/innovus/always_source.tcl', 'r') as file:
   filedata = file.read()
filedata = re.sub(r'set core_width.*', r'set core_width    ' + \
        str(coreDim) + ' ;# Core Area Width', filedata)
filedata = re.sub(r'set core_height.*', r'set core_height   ' + \
        str(coreDim) + ' ;# Core Area Height', filedata)
with open(flowDir + '/scripts/innovus/always_source.tcl', 'w') as file:
   file.write(filedata)

time.sleep(1)

# Run the APR flow
p = sp.Popen(['make','design'], cwd=flowDir)
p.wait()

print('#----------------------------------------------------------------------')
print('# Place and Route finished')
print('#----------------------------------------------------------------------')
time.sleep(2)

p = sp.Popen(['make','drc'], cwd=flowDir)
p.wait()



print('#----------------------------------------------------------------------')
print('# DRC finished')
print('#----------------------------------------------------------------------')


time.sleep(2)

p = sp.Popen(['make','lvs'], cwd=flowDir)
p.wait()

# modify UNIT_CAP.cdl to fix lvs bug
with open(flowPtExportDir + "/" + aux3 + '.cdl', 'r') as file:
   filedata = file.read()
filedata = re.sub('C0', 'X0', filedata)
with open(flowPtExportDir + "/" + aux3 + '.cdl', 'w') as file:
   file.write(filedata)


#run lvs on the fixed cdl
p = sp.Popen(['rm', '-f', 'vpath/lvs_rerun'], cwd=flowDir)
p.wait()
p = sp.Popen(['make', 'lvs_rerun'], cwd=flowDir)
p.wait()

#change UNIT_CAP.cdl back
with open(flowPtExportDir + "/" + aux3 + '.cdl', 'r') as file:
   filedata = file.read()
filedata = re.sub('X0', 'C0', filedata)
with open(flowPtExportDir + "/" + aux3 + '.cdl', 'w') as file:
   file.write(filedata)

print('#----------------------------------------------------------------------')
print('# LVS finished')
print('#----------------------------------------------------------------------')



time.sleep(2)


print('# Exporting files....')
time.sleep(1)

p = sp.Popen(['make','export'], cwd=flowDir)
p.wait()

with open(flowDir + '/reports/innovus/' + designName + \
     '.main.htm.ascii', 'r') as file:
   filedata = file.read()
m = re.search('Total area of Chip: ([0-9.]*)', filedata)
if m:
   designArea = float(m.group(1))
else:
   print('APR Failed')
   sys.exit(1)

print()
if args.mode == 'macro':
  print("Exiting tool....")
  sys.exit(1)

time.sleep(2)


#------------------------------------------------------------------------------
# Generate post PEX netlist
#------------------------------------------------------------------------------
#Generate pre PEX netlist and gds files
# cdlInclude = ''
# cdlParse   = ''
# with open(flowDir + '/scripts/innovus/generated/' + designName + \
#      '.cdlList', 'r') as file:
#    filedata = file.readlines()
# for line in filedata:
#    cdlInclude = cdlInclude + ' -s ' + line.rstrip()
#    cdlParse   = cdlParse + ' -lsr ' + line.rstrip()

# # NOTE: The exported version of the gds is not merged (i.e. doesn't include standard cells)
#  p = sp.Popen(['cp', flowDir+'/export/'+designName+'.gds.gz', \
#          extDir+'/layout/'+designName+'.gds.gz'])
# p = sp.Popen(['cp', flowDir+'/results/calibre/'+designName+'.merged.gds.gz', \
#          extDir+'/layout/'+designName+'.gds.gz'])
# p.wait()

# Copy the cdl netlist to extraction directory
for file in glob.glob(flowDir+'/results/calibre/lvs/_'+designName+'*.sp'):
   shutil.copy(file, extDir+'/sch/'+designName+'.spi')

# Copy the merged gds file to extraction directory
p = sp.Popen(['cp', flowDir+'/results/calibre/'+designName+'.merged.gds.gz', \
         extDir+'/layout/'+designName+'.gds.gz'])
p.wait()


# Clean the space
if os.path.isfile(extDir + '/run/svdb/' + designName + '.dv'):
   os.remove(extDir + '/run/svdb/' + designName + '.dv')
if os.path.isfile(extDir + '/run/svdb/' + designName + '.extf'):
   os.remove(extDir + '/run/svdb/' + designName + '.extf')
if os.path.isfile(extDir + '/run/svdb/' + designName + '.lvsf'):
   os.remove(extDir + '/run/svdb/' + designName + '.lvsf')
if os.path.isfile(extDir + '/run/svdb/' + designName + '.pdsp'):
   os.remove(extDir + '/run/svdb/' + designName + '.pdsp')
if os.path.isfile(extDir + '/run/svdb/' + designName + '.sp'):
   os.remove(extDir + '/run/svdb/' + designName + '.sp')

if os.path.isdir(extDir + '/run/svdb/' + designName + '.phdb'):
   shutil.rmtree(extDir + '/run/svdb/' + designName + '.phdb',
                 ignore_errors=True)
if os.path.isdir(extDir + '/run/svdb/' + designName + '.xdb'):
   shutil.rmtree(extDir + '/run/svdb/' + designName + '.xdb',
                 ignore_errors=True)
if os.path.isdir(extDir + '/run/svdb/' + designName + '.pdb'):
   shutil.rmtree(extDir + '/run/svdb/' + designName + '.pdb',
                 ignore_errors=True)
if os.path.isdir(extDir + '/run/svdb/' + 'template'):
   shutil.rmtree(extDir + '/run/svdb/' + 'template',
                 ignore_errors=True)


# Configure the PEX rule files
for file in os.listdir(calibreRulesDir + '/'):
   if not os.path.isdir(simDir + '/' + file):
      shutil.copy2(calibreRulesDir+'/'+file, extDir+'/run/')

with open(extDir+'/ruleFiles/_calibre.rcx_'+args.platform, 'r') as file:
   filedata = file.read()
filedata = filedata.replace('design', designName)
with open(extDir+'/run/_calibre.rcx_', 'w') as file:
   file.write(filedata)


# Run Calibre RCX
p = sp.Popen(['calibre','-xrc','-phdb','-nowait','-turbo','1',
             '_calibre.rcx_'],cwd=extDir+'/run')
p.wait()
p = sp.Popen(['calibre','-xrc','-pdb','-rcc','-turbo','1','-nowait',
             '_calibre.rcx_'],cwd=extDir+'/run')
p.wait()
p = sp.Popen(['calibre','-xrc','-fmt','-all','-nowait','_calibre.rcx_'],
             cwd=extDir+'/run')
p.wait()
print('# SAR - Post PEX netlist Generated')

#------------------------------------------------------------------------------
# Run Hspice Sims
#------------------------------------------------------------------------------

#generate pex testbench 
ADC_netlist_pex.gen_adc_netlist(resolution, nisw, ncsw, simDir, genDir, args.platform)

#copy pex netlist
p = sp.Popen(['cp',extDir+'/run/'+designName+'.pex.netlist.pex',
             simDir+'/spice/'])
p.wait()
p = sp.Popen(['cp',extDir+'/run/'+designName+'.pex.netlist.'+designName+'.pxi', simDir+'/spice/'])
p.wait()
p = sp.Popen(['cp',extDir+'/run/'+designName+'.pex.netlist', simDir+'/spice/'])
p.wait()

# process pex netlist port definition
ports = ""
for i in range(0, resolution):
	ports += 'result<' + str(i) + '> '
ports = '.SUBCKT sar en clk VSS VDD ' + ports + 'vrefh vinp vcm vrefl vinn\n'

new_file_content = ""
flag = 0
with open(simDir+'/spice/' + designName + '.pex.netlist', 'r') as file:
	for line in file:
		if (re.match("^\.(SUBCKT|subckt) sar", line)):
			line = ports
			new_file_content += line
			flag = 1
		else:
			if (flag and re.match("^\+", line)):
				new_file_content += "\n"
			else:
				flag = 0
				new_file_content += line
	
new_file_content = re.sub(r'\[', '<', new_file_content)
new_file_content = re.sub(r'\]', '>', new_file_content)
with open(simDir+'/spice/' + designName + '.pex.netlist', 'w') as file:
	file.write(new_file_content)

# replace the bracket [] with <>
with open(simDir+'/spice/' + designName + '.pex.netlist.pex', 'r') as file:
	filedata = file.read()
filedata = re.sub(r'\[', '<', filedata)
filedata = re.sub(r'\]', '>', filedata)
with open(simDir+'/spice/' + designName + '.pex.netlist.pex', 'w') as file:
	file.write(filedata)

with open(simDir+'/spice/' + designName + '.pex.netlist.' + designName + '.pxi', 'r') as file:
	filedata = file.read()
filedata = re.sub(r'\[', '<', filedata)
filedata = re.sub(r'\]', '>', filedata)
with open(simDir+'/spice/' + designName + '.pex.netlist.' + designName + '.pxi', 'w') as file:
	file.write(filedata)

pex_sp = glob.glob(simDir + "/run/*.pex.sp")

for pex in pex_sp:
    p = sp.Popen(["finesim", "-spice", "-np", "8", pex.split("/")[-1]], cwd=simDir + "/run/")
    p.wait()
    p = sp.Popen(["python", "result.py", pex.split("/")[-1][0:-3] + ".mt0"], cwd=simDir + "/run/")
    p.wait()


