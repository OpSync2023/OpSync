ifndef SDE_INSTALL
$(error SDE_INSTALL is not set)
endif

P4_PROG = opsync_schedule
ARCH = tofino2
PROFILE := test

SOURCES = opsync_schedule.cpp

CC = gcc

CFLAGS  = -I$(SDE_INSTALL)/include -g

BF_LIBS  = -lbf_switch             \
           -lpi                    \
           -lpi_dummy              \
           -lpifeproto             \
           -lavago                 \
           -ldriver                \
           -lbfutils               \
           -ltarget_sys            \
           -lpython3.10    #tf2

#LDFLAGS  = -Wl,-rpath,$(SDE_INSTALL)/lib
LDLIBS   = -L$(SDE_INSTALL)/lib -L$(SDE_INSTALL)/lib/$(ARCH)pd
LDLIBS  += -Wl,--start-group $(BF_LIBS) -Wl,--end-group
LDLIBS  += -lm -pthread -lpcap -lstdc++ -ldl -levent -ldriver


all: $(P4_PROG)


$(P4_PROG): 
	$(CC) -g $(CFLAGS) $(SOURCES) -o $(P4_PROG) $(LDLIBS) $(LDFLAGS)
	@echo ' Finished successfully building.'

clean:
	rm $(P4_PROG)