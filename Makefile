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

LIBNAME=CMGRDF
SONAME=lib$(LIBNAME).so

# Linker and flags -------------------------------------------------------------
LD = g++
ROOTLDFLAGS   = $(shell root-config --ldflags)
LDFLAGS       = $(ROOTLDFLAGS) -shared -Wl,-soname,$(SONAME) -Wl,-E -Wl,-z,defs -fPIC
SRCS = $(notdir $(shell ls $(SRC_DIR)/*.cc ))
OBJS = $(SRCS:.cc=.o) 

#Makefile Rules ---------------------------------------------------------------
.PHONY: clean dirs obj lib env

all: dirs obj lib compile_python

#---------------------------------------
dirs:
	@mkdir -p $(LIB_DIR)
	@mkdir -p $(OBJ_DIR)

obj: 
$(OBJ_DIR)/%.o : $(SRC_DIR)/%.cc $(INC_DIR)/%.h
	$(CC) $(CCFLAGS) -I $(INC_DIR) -I $(SRC_DIR) -c $< -o $@
$(OBJ_DIR)/%.o : $(SRC_DIR)/%.cc $(SRC_DIR)/%.h
	$(CC) $(CCFLAGS) -I $(INC_DIR) -I $(SRC_DIR) -c $< -o $@

#---------------------------------------

lib: dirs ${LIB_DIR}/$(SONAME)
${LIB_DIR}/$(SONAME):$(addprefix $(OBJ_DIR)/,$(OBJS)) 
#	@echo "\n*** Building $(SONAME) library:"
	$(LD) $(LDFLAGS) $(BOOST_INC) $(addprefix $(OBJ_DIR)/,$(OBJS))  $(SOFLAGS) -o $@ $(LIBS)

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

env:
	@echo "export CMGRDF=$(MAIN_DIR)"
	@echo "export PYTHONPATH=$(MAIN_DIR)/python:$(PYTHONPATH)"
	@echo "export LD_LIBRARY_PATH=$(MAIN_DIR)/lib:$(LD_LIBRARY_PATH)"