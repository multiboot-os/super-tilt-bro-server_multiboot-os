#!/bin/bash

dbg_log_flags=""
optim_flags="-O3 -DNDEBUG -flto"
if [ "x$1" == "xdbg" ]; then
	dbg_log_flags="-DLOG_FLOOD"
	optim_flags="-O0 -g"
fi

g++ \
	$optim_flags -o stb_server $dbg_log_flags \
	-I .. -I ../.. \
	stb_server.cpp \
	../network.cpp \
	../GameState.cpp \
	DatagramDispatcher.cpp \
	ClientsDatagramRouting.cpp \
	InitializationHandler.cpp \
	GameInstance.cpp \
	StatisticsSink.cpp \
	-lpthread \
	-luuid \
	-lboost_system
