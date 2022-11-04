CC = c++
ROOTINC = $(shell root-config --incdir)
CCFLAGS = $(shell root-config --cflags) -O3 -msse3 -mavx -g -fPIC -W -Wall
LIBS = $(shell root-config --libs --glibs)  -lMathMore -lMinuit -lGenVector -lROOTVecOps #  -lRooFitCore -lRooFit -lRooStats

MAIN_DIR = $(shell pwd)
SRC_DIR = src
INC_DIR = include
LIB_DIR = lib
OBJ_DIR = obj
PY_DIR = python
EXT_DIR = externals

LIBNAME=CMGRDF
SONAME=lib$(LIBNAME).so

# Linker and flags -------------------------------------------------------------
LD = g++
ROOTLDFLAGS   = $(shell root-config --ldflags)
LDFLAGS       = $(ROOTLDFLAGS) -shared -Wl,-soname,$(SONAME) -Wl,-E -Wl,-z,defs -fPIC
SRCS = $(notdir $(shell ls $(SRC_DIR)/*.cc ))
OBJS = $(SRCS:.cc=.o) 

# Rochester Corrections
OBJS += $(notdir $(patsubst %.cc,%.o,$(wildcard $(EXT_DIR)/RoccoR/RoccoR.cc)))

#Makefile Rules ---------------------------------------------------------------
.PHONY: clean dirs obj lib env

all: dirs obj lib compile_python

#---------------------------------------
dirs:
	@mkdir -p $(LIB_DIR)
	@mkdir -p $(OBJ_DIR)

obj: 
$(OBJ_DIR)/%.o : $(SRC_DIR)/%.cc $(INC_DIR)/%.h
	$(CC) $(CCFLAGS) -I $(INC_DIR) -I $(SRC_DIR) -I $(EXT_DIR) -c $< -o $@

#---------------------------------------

lib: $(LIB_DIR)/$(SONAME) | dirs
$(LIB_DIR)/$(SONAME):$(addprefix $(OBJ_DIR)/,$(notdir $(OBJS)))
	$(LD) $(LDFLAGS) $^  $(SOFLAGS) -o $@ $(LIBS)


#---------------------------------------

compile_python:
	python3 -m compileall -q python 

#---------------------------------------

clean:
# 	@echo "*** Cleaning all directories and dictionaries ..."
	@rm -rf $(OBJ_DIR) 
	@rm -rf $(LIB_DIR) 
	@rm -rf python/*pyc python/*/*pyc

#---------------------------------------

debug:
	@echo "OBJS: $(OBJS)"
	@echo "SRCS: $(SRCS)"

#---------------------------------------
## Rochester corrections
$(OBJ_DIR)/RoccoR.o: externals/RoccoR/RoccoR.cc externals/RoccoR/RoccoR.h
	$(CC) $(CCFLAGS) -I $(INC_DIR) -I $(SRC_DIR) -c $< -o $@

#---------------------------------------
env:
	@echo 'export CMGRDF=$(MAIN_DIR);'
	@echo 'export PYTHONPATH=$${CMGRDF}/python:$${PYTHONPATH};'
	@echo 'export LD_LIBRARY_PATH=$${CMGRDF}/lib:$${LD_LIBRARY_PATH};'
	@test -d $(MAIN_DIR)/externals/HiggsAnalysis/CombinedLimit && \
	   echo 'export COMBINE=$${CMGRDF}/externals/HiggsAnalysis/CombinedLimit/build;' && \
	   echo 'export PATH=$${COMBINE}/bin:$${PATH};' && \
	   echo 'export LD_LIBRARY_PATH=$${COMBINE}/lib:$${LD_LIBRARY_PATH};' && \
	   echo 'export PYTHONPATH=$${COMBINE}/lib/python:$${COMBINE}/lib:$${PYTHONPATH};' || \
	   true;
	@which correction > /dev/null 2>&1 && \
	   echo 'export CORRECTIONLIB=$$(correction config --incdir | sed s+/include$$++)' && \
	   echo 'export LD_LIBRARY_PATH=$${CORRECTIONLIB}/lib:$${LD_LIBRARY_PATH};' || \
	   true;	   
	@test -d $(MAIN_DIR)/externals/correctionlib && \
	   echo 'export CORRECTIONLIB=$${CMGRDF}/externals/correctionlib/correctionlib;' && \
	   echo 'export LD_LIBRARY_PATH=$${CORRECTIONLIB}/lib:$${LD_LIBRARY_PATH};' && \
	   echo 'export PYTHONPATH=$${CORRECTIONLIB}:$${PYTHONPATH};' || \
	   true;	   
	@test -d $(MAIN_DIR)/externals/onnxruntime-linux-x64-1.11.1 && \
	   echo 'export ONNXRUNTIME=$${CMGRDF}/externals/onnxruntime-linux-x64-1.11.1;' && \
	   echo 'export LD_LIBRARY_PATH=$${ONNXRUNTIME}/lib:$${LD_LIBRARY_PATH};'  || \
	   true;
